from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.test import TestCase
from organizations.models import Department, DepartmentMembership, Role
from .models import AuditEvent
from .services import record_audit_event
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch


class AuditEventTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        self.department = Department.objects.create(
            name="Emergency",
            description="Emergency medical services",
        )

    def test_record_audit_event_creates_event(self):

        event = record_audit_event(
            actor=self.admin,
            action="department.deactivated",
            target=self.department,
            metadata={
                "previous_is_active": True,
                "new_is_active": False,
            },
        )

        self.assertEqual(AuditEvent.objects.count(), 1)
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(
            event.action,
            "department.deactivated",
        )
        self.assertEqual(
            event.target_type,
            "organizations.Department",
        )
        self.assertEqual(
            event.target_id,
            self.department.id,
        )
        self.assertEqual(
            event.metadata["previous_is_active"],
            True,
        )
        self.assertEqual(
            event.metadata["new_is_active"],
            False,
        )
        self.assertIsNotNone(event.created_at)

    def test_metadata_defaults_to_empty_dictionary(self):

        event = record_audit_event(
            actor=self.admin,
            action="department.created",
            target=self.department,
        )

        self.assertEqual(event.metadata, {})

    def test_event_can_have_no_actor(self):

        event = record_audit_event(
            actor=None,
            action="system.event",
            target=self.department,
        )

        self.assertIsNone(event.actor)

    def test_anonymous_actor_is_stored_as_none(self):

        event = record_audit_event(
            actor=AnonymousUser(),
            action="system.event",
            target=self.department,
        )

        self.assertIsNone(event.actor)

    def test_empty_action_is_rejected(self):

        with self.assertRaises(ValueError):
            record_audit_event(
                actor=self.admin,
                action="",
                target=self.department,
            )

        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_whitespace_only_action_is_rejected(self):

        with self.assertRaises(ValueError):
            record_audit_event(
                actor=self.admin,
                action="   ",
                target=self.department,
            )

        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_non_string_action_is_rejected(self):

        with self.assertRaises(ValueError):
            record_audit_event(
                actor=self.admin,
                action=123,
                target=self.department,
            )

        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_unsaved_target_is_rejected(self):

        unsaved_department = Department(
            name="Radiology",
        )

        with self.assertRaises(ValueError):
            record_audit_event(
                actor=self.admin,
                action="department.created",
                target=unsaved_department,
            )

        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_invalid_metadata_is_rejected(self):

        with self.assertRaises(ValueError):
            record_audit_event(
                actor=self.admin,
                action="department.updated",
                target=self.department,
                metadata="invalid metadata",
            )

        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_audit_events_are_ordered_newest_first(self):

        first_event = record_audit_event(
            actor=self.admin,
            action="department.created",
            target=self.department,
        )

        second_event = record_audit_event(
            actor=self.admin,
            action="department.updated",
            target=self.department,
        )

        events = list(AuditEvent.objects.all())

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].id, second_event.id)
        self.assertEqual(events[1].id, first_event.id)

    def test_audit_event_remains_after_actor_deletion(self):

        event = record_audit_event(
            actor=self.admin,
            action="department.created",
            target=self.department,
        )

        event_id = event.id

        self.admin.delete()

        event = AuditEvent.objects.get(id=event_id)

        self.assertIsNone(event.actor)
        self.assertEqual(
            event.action,
            "department.created",
        )

    def test_audit_event_remains_after_target_deletion(self):

        department_id = self.department.id

        event = record_audit_event(
            actor=self.admin,
            action="department.created",
            target=self.department,
        )

        self.department.delete()

        event.refresh_from_db()

        self.assertEqual(
            event.target_type,
            "organizations.Department",
        )
        self.assertEqual(
            event.target_id,
            department_id,
        )

    def test_audit_event_is_rolled_back_with_transaction(self):

        with self.assertRaises(RuntimeError):

            with transaction.atomic():

                record_audit_event(
                    actor=self.admin,
                    action="department.deactivated",
                    target=self.department,
                )

                raise RuntimeError("Simulated failure")

        self.assertEqual(AuditEvent.objects.count(), 0)

class DepartmentTaskAcceptanceAuditTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_superuser(
            email="auditadmin@example.com",
            name="Audit Administrator",
            password="StrongTestPassword123!"
        )

        self.department = Department.objects.create(
            name="Radiology",
            description="Radiology department"
        )

        self.url = reverse(
            "department-task-acceptance",
            kwargs={"department_id": self.department.id}
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_pausing_task_acceptance_creates_audit_event(self):

        response = self.client.patch(
            self.url,
            {"accepts_new_tasks": False},
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        self.department.refresh_from_db()

        self.assertFalse(
            self.department.accepts_new_tasks
        )

        events = AuditEvent.objects.filter(
            actor=self.admin,
            target_type="organizations.Department",
            target_id=self.department.id
        )

        self.assertEqual(events.count(), 1)

        event = events.get()

        self.assertEqual(event.action, "department.task_acceptance.updated")
        self.assertEqual(
            event.metadata,
            {
                "previous_accepts_new_tasks": True,
                "new_accepts_new_tasks": False,
            },
        )

    def test_unchanged_task_acceptance_creates_no_audit_event(self):

        response = self.client.patch(
            self.url,
            {"accepts_new_tasks": True},
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        self.department.refresh_from_db()

        self.assertTrue(self.department.accepts_new_tasks)

        self.assertEqual(
            AuditEvent.objects.count(),
            0
        )

    def test_invalid_task_acceptance_creates_no_audit_event(self):

        response = self.client.patch(
            self.url,
            {"accepts_new_tasks": "invalid"},
            format="json"
        )

        self.assertEqual(response.status_code, 400)

        self.department.refresh_from_db()

        self.assertTrue(self.department.accepts_new_tasks)

        self.assertEqual(
            AuditEvent.objects.count(),
            0
        )
    
    def test_unauthorized_staff_creates_no_audit_event(self):

        User = get_user_model()

        staff = User.objects.create_user(
            email="staff@example.com",
            name="Regular Staff",
            password="StrongTestPassword123!",
            is_active=True,
            approval_status="approved"
        )

        self.client.force_authenticate(user=staff)

        response = self.client.patch(
            self.url,
            {"accepts_new_tasks": False},
            format="json"
        )

        self.assertEqual(response.status_code, 403)

        self.department.refresh_from_db()

        self.assertTrue(self.department.accepts_new_tasks)

        self.assertEqual(AuditEvent.objects.count(), 0)


class AuditEndpointTestBase(TestCase):
    """Shared fixtures and assertions for CareFlow audit API tests."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            email="integration.admin@example.com",
            name="System Administrator",
            password="StrongTestPassword123!",
        )
        self.staff = User.objects.create_user(
            email="integration.staff@example.com",
            name="Approved Staff",
            password="StrongTestPassword123!",
            is_active=True,
            approval_status="approved",
        )
        self.second_staff = User.objects.create_user(
            email="integration.second@example.com",
            name="Second Approved Staff",
            password="StrongTestPassword123!",
            is_active=True,
            approval_status="approved",
        )
        self.department = Department.objects.create(
            name="Cardiology",
            description="Cardiology department",
        )
        self.other_department = Department.objects.create(
            name="Neurology",
            description="Neurology department",
        )
        self.administrator_role = Role.objects.get(name="Administrator")
        self.nurse_role = Role.objects.get(name="Nurse")
        self.doctor_role = Role.objects.get(name="Doctor")
        self.staff.requested_role = self.nurse_role
        self.staff.save(update_fields=["requested_role"])

        self.second_staff.requested_role = self.nurse_role
        self.second_staff.save(update_fields=["requested_role"])
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def url(self, name, **kwargs):
        return reverse(name, kwargs=kwargs or None)

    def assert_audit(self, action, target, metadata=None, actor=None):
        event = AuditEvent.objects.get(
            action=action,
            target_type=target._meta.label,
            target_id=target.pk,
        )
        expected_actor = self.admin if actor is None else actor
        self.assertEqual(event.actor_id, expected_actor.pk)
        if metadata is not None:
            self.assertEqual(event.metadata, metadata)
        return event

    def make_pending_user(self, email="pending.audit@example.com", role=None):
        User = get_user_model()
        return User.objects.create_user(
            email=email,
            name="Pending Registrant",
            password="StrongTestPassword123!",
            is_active=False,
            approval_status="pending",
            requested_department=self.department,
            requested_role=self.nurse_role if role is None else role,
        )


class DepartmentAuditIntegrationTests(AuditEndpointTestBase):

    def test_create_department_logs_administrator_and_state(self):
        response = self.client.post(
            self.url("department-list-create"),
            {
                "name": "Radiology",
                "description": "Medical imaging",
                "administrator": self.staff.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        department = Department.objects.get(pk=response.data["id"])
        membership = DepartmentMembership.objects.get(
            user=self.staff,
            department=department,
            role=self.administrator_role,
        )
        self.assert_audit(
            "department.created",
            department,
            {
                "administrator_id": self.staff.id,
                "administrator_membership_id": membership.id,
                "is_active": True,
                "accepts_new_tasks": True,
            },
        )
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_invalid_department_creation_has_no_audit(self):
        response = self.client.post(
            self.url("department-list-create"),
            {"name": "Radiology", "description": "Medical imaging"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Department.objects.filter(name="Radiology").exists())
        self.assertFalse(AuditEvent.objects.exists())

    def test_edit_department_logs_only_changed_fields(self):
        response = self.client.patch(
            self.url("department-detail", department_id=self.department.id),
            {"name": "Heart Center"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.department.refresh_from_db()
        self.assertEqual(self.department.name, "Heart Center")
        self.assert_audit(
            "department.updated",
            self.department,
            {"changes": {"name": {"old": "Cardiology", "new": "Heart Center"}}},
        )

    def test_unchanged_department_update_does_not_log(self):
        response = self.client.patch(
            self.url("department-detail", department_id=self.department.id),
            {"name": "Cardiology"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuditEvent.objects.exists())

    def test_inactive_department_edit_does_not_log(self):
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])
        response = self.client.patch(
            self.url("department-detail", department_id=self.department.id),
            {"name": "Heart Center"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.department.refresh_from_db()
        self.assertEqual(self.department.name, "Cardiology")
        self.assertFalse(AuditEvent.objects.exists())

    def test_deactivate_department_logs_previous_and_new_state(self):
        response = self.client.post(
            self.url("department-deactivate", department_id=self.department.id)
        )
        self.assertEqual(response.status_code, 200)
        self.department.refresh_from_db()
        self.assertFalse(self.department.is_active)
        self.assert_audit(
            "department.deactivated",
            self.department,
            {"previous_is_active": True, "new_is_active": False},
        )

    def test_activate_department_logs_previous_and_new_state(self):
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])
        response = self.client.post(
            self.url("department-activate", department_id=self.department.id)
        )
        self.assertEqual(response.status_code, 200)
        self.department.refresh_from_db()
        self.assertTrue(self.department.is_active)
        self.assert_audit(
            "department.activated",
            self.department,
            {"previous_is_active": False, "new_is_active": True},
        )

    def test_repeated_department_deactivation_logs_only_once(self):
        url = self.url("department-deactivate", department_id=self.department.id)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 409)
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_already_active_department_cannot_be_activated(self):
        response = self.client.post(
            self.url("department-activate", department_id=self.department.id)
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(AuditEvent.objects.exists())

    def test_non_superuser_cannot_deactivate_department_or_log(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            self.url("department-deactivate", department_id=self.department.id)
        )
        self.assertEqual(response.status_code, 403)
        self.department.refresh_from_db()
        self.assertTrue(self.department.is_active)
        self.assertFalse(AuditEvent.objects.exists())

    def test_deactivation_and_audit_rollback_together(self):
        url = self.url("department-deactivate", department_id=self.department.id)
        with patch(
            "organizations.views.record_audit_event",
            side_effect=RuntimeError("Audit write failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Audit write failed"):
                self.client.post(url)
        self.department.refresh_from_db()
        self.assertTrue(self.department.is_active)
        self.assertFalse(AuditEvent.objects.exists())


class StaffAuditIntegrationTests(AuditEndpointTestBase):

    def test_deactivate_staff_creates_audit(self):
        response = self.client.post(
            self.url("admin-staff-deactivate", user_id=self.staff.id)
        )
        self.assertEqual(response.status_code, 200)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)
        self.assert_audit(
            "staff.deactivated",
            self.staff,
            {"previous_is_active": True, "new_is_active": False},
        )

    def test_activate_staff_creates_audit(self):
        self.staff.is_active = False
        self.staff.save(update_fields=["is_active"])
        response = self.client.post(
            self.url("admin-staff-activate", user_id=self.staff.id)
        )
        self.assertEqual(response.status_code, 200)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)
        self.assert_audit(
            "staff.activated",
            self.staff,
            {"previous_is_active": False, "new_is_active": True},
        )

    def test_deactivating_staff_twice_only_logs_once(self):
        url = self.url("admin-staff-deactivate", user_id=self.staff.id)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 409)
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_administrator_in_inactive_department_cannot_be_deactivated(self):
        DepartmentMembership.objects.create(
            user=self.staff,
            department=self.department,
            role=self.administrator_role,
        )
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])
        response = self.client.post(
            self.url("admin-staff-deactivate", user_id=self.staff.id)
        )
        self.assertEqual(response.status_code, 409)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)
        self.assertFalse(AuditEvent.objects.exists())

    def test_superuser_self_deactivation_is_rejected_without_audit(self):
        response = self.client.post(
            self.url("admin-staff-deactivate", user_id=self.admin.id)
        )
        self.assertEqual(response.status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertFalse(AuditEvent.objects.exists())

    def test_regular_staff_cannot_deactivate_other_staff(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            self.url("admin-staff-deactivate", user_id=self.second_staff.id)
        )
        self.assertEqual(response.status_code, 403)
        self.second_staff.refresh_from_db()
        self.assertTrue(self.second_staff.is_active)
        self.assertFalse(AuditEvent.objects.exists())


class RegistrationAuditIntegrationTests(AuditEndpointTestBase):

    def test_approval_creates_membership_and_audit(self):
        pending = self.make_pending_user()
        response = self.client.post(
            self.url("approve-registration", user_id=pending.id)
        )
        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.approval_status, "approved")
        self.assertTrue(pending.is_active)
        membership = DepartmentMembership.objects.get(
            user=pending, department=self.department, role=self.nurse_role
        )
        self.assert_audit(
            "registration.approved",
            pending,
            {
                "previous_approval_status": "pending",
                "new_approval_status": "approved",
                "previous_is_active": False,
                "new_is_active": True,
                "department_id": self.department.id,
                "role_id": self.nurse_role.id,
                "membership_id": membership.id,
            },
        )
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_rejection_creates_audit_without_membership(self):
        pending = self.make_pending_user()
        response = self.client.post(
            self.url("reject-registration", user_id=pending.id)
        )
        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.approval_status, "rejected")
        self.assertFalse(pending.is_active)
        self.assertFalse(DepartmentMembership.objects.filter(user=pending).exists())
        self.assert_audit(
            "registration.rejected",
            pending,
            {
                "previous_approval_status": "pending",
                "new_approval_status": "rejected",
                "previous_is_active": False,
                "new_is_active": False,
                "requested_department_id": self.department.id,
                "requested_role_id": self.nurse_role.id,
            },
        )

    def test_repeated_registration_approval_does_not_duplicate_audit(self):
        pending = self.make_pending_user()
        url = self.url("approve-registration", user_id=pending.id)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 409)
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_approval_in_inactive_department_creates_no_audit(self):
        pending = self.make_pending_user()
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])
        response = self.client.post(
            self.url("approve-registration", user_id=pending.id)
        )
        self.assertEqual(response.status_code, 409)
        pending.refresh_from_db()
        self.assertEqual(pending.approval_status, "pending")
        self.assertFalse(DepartmentMembership.objects.filter(user=pending).exists())
        self.assertFalse(AuditEvent.objects.exists())

    def test_requesting_administrator_role_cannot_be_approved_or_logged(self):
        pending = self.make_pending_user(role=self.administrator_role)
        response = self.client.post(
            self.url("approve-registration", user_id=pending.id)
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AuditEvent.objects.exists())

    def test_regular_staff_cannot_reject_registration_or_log(self):
        pending = self.make_pending_user()
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            self.url("reject-registration", user_id=pending.id)
        )
        self.assertEqual(response.status_code, 403)
        pending.refresh_from_db()
        self.assertEqual(pending.approval_status, "pending")
        self.assertFalse(AuditEvent.objects.exists())


class MembershipAuditIntegrationTests(AuditEndpointTestBase):

    def setUp(self):
        super().setUp()

        # Give staff members their permanent clinical professions.
        self.staff.requested_role = self.nurse_role
        self.staff.save(update_fields=["requested_role"])

        self.second_staff.requested_role = self.nurse_role
        self.second_staff.save(update_fields=["requested_role"])

    def test_membership_creation_logs_user_department_and_role(self):

        response = self.client.post(
            self.url("membership-list-create"),
            {
                "user": self.staff.id,
                "department": self.department.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        membership = DepartmentMembership.objects.get(
            pk=response.data["id"]
        )

        # The role was assigned automatically.
        self.assertEqual(
            membership.role,
            self.nurse_role
        )

        self.assert_audit(
            "department.membership.created",
            membership,
            {
                "user_id": self.staff.id,
                "department_id": self.department.id,
                "role_id": self.nurse_role.id,
            },
        )

    def test_duplicate_membership_creation_does_not_log(self):

        DepartmentMembership.objects.create(
            user=self.staff,
            department=self.department,
            role=self.nurse_role,
        )

        response = self.client.post(
            self.url("membership-list-create"),
            {
                "user": self.staff.id,
                "department": self.department.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            DepartmentMembership.objects.filter(
                user=self.staff,
                department=self.department,
            ).count(),
            1,
        )

        self.assertFalse(AuditEvent.objects.exists())

    def test_membership_role_change_is_rejected_without_audit(self):

        membership = DepartmentMembership.objects.create(
            user=self.staff,
            department=self.department,
            role=self.nurse_role
        )

        response = self.client.patch(
            self.url(
                "membership-detail",
                membership_id=membership.id
            ),
            {
                "role": self.doctor_role.id
            },
            format="json",
        )

        self.assertEqual(response.status_code, 405)

        membership.refresh_from_db()

        # The staff member remains a Nurse.
        self.assertEqual(
            membership.role,
            self.nurse_role
        )

        # A rejected operation must not generate an audit record.
        self.assertFalse(
            AuditEvent.objects.exists()
        )

    def test_unchanged_membership_role_patch_is_rejected(self):

        membership = DepartmentMembership.objects.create(
            user=self.staff,
            department=self.department,
            role=self.nurse_role
        )

        response = self.client.patch(
            self.url(
                "membership-detail",
                membership_id=membership.id
            ),
            {
                "role": self.nurse_role.id
            },
            format="json",
        )

        self.assertEqual(response.status_code, 405)

        membership.refresh_from_db()

        self.assertEqual(
            membership.role,
            self.nurse_role
        )

        self.assertFalse(
            AuditEvent.objects.exists()
        )

    def test_deleting_membership_keeps_audit_history(self):

        membership = DepartmentMembership.objects.create(
            user=self.staff,
            department=self.department,
            role=self.nurse_role
        )

        membership_id = membership.id

        response = self.client.delete(
            self.url(
                "membership-detail",
                membership_id=membership_id
            )
        )

        self.assertEqual(response.status_code, 204)

        # The department membership is deleted.
        self.assertFalse(
            DepartmentMembership.objects.filter(
                pk=membership_id
            ).exists()
        )

        # The user account still exists.
        self.assertTrue(
            get_user_model().objects.filter(
                pk=self.staff.id
            ).exists()
        )

        # The audit record is preserved.
        self.assert_audit(
            "department.membership.deleted",
            membership,
            {
                "user_id": self.staff.id,
                "department_id": self.department.id,
                "role_id": self.nurse_role.id,
                "role_name": "Nurse",
            },
        )

    def test_only_administrator_cannot_be_deleted_or_logged(self):

        membership = DepartmentMembership.objects.create(
            user=self.staff,
            department=self.department,
            role=self.administrator_role,
        )

        response = self.client.delete(
            self.url(
                "membership-detail",
                membership_id=membership.id
            )
        )

        self.assertEqual(response.status_code, 409)

        self.assertTrue(
            DepartmentMembership.objects.filter(
                pk=membership.id
            ).exists()
        )

        self.assertFalse(
            AuditEvent.objects.exists()
        )

    def test_cannot_add_membership_in_inactive_department(self):

        self.department.is_active = False

        self.department.save(
            update_fields=["is_active"]
        )

        response = self.client.post(
            self.url("membership-list-create"),
            {
                "user": self.staff.id,
                "department": self.department.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.staff,
                department=self.department,
            ).exists()
        )

        self.assertFalse(
            AuditEvent.objects.exists()
        )

    def test_non_administrator_cannot_add_membership_or_log(self):

        self.client.force_authenticate(
            user=self.staff
        )

        response = self.client.post(
            self.url("membership-list-create"),
            {
                "user": self.second_staff.id,
                "department": self.department.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.second_staff,
                department=self.department,
            ).exists()
        )

        self.assertFalse(
            AuditEvent.objects.exists()
        )

class AdministratorTransferAuditIntegrationTests(AuditEndpointTestBase):

    def setUp(self):
        super().setUp()
        self.current_membership = DepartmentMembership.objects.create(
            user=self.staff,
            department=self.department,
            role=self.administrator_role,
        )
        self.transfer_url = self.url(
            "transfer-department-administrator",
            department_id=self.department.id,
        )

    def test_transferring_to_existing_member_records_audit(self):

        existing = DepartmentMembership.objects.create(
            user=self.second_staff,
            department=self.department,
            role=self.nurse_role,
        )

        response = self.client.post(
            self.transfer_url,
            {"new_administrator": self.second_staff.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        # The successor becomes Administrator.
        existing.refresh_from_db()

        self.assertEqual(
            existing.role,
            self.administrator_role,
        )

        # The previous Administrator keeps their membership.
        self.current_membership.refresh_from_db()

        self.assertEqual(
            self.current_membership.role,
            self.nurse_role,
        )

        self.assertTrue(
            get_user_model().objects.filter(
                pk=self.staff.id
            ).exists()
        )

        self.assertEqual(
            DepartmentMembership.objects.filter(
                department=self.department,
                role=self.administrator_role,
            ).count(),
            1,
        )

        self.assert_audit(
            "department.administrator.transferred",
            self.department,
            {
                "previous_administrator_id": self.staff.id,
                "new_administrator_id": self.second_staff.id,
                "previous_membership_id": self.current_membership.id,
                "new_membership_id": existing.id,
                "new_administrator_was_member": True,
                "previous_administrator_remained_member": True,
                "previous_restored_role_id": self.nurse_role.id,
            },
        )

    def test_transferring_to_new_member_records_audit(self):

        response = self.client.post(
            self.transfer_url,
            {"new_administrator": self.second_staff.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        # A new Administrator membership is created for the successor.
        new_membership = DepartmentMembership.objects.get(
            user=self.second_staff,
            department=self.department,
            role=self.administrator_role,
        )

        # The previous Administrator remains a member as Nurse.
        self.current_membership.refresh_from_db()

        self.assertEqual(
            self.current_membership.role,
            self.nurse_role,
        )

        self.assertEqual(
            DepartmentMembership.objects.filter(
                department=self.department,
                role=self.administrator_role,
            ).count(),
            1,
        )

        self.assert_audit(
            "department.administrator.transferred",
            self.department,
            {
                "previous_administrator_id": self.staff.id,
                "new_administrator_id": self.second_staff.id,
                "previous_membership_id": self.current_membership.id,
                "new_membership_id": new_membership.id,
                "new_administrator_was_member": False,
                "previous_administrator_remained_member": True,
                "previous_restored_role_id": self.nurse_role.id,
            },
        )

    def test_department_administrator_can_transfer_their_own_department(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            self.transfer_url,
            {"new_administrator": self.second_staff.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assert_audit(
            "department.administrator.transferred",
            self.department,
            actor=self.staff,
        )

    def test_cannot_transfer_to_current_administrator_or_log(self):
        response = self.client.post(
            self.transfer_url,
            {"new_administrator": self.staff.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(
            DepartmentMembership.objects.filter(pk=self.current_membership.id).exists()
        )
        self.assertFalse(AuditEvent.objects.exists())

    def test_cannot_transfer_in_inactive_department_or_log(self):
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])
        response = self.client.post(
            self.transfer_url,
            {"new_administrator": self.second_staff.id},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(AuditEvent.objects.exists())

    def test_cannot_transfer_without_one_current_administrator(self):
        self.current_membership.delete()
        response = self.client.post(
            self.transfer_url,
            {"new_administrator": self.second_staff.id},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(AuditEvent.objects.exists())

    def test_regular_staff_cannot_transfer_department_or_log(self):
        self.client.force_authenticate(user=self.second_staff)
        response = self.client.post(
            self.transfer_url,
            {"new_administrator": self.second_staff.id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AuditEvent.objects.exists())


class TaskAcceptanceAdditionalAuditTests(AuditEndpointTestBase):

    def test_own_department_administrator_can_pause_and_log(self):
        DepartmentMembership.objects.create(
            user=self.staff,
            department=self.department,
            role=self.administrator_role,
        )
        self.client.force_authenticate(user=self.staff)
        response = self.client.patch(
            self.url("department-task-acceptance", department_id=self.department.id),
            {"accepts_new_tasks": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assert_audit(
            "department.task_acceptance.updated",
            self.department,
            {
                "previous_accepts_new_tasks": True,
                "new_accepts_new_tasks": False,
            },
            actor=self.staff,
        )

    def test_other_department_administrator_cannot_pause_or_log(self):
        DepartmentMembership.objects.create(
            user=self.staff,
            department=self.other_department,
            role=self.administrator_role,
        )
        self.client.force_authenticate(user=self.staff)
        response = self.client.patch(
            self.url("department-task-acceptance", department_id=self.department.id),
            {"accepts_new_tasks": False},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.department.refresh_from_db()
        self.assertTrue(self.department.accepts_new_tasks)
        self.assertFalse(AuditEvent.objects.exists())

    def test_inactive_department_cannot_change_acceptance_or_log(self):
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])
        response = self.client.patch(
            self.url("department-task-acceptance", department_id=self.department.id),
            {"accepts_new_tasks": False},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.department.refresh_from_db()
        self.assertTrue(self.department.accepts_new_tasks)
        self.assertFalse(AuditEvent.objects.exists())
