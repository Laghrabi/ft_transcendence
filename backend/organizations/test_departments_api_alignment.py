"""Integration tests for the Departments frontend API contract."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from organizations.models import Department, DepartmentMembership, Role
from workflow.models import Case, Task


class DepartmentsAPITestData(APITestCase):
    """Shared fixtures and assertions; this base class contains no tests."""

    list_url = "/api/auth/departments/"
    memberships_url = "/api/auth/memberships/"
    public_fields = {"id", "name", "description", "is_active", "accepts_new_tasks"}
    detail_fields = public_fields | {"administrator", "created_at", "updated_at"}

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.doctor_role = Role.objects.get(name="Doctor")
        cls.nurse_role = Role.objects.get(name="Nurse")
        cls.admin_role = Role.objects.get(name="Administrator")

        cls.cardio = Department.objects.create(
            name="Cardiology", description="Cardiovascular care."
        )
        cls.radio = Department.objects.create(name="Radiology")
        cls.inactive = Department.objects.create(
            name="Inactive Department", is_active=False
        )
        cls.no_admin = Department.objects.create(name="No Administrator")

        cls.superuser = User.objects.create_superuser(
            email="system@example.com", name="System Admin",
            password="TestPassword123!",
        )
        cls.admin = User.objects.create_user(
            email="admin@example.com", name="Cardiology Admin",
            password=None, requested_role=cls.doctor_role,
            avatar="https://example.com/avatar.png",
            approval_status="approved", is_active=True,
        )
        cls.doctor = User.objects.create_user(
            email="doctor@example.com", name="Radiology Doctor",
            password=None, requested_role=cls.doctor_role,
            approval_status="approved", is_active=True,
        )
        cls.nurse = User.objects.create_user(
            email="nurse@example.com", name="Cardiology Nurse",
            password=None, requested_role=cls.nurse_role,
            approval_status="approved", is_active=True,
        )
        cls.unassigned = User.objects.create_user(
            email="unassigned@example.com", name="Unassigned Doctor",
            password=None, requested_role=cls.doctor_role,
            approval_status="approved", is_active=True,
        )
        cls.radio_admin = User.objects.create_user(
            email="radioadmin@example.com", name="Radiology Admin",
            password=None, requested_role=cls.nurse_role,
            approval_status="approved", is_active=True,
        )
        cls.disabled = User.objects.create_user(
            email="disabled@example.com", name="Inactive Nurse",
            password=None, requested_role=cls.nurse_role,
            approval_status="approved", is_active=False,
        )
        cls.pending = User.objects.create_user(
            email="pending@example.com", name="Pending Doctor",
            password=None, requested_role=cls.doctor_role,
            approval_status="pending", is_active=False,
        )
        cls.rejected = User.objects.create_user(
            email="rejected@example.com", name="Rejected Doctor",
            password=None, requested_role=cls.doctor_role,
            approval_status="rejected", is_active=False,
        )
        cls.admin_membership = DepartmentMembership.objects.create(
            department=cls.cardio, user=cls.admin, role=cls.admin_role,
        )
        cls.nurse_membership = DepartmentMembership.objects.create(
            department=cls.cardio, user=cls.nurse, role=cls.nurse_role,
        )
        cls.doctor_membership = DepartmentMembership.objects.create(
            department=cls.radio, user=cls.doctor, role=cls.doctor_role,
        )
        DepartmentMembership.objects.create(
            department=cls.radio, user=cls.radio_admin, role=cls.admin_role,
        )
        cls.disabled_membership = DepartmentMembership.objects.create(
            department=cls.radio, user=cls.disabled, role=cls.nurse_role,
        )

    def detail_url(self, department):
        return f"{self.list_url}{department.pk}/"

    def action_url(self, department, action):
        return f"{self.detail_url(department)}{action}/"

    def find_department(self, data, department):
        index = 0
        while index < len(data):
            if data[index]["id"] == department.pk:
                return data[index]
            index += 1
        self.fail(f"Department {department.pk} missing from response")

    def make_old_timestamp(self, department):
        old = timezone.now() - timedelta(days=2)
        Department.objects.filter(pk=department.pk).update(updated_at=old)
        department.refresh_from_db()

    def audit_events(self, department):
        return AuditEvent.objects.filter(
            target_type=Department._meta.label, target_id=department.pk,
        )

    def snapshot(self, department):
        department.refresh_from_db()
        return (
            department.name, department.description,
            department.is_active, department.accepts_new_tasks,
            department.created_at, department.updated_at,
            list(DepartmentMembership.objects.filter(department=department)
                 .order_by("id").values_list("id", "user_id", "role_id")),
            self.audit_events(department).count(),
        )

    def assert_unchanged(self, department, before):
        self.assertEqual(self.snapshot(department), before)

    def assert_updated(self, department, before, action, actor):
        department.refresh_from_db()
        self.assertEqual(department.created_at, before[4])
        self.assertGreater(department.updated_at, before[5])
        events = self.audit_events(department)
        self.assertEqual(events.count(), before[7] + 1)
        self.assertTrue(events.filter(action=action, actor=actor).exists())

    def assert_department_data(self, data, department, administrator):
        self.assertEqual(set(data), self.detail_fields)
        self.assertEqual(data["id"], department.pk)
        self.assertEqual(data["name"], department.name)
        self.assertEqual(data["description"], department.description)
        self.assertEqual(data["is_active"], department.is_active)
        self.assertEqual(data["accepts_new_tasks"], department.accepts_new_tasks)
        # Compare instants, not the particular timezone representation.
        from django.utils.dateparse import parse_datetime
        self.assertEqual(parse_datetime(data["created_at"]), department.created_at)
        self.assertEqual(parse_datetime(data["updated_at"]), department.updated_at)
        if administrator is None:
            self.assertIsNone(data["administrator"])
        else:
            self.assertEqual(data["administrator"], {
                "id": administrator.pk,
                "name": administrator.name,
                "avatar": administrator.avatar,
            })

    def create_case(self, department, creator, case_status=Case.Status.OPEN):
        return Case.objects.create(
            title="Test case", case_type="General",
            lead_department=department, created_by=creator,
            status=case_status,
        )

    def create_task(self, case, department, assigner, assignee, task_status):
        return Task.objects.create(
            case=case, title="Test task", assigned_department=department,
            original_assigner=assigner, current_assignee=assignee,
            status=task_status,
        )


class DepartmentReadAPITests(DepartmentsAPITestData):
    def test_public_list_preserves_registration_fields(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(self.find_department(response.data, self.cardio)),
                         self.public_fields)

    def test_all_approved_staff_receive_full_department_list(self):
        users = (self.doctor, self.nurse, self.admin, self.superuser, self.unassigned)
        index = 0
        while index < len(users):
            with self.subTest(user=users[index].email):
                self.client.force_authenticate(user=users[index])
                response = self.client.get(self.list_url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assert_department_data(
                    self.find_department(response.data, self.cardio),
                    self.cardio, self.admin,
                )
                self.assert_department_data(
                    self.find_department(response.data, self.inactive),
                    self.inactive, None,
                )
            index += 1

    def test_all_approved_staff_can_read_other_department_details(self):
        users = (self.doctor, self.nurse, self.admin, self.superuser, self.unassigned)
        index = 0
        while index < len(users):
            with self.subTest(user=users[index].email):
                self.client.force_authenticate(user=users[index])
                response = self.client.get(self.detail_url(self.radio))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assert_department_data(response.data, self.radio, self.radio_admin)
            index += 1

    def test_inactive_department_details_are_visible(self):
        self.client.force_authenticate(user=self.nurse)
        response = self.client.get(self.detail_url(self.inactive))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_department_data(response.data, self.inactive, None)

    def test_department_without_administrator_returns_null(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(self.detail_url(self.no_admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_department_data(response.data, self.no_admin, None)

    def test_unknown_historical_timestamps_return_null(self):
        Department.objects.filter(pk=self.no_admin.pk).update(
            created_at=None, updated_at=None,
        )
        self.client.force_authenticate(user=self.nurse)
        response = self.client.get(self.detail_url(self.no_admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["created_at"])
        self.assertIsNone(response.data["updated_at"])

    def test_anonymous_cannot_read_protected_details(self):
        response = self.client.get(self.detail_url(self.cardio))
        self.assertIn(response.status_code, (
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN,
        ))

    def test_ineligible_accounts_cannot_read_protected_details(self):
        users = (self.disabled, self.pending, self.rejected)
        index = 0
        while index < len(users):
            with self.subTest(user=users[index].email):
                self.client.force_authenticate(user=users[index])
                response = self.client.get(self.detail_url(self.cardio))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            index += 1

    def test_missing_department_returns_404(self):
        self.client.force_authenticate(user=self.nurse)
        missing_id = Department.objects.latest("pk").pk + 1
        response = self.client.get(f"{self.list_url}{missing_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_requests_do_not_modify_department(self):
        before = self.snapshot(self.cardio)
        self.client.force_authenticate(user=self.nurse)
        self.assertEqual(self.client.get(self.list_url).status_code, 200)
        self.assertEqual(self.client.get(self.detail_url(self.cardio)).status_code, 200)
        self.assert_unchanged(self.cardio, before)


class DepartmentTimestampAPITests(DepartmentsAPITestData):
    def setUp(self):
        self.make_old_timestamp(self.cardio)
        self.make_old_timestamp(self.inactive)
        self.client.force_authenticate(user=self.superuser)

    def test_create_department_sets_timestamps_and_administrator(self):
        response = self.client.post(self.list_url, {
            "name": "Neurology", "description": "Neurological care.",
            "administrator": self.unassigned.pk,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        department = Department.objects.get(pk=response.data["id"])
        self.assertIsNotNone(department.created_at)
        self.assertGreaterEqual(department.updated_at, department.created_at)
        self.assertTrue(department.is_active)
        self.assertTrue(department.accepts_new_tasks)
        self.assertTrue(self.audit_events(department).filter(
            action="department.created", actor=self.superuser,
        ).exists())
        response = self.client.get(self.detail_url(department))
        self.assertEqual(response.status_code, 200)
        self.assert_department_data(response.data, department, self.unassigned)

    def test_edit_name_updates_timestamp(self):
        before = self.snapshot(self.cardio)
        response = self.client.patch(self.detail_url(self.cardio), {
            "name": "Updated Cardiology",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assert_updated(self.cardio, before, "department.updated", self.superuser)
        self.assertEqual(self.cardio.name, "Updated Cardiology")
        self.assert_department_data(response.data, self.cardio, self.admin)

    def test_edit_description_updates_timestamp(self):
        before = self.snapshot(self.cardio)
        response = self.client.patch(self.detail_url(self.cardio), {
            "description": "New description.",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assert_updated(self.cardio, before, "department.updated", self.superuser)
        self.assertEqual(self.cardio.description, "New description.")

    def test_unchanged_edit_preserves_timestamp_and_audit(self):
        before = self.snapshot(self.cardio)
        response = self.client.patch(self.detail_url(self.cardio), {
            "name": self.cardio.name, "description": self.cardio.description,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assert_unchanged(self.cardio, before)

    def test_invalid_edit_preserves_timestamp_and_audit(self):
        before = self.snapshot(self.cardio)
        response = self.client.patch(self.detail_url(self.cardio), {
            "name": self.radio.name,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assert_unchanged(self.cardio, before)

    def test_edit_inactive_department_is_rejected(self):
        before = self.snapshot(self.inactive)
        response = self.client.patch(self.detail_url(self.inactive), {
            "name": "New name",
        }, format="json")
        self.assertEqual(response.status_code, 409)
        self.assert_unchanged(self.inactive, before)

    def test_read_only_timestamps_and_settings_cannot_be_patched(self):
        before = self.snapshot(self.cardio)
        response = self.client.patch(self.detail_url(self.cardio), {
            "created_at": "2000-01-01T00:00:00Z",
            "updated_at": "2000-01-01T00:00:00Z",
            "administrator": self.doctor.pk,
            "is_active": False, "accepts_new_tasks": False,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assert_unchanged(self.cardio, before)

    def test_deactivation_updates_timestamp(self):
        before = self.snapshot(self.cardio)
        response = self.client.post(self.action_url(self.cardio, "deactivate"))
        self.assertEqual(response.status_code, 200)
        self.assert_updated(self.cardio, before, "department.deactivated", self.superuser)
        self.assertFalse(self.cardio.is_active)

    def test_activation_updates_timestamp(self):
        before = self.snapshot(self.inactive)
        response = self.client.post(self.action_url(self.inactive, "activate"))
        self.assertEqual(response.status_code, 200)
        self.assert_updated(self.inactive, before, "department.activated", self.superuser)
        self.assertTrue(self.inactive.is_active)

    def test_repeated_deactivation_preserves_timestamp(self):
        before = self.snapshot(self.inactive)
        response = self.client.post(self.action_url(self.inactive, "deactivate"))
        self.assertEqual(response.status_code, 409)
        self.assert_unchanged(self.inactive, before)

    def test_repeated_activation_preserves_timestamp(self):
        before = self.snapshot(self.cardio)
        response = self.client.post(self.action_url(self.cardio, "activate"))
        self.assertEqual(response.status_code, 409)
        self.assert_unchanged(self.cardio, before)

    def test_pause_task_acceptance_updates_timestamp(self):
        self.client.force_authenticate(user=self.admin)
        before = self.snapshot(self.cardio)
        response = self.client.patch(self.action_url(self.cardio, "task-acceptance"), {
            "accepts_new_tasks": False,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assert_updated(self.cardio, before, "department.task_acceptance.updated", self.admin)
        self.assertFalse(self.cardio.accepts_new_tasks)
        self.assertTrue(self.cardio.is_active)
        self.assert_department_data(response.data, self.cardio, self.admin)

    def test_resume_task_acceptance_updates_timestamp(self):
        Department.objects.filter(pk=self.cardio.pk).update(accepts_new_tasks=False)
        before = self.snapshot(self.cardio)
        response = self.client.patch(self.action_url(self.cardio, "task-acceptance"), {
            "accepts_new_tasks": True,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assert_updated(self.cardio, before, "department.task_acceptance.updated", self.superuser)
        self.assertTrue(self.cardio.accepts_new_tasks)

    def test_unchanged_task_acceptance_preserves_timestamp(self):
        before = self.snapshot(self.cardio)
        response = self.client.patch(self.action_url(self.cardio, "task-acceptance"), {
            "accepts_new_tasks": True,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assert_unchanged(self.cardio, before)

    def test_invalid_task_acceptance_preserves_timestamp(self):
        before = self.snapshot(self.cardio)
        response = self.client.patch(self.action_url(self.cardio, "task-acceptance"), {
            "accepts_new_tasks": "false",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assert_unchanged(self.cardio, before)

    def test_inactive_department_task_acceptance_rejected(self):
        before = self.snapshot(self.inactive)
        response = self.client.patch(self.action_url(self.inactive, "task-acceptance"), {
            "accepts_new_tasks": False,
        }, format="json")
        self.assertEqual(response.status_code, 409)
        self.assert_unchanged(self.inactive, before)

    def test_transfer_to_existing_member_updates_timestamp_and_leader(self):
        self.client.force_authenticate(user=self.admin)
        before = self.snapshot(self.cardio)
        response = self.client.post(self.action_url(self.cardio, "transfer-administrator"), {
            "new_administrator": self.nurse.pk,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assert_updated(self.cardio, before, "department.administrator.transferred", self.admin)
        self.admin_membership.refresh_from_db()
        self.nurse_membership.refresh_from_db()
        self.assertEqual(self.admin_membership.role_id, self.doctor_role.pk)
        self.assertEqual(self.nurse_membership.role_id, self.admin_role.pk)
        response = self.client.get(self.detail_url(self.cardio))
        self.assertEqual(response.status_code, 200)
        self.assert_department_data(response.data, self.cardio, self.nurse)

    def test_transfer_to_external_staff_updates_timestamp(self):
        before = self.snapshot(self.cardio)
        response = self.client.post(self.action_url(self.cardio, "transfer-administrator"), {
            "new_administrator": self.unassigned.pk,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assert_updated(self.cardio, before, "department.administrator.transferred", self.superuser)
        self.assertTrue(DepartmentMembership.objects.filter(
            department=self.cardio, user=self.unassigned, role=self.admin_role,
        ).exists())

    def test_transfer_to_current_administrator_preserves_timestamp(self):
        before = self.snapshot(self.cardio)
        response = self.client.post(self.action_url(self.cardio, "transfer-administrator"), {
            "new_administrator": self.admin.pk,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assert_unchanged(self.cardio, before)

    def test_transfer_to_ineligible_staff_preserves_timestamp(self):
        before = self.snapshot(self.cardio)
        users = (self.disabled, self.pending, self.rejected)
        index = 0
        while index < len(users):
            with self.subTest(user=users[index].email):
                response = self.client.post(self.action_url(self.cardio, "transfer-administrator"), {
                    "new_administrator": users[index].pk,
                }, format="json")
                self.assertEqual(response.status_code, 400)
                self.assert_unchanged(self.cardio, before)
            index += 1

    def test_adding_and_removing_members_does_not_update_department_timestamp(self):
        created_at, updated_at = self.cardio.created_at, self.cardio.updated_at
        response = self.client.post(self.memberships_url, {
            "department": self.cardio.pk, "user": self.unassigned.pk,
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.cardio.refresh_from_db()
        self.assertEqual(self.cardio.created_at, created_at)
        self.assertEqual(self.cardio.updated_at, updated_at)
        membership_id = response.data["id"]
        response = self.client.delete(f"{self.memberships_url}{membership_id}/")
        self.assertEqual(response.status_code, 204)
        self.cardio.refresh_from_db()
        self.assertEqual(self.cardio.created_at, created_at)
        self.assertEqual(self.cardio.updated_at, updated_at)


class DepartmentModificationPermissionTests(DepartmentsAPITestData):
    def test_regular_staff_cannot_create_department(self):
        self.client.force_authenticate(user=self.nurse)
        response = self.client.post(self.list_url, {
            "name": "Unauthorized Department", "administrator": self.nurse.pk,
        }, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Department.objects.filter(name="Unauthorized Department").exists())

    def test_department_admin_can_create_department(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.list_url, {
            "name": "New Department", "administrator": self.unassigned.pk,
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(DepartmentMembership.objects.filter(
            department_id=response.data["id"], user=self.unassigned, role=self.admin_role,
        ).exists())

    def test_non_superusers_cannot_edit_department_information(self):
        before = self.snapshot(self.cardio)
        users = (self.nurse, self.doctor, self.admin)
        index = 0
        while index < len(users):
            with self.subTest(user=users[index].email):
                self.client.force_authenticate(user=users[index])
                response = self.client.patch(self.detail_url(self.cardio), {
                    "name": "Unauthorized name",
                }, format="json")
                self.assertEqual(response.status_code, 403)
                self.assert_unchanged(self.cardio, before)
            index += 1

    def test_non_superusers_cannot_activate_or_deactivate(self):
        active_before = self.snapshot(self.cardio)
        inactive_before = self.snapshot(self.inactive)
        users = (self.nurse, self.doctor, self.admin)
        index = 0
        while index < len(users):
            with self.subTest(user=users[index].email):
                self.client.force_authenticate(user=users[index])
                self.assertEqual(self.client.post(self.action_url(self.cardio, "deactivate")).status_code, 403)
                self.assertEqual(self.client.post(self.action_url(self.inactive, "activate")).status_code, 403)
                self.assert_unchanged(self.cardio, active_before)
                self.assert_unchanged(self.inactive, inactive_before)
            index += 1

    def test_unauthorized_users_cannot_change_task_acceptance(self):
        before = self.snapshot(self.cardio)
        users = (self.nurse, self.doctor, self.radio_admin)
        index = 0
        while index < len(users):
            with self.subTest(user=users[index].email):
                self.client.force_authenticate(user=users[index])
                response = self.client.patch(self.action_url(self.cardio, "task-acceptance"), {
                    "accepts_new_tasks": False,
                }, format="json")
                self.assertEqual(response.status_code, 403)
                self.assert_unchanged(self.cardio, before)
            index += 1

    def test_unauthorized_users_cannot_transfer_administrator(self):
        before = self.snapshot(self.cardio)
        users = (self.nurse, self.doctor, self.radio_admin)
        index = 0
        while index < len(users):
            with self.subTest(user=users[index].email):
                self.client.force_authenticate(user=users[index])
                response = self.client.post(self.action_url(self.cardio, "transfer-administrator"), {
                    "new_administrator": self.unassigned.pk,
                }, format="json")
                self.assertEqual(response.status_code, 403)
                self.assert_unchanged(self.cardio, before)
            index += 1


class DepartmentGovernanceSafeguardTests(DepartmentsAPITestData):
    """Test Member 1 governance safeguards, not workflow operations."""

    def setUp(self):
        self.client.force_authenticate(user=self.superuser)
        self.make_old_timestamp(self.cardio)

    def test_open_case_prevents_department_deactivation(self):
        self.create_case(self.cardio, self.admin)
        before = self.snapshot(self.cardio)
        response = self.client.post(self.action_url(self.cardio, "deactivate"))
        self.assertEqual(response.status_code, 409)
        self.assert_unchanged(self.cardio, before)

    def test_unfinished_incoming_task_prevents_department_deactivation(self):
        case = self.create_case(self.radio, self.radio_admin)
        self.create_task(case, self.cardio, self.radio_admin, self.nurse, Task.Status.ASSIGNED)
        before = self.snapshot(self.cardio)
        response = self.client.post(self.action_url(self.cardio, "deactivate"))
        self.assertEqual(response.status_code, 409)
        self.assert_unchanged(self.cardio, before)

    def test_unfinished_outgoing_task_prevents_deactivation_even_if_case_closed(self):
        case = self.create_case(self.cardio, self.admin, Case.Status.CLOSED)
        self.create_task(case, self.radio, self.admin, self.doctor, Task.Status.IN_PROGRESS)
        before = self.snapshot(self.cardio)
        response = self.client.post(self.action_url(self.cardio, "deactivate"))
        self.assertEqual(response.status_code, 409)
        self.assert_unchanged(self.cardio, before)

    def test_terminal_incoming_tasks_do_not_prevent_deactivation(self):
        case = self.create_case(self.radio, self.radio_admin)
        self.create_task(case, self.cardio, self.radio_admin, self.nurse, Task.Status.COMPLETED)
        self.create_task(case, self.cardio, self.radio_admin, self.nurse, Task.Status.CANCELLED)
        before = self.snapshot(self.cardio)
        response = self.client.post(self.action_url(self.cardio, "deactivate"))
        self.assertEqual(response.status_code, 200)
        self.assert_updated(self.cardio, before, "department.deactivated", self.superuser)
        self.assertFalse(self.cardio.is_active)

    def assert_membership_removal_blocked(self, membership):
        before = self.snapshot(self.cardio)
        audit_count = AuditEvent.objects.count()
        response = self.client.delete(f"{self.memberships_url}{membership.pk}/")
        self.assertEqual(response.status_code, 409)
        self.assertTrue(DepartmentMembership.objects.filter(pk=membership.pk).exists())
        self.assert_unchanged(self.cardio, before)
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_current_assignee_membership_removal_blocked(self):
        case = self.create_case(self.cardio, self.admin)
        self.create_task(case, self.cardio, self.admin, self.nurse, Task.Status.BLOCKED)
        self.assert_membership_removal_blocked(self.nurse_membership)

    def test_original_assigner_membership_removal_blocked(self):
        case = self.create_case(self.cardio, self.nurse)
        self.create_task(case, self.radio, self.nurse, self.doctor, Task.Status.ASSIGNED)
        self.assert_membership_removal_blocked(self.nurse_membership)

    def test_terminal_task_does_not_prevent_membership_removal(self):
        case = self.create_case(self.cardio, self.admin)
        self.create_task(case, self.cardio, self.admin, self.nurse, Task.Status.COMPLETED)
        response = self.client.delete(f"{self.memberships_url}{self.nurse_membership.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(DepartmentMembership.objects.filter(pk=self.nurse_membership.pk).exists())

    def test_superuser_administrator_transfer_cannot_orphan_task(self):
        # A superuser without a clinical profession loses the temporary membership
        # on transfer, so the existing unfinished-task safeguard must apply.
        DepartmentMembership.objects.create(
            department=self.no_admin, user=self.superuser, role=self.admin_role,
        )
        case = self.create_case(self.no_admin, self.superuser)
        self.create_task(case, self.radio, self.superuser, self.doctor, Task.Status.ASSIGNED)
        before = self.snapshot(self.no_admin)
        response = self.client.post(self.action_url(self.no_admin, "transfer-administrator"), {
            "new_administrator": self.unassigned.pk,
        }, format="json")
        self.assertEqual(response.status_code, 409)
        self.assert_unchanged(self.no_admin, before)
