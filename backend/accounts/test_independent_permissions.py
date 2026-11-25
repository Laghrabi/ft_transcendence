from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from organizations.models import Department, DepartmentMembership, Role
from collaboration.models import Notification
from workflow.models import Blocker, Case, Task
from accounts.permissions import (
    IsApprovedUser,
    _valid_department_id,
    _can_participate_in_department,
    _is_active_task,
    _is_eligible_original_assigner,
    _is_eligible_current_assignee,
    _can_perform_task_recovery,
    _has_global_analytics_access,
    is_active_approved_user,
    can_manage_department,
    can_participate_in_tasks,
    can_receive_new_tasks,
    can_receive_task_in_department,
    can_initiate_task_assignment_to_department,
    can_view_case,
    can_create_case,
    can_update_case,
    can_close_case,
    can_reopen_case,
    can_create_task,
    can_view_task,
    can_update_task,
    can_start_task,
    can_complete_task,
    can_reassign_task,
    can_cancel_task,
    can_view_blocker,
    can_report_blocker,
    can_resolve_blocker,
    can_exceptionally_reassign_task,
    can_exceptionally_cancel_task,
    can_view_case_comments,
    can_create_comment,
    can_view_notifications,
    can_view_notification,
    can_update_notification_state,
    can_view_personal_analytics,
    can_view_department_analytics,
    can_view_hospital_analytics,
)


class PermissionTestData(TestCase):
    """Shared users, departments and memberships; no tests in this class."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.cardiology = Department.objects.create(
            name="Cardiology",
            is_active=True,
            accepts_new_tasks=True,
        )
        cls.radiology = Department.objects.create(
            name="Radiology",
            is_active=True,
            accepts_new_tasks=True,
        )
        cls.emergency = Department.objects.create(
            name="Emergency",
            is_active=True,
            accepts_new_tasks=False,
        )
        cls.archived = Department.objects.create(
            name="Inactive",
            is_active=False,
            accepts_new_tasks=True,
        )

        cls.nurse_role = Role.objects.get(name="Nurse")
        cls.doctor_role = Role.objects.get(name="Doctor")
        cls.admin_role = Role.objects.get(name="Administrator")
        cls.other_role = Role.objects.create(name="Observer")

        cls.superuser = User.objects.create_superuser(
            email="system@example.com",
            name="System Admin",
            password="SafePassword123!",
        )

        cls.cardio_admin = User.objects.create_user(
            email="cardio.admin@example.com",
            name="Cardio Admin",
            password="SafePassword123!",
            approval_status="approved",
            is_active=True,
        )
        cls.radio_admin = User.objects.create_user(
            email="radio.admin@example.com",
            name="Radio Admin",
            password="SafePassword123!",
            approval_status="approved",
            is_active=True,
        )
        cls.emergency_admin = User.objects.create_user(
            email="emergency.admin@example.com",
            name="Emergency Admin",
            password="SafePassword123!",
            approval_status="approved",
            is_active=True,
        )
        cls.archived_admin = User.objects.create_user(
            email="inactive.admin@example.com",
            name="Inactive Admin",
            password="SafePassword123!",
            approval_status="approved",
            is_active=True,
        )
        cls.nurse = User.objects.create_user(
            email="nurse@example.com",
            name="Nurse",
            password="SafePassword123!",
            approval_status="approved",
            is_active=True,
        )
        cls.doctor = User.objects.create_user(
            email="doctor@example.com",
            name="Doctor",
            password="SafePassword123!",
            approval_status="approved",
            is_active=True,
        )
        cls.unassigned_user = User.objects.create_user(
            email="unassigned@example.com",
            name="Unassigned",
            password="SafePassword123!",
            approval_status="approved",
            is_active=True,
        )
        cls.observer = User.objects.create_user(
            email="observer@example.com",
            name="Observer",
            password="SafePassword123!",
            approval_status="approved",
            is_active=True,
        )

        DepartmentMembership.objects.create(
            user=cls.cardio_admin,
            department=cls.cardiology,
            role=cls.admin_role,
        )
        DepartmentMembership.objects.create(
            user=cls.radio_admin,
            department=cls.radiology,
            role=cls.admin_role,
        )
        DepartmentMembership.objects.create(
            user=cls.emergency_admin,
            department=cls.emergency,
            role=cls.admin_role,
        )
        DepartmentMembership.objects.create(
            user=cls.archived_admin,
            department=cls.archived,
            role=cls.admin_role,
        )
        cls.nurse_membership = DepartmentMembership.objects.create(
            user=cls.nurse,
            department=cls.cardiology,
            role=cls.nurse_role,
        )
        DepartmentMembership.objects.create(
            user=cls.doctor,
            department=cls.radiology,
            role=cls.doctor_role,
        )
        DepartmentMembership.objects.create(
            user=cls.observer,
            department=cls.cardiology,
            role=cls.other_role,
        )


class IndependentPermissionTests(PermissionTestData):

    # Recipient eligibility

    def test_nurse_can_receive_in_own_department(self):
        self.assertTrue(
            can_receive_task_in_department(
                self.nurse, self.cardiology
            )
        )

    def test_doctor_can_receive_in_own_department_by_id(self):
        self.assertTrue(
            can_receive_task_in_department(
                self.doctor, self.radiology.pk
            )
        )

    def test_administrator_can_receive_tasks(self):
        self.assertTrue(
            can_receive_task_in_department(
                self.cardio_admin, self.cardiology
            )
        )

    def test_staff_cannot_receive_in_wrong_department(self):
        self.assertFalse(
            can_receive_task_in_department(
                self.nurse, self.radiology
            )
        )

    def test_paused_department_cannot_receive_new_work(self):
        self.assertFalse(
            can_receive_task_in_department(
                self.emergency_admin, self.emergency
            )
        )

    def test_inactive_department_cannot_receive_new_work(self):
        self.assertFalse(
            can_receive_task_in_department(
                self.archived_admin, self.archived
            )
        )

    def test_unassigned_user_cannot_receive(self):
        self.assertFalse(
            can_receive_task_in_department(
                self.unassigned_user, self.cardiology
            )
        )

    def test_pending_user_cannot_receive(self):
        self.nurse.approval_status = "pending"
        self.nurse.save(update_fields=["approval_status"])

        self.assertFalse(
            can_receive_task_in_department(
                self.nurse, self.cardiology
            )
        )

    def test_rejected_user_cannot_receive(self):
        self.nurse.approval_status = "rejected"
        self.nurse.save(update_fields=["approval_status"])

        self.assertFalse(
            can_receive_task_in_department(
                self.nurse, self.cardiology
            )
        )

    def test_deactivated_user_cannot_receive(self):
        self.nurse.is_active = False
        self.nurse.save(update_fields=["is_active"])

        self.assertFalse(
            can_receive_task_in_department(
                self.nurse, self.cardiology
            )
        )

    def test_unknown_role_cannot_receive(self):
        self.assertFalse(
            can_receive_task_in_department(
                self.observer, self.cardiology
            )
        )

    def test_anonymous_cannot_receive(self):
        self.assertFalse(
            can_receive_task_in_department(
                AnonymousUser(), self.cardiology
            )
        )

    def test_superuser_without_membership_cannot_receive_as_staff(self):
        self.assertFalse(
            can_receive_task_in_department(
                self.superuser, self.cardiology
            )
        )

    def test_nonexistent_department_cannot_receive(self):
        self.assertFalse(
            can_receive_task_in_department(
                self.nurse, 999999
            )
        )

    def test_invalid_destination_id_cannot_receive(self):
        self.assertFalse(
            can_receive_task_in_department(self.nurse, None)
        )
        self.assertFalse(
            can_receive_task_in_department(self.nurse, "invalid")
        )
        self.assertFalse(
            can_receive_task_in_department(self.nurse, True)
        )

    # Preliminary assignment eligibility

    def test_nurse_can_initiate_cross_department_assignment(self):
        self.assertTrue(
            can_initiate_task_assignment_to_department(
                self.nurse, self.radiology
            )
        )

    def test_doctor_can_initiate_cross_department_assignment(self):
        self.assertTrue(
            can_initiate_task_assignment_to_department(
                self.doctor, self.cardiology
            )
        )

    def test_department_administrator_can_initiate_assignment(self):
        self.assertTrue(
            can_initiate_task_assignment_to_department(
                self.cardio_admin, self.radiology
            )
        )

    def test_user_without_role_cannot_initiate_assignment(self):
        self.assertFalse(
            can_initiate_task_assignment_to_department(
                self.unassigned_user, self.radiology
            )
        )

    def test_sender_cannot_assign_to_paused_department(self):
        self.assertFalse(
            can_initiate_task_assignment_to_department(
                self.nurse, self.emergency
            )
        )

    def test_sender_cannot_assign_to_inactive_department(self):
        self.assertFalse(
            can_initiate_task_assignment_to_department(
                self.nurse, self.archived
            )
        )

    def test_superuser_without_task_role_cannot_initiate_assignment(self):
        self.assertFalse(
            can_initiate_task_assignment_to_department(
                self.superuser, self.cardiology
            )
        )

    def test_invalid_destination_cannot_start_assignment(self):
        self.assertFalse(
            can_initiate_task_assignment_to_department(
                self.nurse, 0
            )
        )

    # Department analytics permissions

    def test_superuser_can_view_any_active_department_analytics(self):
        self.assertTrue(
            can_view_department_analytics(
                self.superuser, self.radiology
            )
        )

    def test_superuser_can_view_inactive_department_history(self):
        self.assertTrue(
            can_view_department_analytics(
                self.superuser, self.archived
            )
        )

    def test_administrator_can_view_own_department_analytics(self):
        self.assertTrue(
            can_view_department_analytics(
                self.cardio_admin, self.cardiology.pk
            )
        )

    def test_administrator_can_view_other_department_analytics(self):
        self.assertTrue(
            can_view_department_analytics(
                self.cardio_admin, self.radiology
            )
        )

    def test_inactive_department_admin_loses_analytics_access(self):
        self.assertFalse(
            can_view_department_analytics(
                self.archived_admin, self.archived
            )
        )

    def test_nurse_can_view_own_department_analytics(self):
        self.assertTrue(
            can_view_department_analytics(
                self.nurse, self.cardiology
            )
        )

    def test_doctor_can_view_own_department_analytics(self):
        self.assertTrue(
            can_view_department_analytics(
                self.doctor, self.radiology
            )
        )

    def test_pending_admin_cannot_view_analytics(self):
        self.cardio_admin.approval_status = "pending"
        self.cardio_admin.save(update_fields=["approval_status"])

        self.assertFalse(
            can_view_department_analytics(
                self.cardio_admin, self.cardiology
            )
        )

    def test_disabled_admin_cannot_view_analytics(self):
        self.cardio_admin.is_active = False
        self.cardio_admin.save(update_fields=["is_active"])

        self.assertFalse(
            can_view_department_analytics(
                self.cardio_admin, self.cardiology
            )
        )

    def test_unauthenticated_cannot_view_analytics(self):
        self.assertFalse(
            can_view_department_analytics(
                AnonymousUser(), self.cardiology
            )
        )

    def test_unknown_department_has_no_analytics(self):
        self.assertFalse(
            can_view_department_analytics(
                self.superuser, 999999
            )
        )

    def test_invalid_department_has_no_analytics(self):
        self.assertFalse(
            can_view_department_analytics(
                self.superuser, None
            )
        )


class CaseVisibilityPermissionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.user = User.objects.create_user(
            email="fatima@example.com",
            name="Fatima",
            password="StrongPassword123!",
            is_active=True,
            approval_status="approved",
        )

        cls.department = Department.objects.create(
            name="Visibility department",
            is_active=True,
            accepts_new_tasks=True,
        )
        cls.case = Case.objects.create(
            title="Visibility case",
            case_type="examination",
            lead_department=cls.department,
            created_by=cls.user,
        )

    def test_approved_user_can_view_case(self):
        self.assertTrue(
            can_view_case(self.user, self.case)
        )

    def test_pending_user_cannot_view_case(self):
        self.user.approval_status = "pending"
        self.user.save(update_fields=["approval_status"])

        self.assertFalse(
            can_view_case(self.user, self.case)
        )

    def test_rejected_user_cannot_view_case(self):
        self.user.approval_status = "rejected"
        self.user.save(update_fields=["approval_status"])

        self.assertFalse(
            can_view_case(self.user, self.case)
        )

    def test_inactive_user_cannot_view_case(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        self.assertFalse(
            can_view_case(self.user, self.case)
        )

    def test_anonymous_user_cannot_view_case(self):
        self.assertFalse(
            can_view_case(AnonymousUser(), self.case)
        )

    def test_none_user_cannot_view_case(self):
        self.assertFalse(
            can_view_case(None, self.case)
        )

    def test_user_without_department_membership_can_view_case(self):
        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.user
            ).exists()
        )

        self.assertTrue(
            can_view_case(self.user, self.case)
        )

    def test_missing_case_cannot_be_viewed(self):
        self.assertFalse(
            can_view_case(self.user, None)
        )

    def test_closed_case_remains_visible(self):
        self.case.status = Case.Status.CLOSED
        self.case.save(update_fields=["status"])
        self.assertTrue(can_view_case(self.user, self.case))


class AccountAndDepartmentPermissionTests(PermissionTestData):
    """Account eligibility and reusable department checks."""

    def test_account_eligibility_matrix(self):
        users = (self.nurse, self.doctor, self.cardio_admin,
                 self.superuser, self.unassigned_user, AnonymousUser(), None)
        expected = (True, True, True, True, True, False, False)
        i = 0
        while i < len(users):
            with self.subTest(index=i):
                self.assertEqual(is_active_approved_user(users[i]), expected[i])
                request = SimpleNamespace(user=users[i])
                self.assertEqual(IsApprovedUser().has_permission(request, None), expected[i])
            i += 1

    def test_inactive_pending_rejected_accounts_denied(self):
        states = ((False, "approved"), (True, "pending"), (True, "rejected"))
        i = 0
        while i < len(states):
            active, approval = states[i]
            self.nurse.is_active = active
            self.nurse.approval_status = approval
            self.nurse.save(update_fields=["is_active", "approval_status"])
            with self.subTest(active=active, approval=approval):
                self.assertFalse(is_active_approved_user(self.nurse))
                self.assertFalse(IsApprovedUser().has_permission(SimpleNamespace(user=self.nurse), None))
                self.assertFalse(can_participate_in_tasks(self.nurse))
                self.assertFalse(_can_participate_in_department(self.nurse, self.cardiology))
            i += 1

    def test_department_id_validation(self):
        self.assertEqual(_valid_department_id(self.cardiology), self.cardiology.pk)
        self.assertEqual(_valid_department_id(self.cardiology.pk), self.cardiology.pk)
        invalid = (None, True, False, 0, -1, "invalid", "1", 1.5, Department())
        i = 0
        while i < len(invalid):
            with self.subTest(value=invalid[i]):
                self.assertIsNone(_valid_department_id(invalid[i]))
                self.assertFalse(can_manage_department(self.cardio_admin, invalid[i]))
                self.assertFalse(can_receive_new_tasks(invalid[i]))
                self.assertFalse(_can_participate_in_department(self.nurse, invalid[i]))
            i += 1

    def test_administrator_can_manage_own_department(self):
        self.assertTrue(
            can_manage_department(self.cardio_admin, self.cardiology.pk)
        )

    def test_administrator_can_manage_own_department_by_object(self):
        self.assertTrue(
            can_manage_department(self.cardio_admin, self.cardiology)
        )

    def test_administrator_cannot_manage_other_department(self):
        self.assertFalse(
            can_manage_department(self.cardio_admin, self.radiology.pk)
        )

    def test_ordinary_staff_cannot_manage_department(self):
        self.assertFalse(
            can_manage_department(self.nurse, self.cardiology.pk)
        )

    def test_superuser_without_membership_cannot_manage_via_department_helper(self):
        self.assertFalse(
            can_manage_department(self.superuser, self.cardiology.pk)
        )

    def test_inactive_department_admin_cannot_manage(self):
        self.assertFalse(
            can_manage_department(self.archived_admin, self.archived.pk)
        )

    def test_paused_department_can_still_be_managed(self):
        self.assertTrue(
            can_manage_department(self.emergency_admin, self.emergency.pk)
        )

    def test_missing_department_cannot_be_managed(self):
        self.assertFalse(
            can_manage_department(self.cardio_admin, 999999)
        )

    def test_active_department_can_receive_new_tasks(self):
        self.assertTrue(
            can_receive_new_tasks(self.cardiology.pk)
        )

    def test_department_object_can_be_checked_for_new_tasks(self):
        self.assertTrue(
            can_receive_new_tasks(self.cardiology)
        )

    def test_paused_department_cannot_receive_new_tasks(self):
        self.assertFalse(
            can_receive_new_tasks(self.emergency.pk)
        )

    def test_inactive_department_cannot_receive_new_tasks(self):
        self.assertFalse(
            can_receive_new_tasks(self.archived.pk)
        )

    def test_missing_department_cannot_receive_new_tasks(self):
        self.assertFalse(
            can_receive_new_tasks(999999)
        )

    def test_nurse_can_participate_in_own_department(self):
        self.assertTrue(
            _can_participate_in_department(self.nurse, self.cardiology)
        )

    def test_doctor_can_participate_in_own_department(self):
        self.assertTrue(
            _can_participate_in_department(self.doctor, self.radiology.pk)
        )

    def test_admin_can_participate_in_own_department(self):
        self.assertTrue(
            _can_participate_in_department(self.cardio_admin, self.cardiology)
        )

    def test_staff_cannot_participate_in_unrelated_department(self):
        self.assertFalse(
            _can_participate_in_department(self.nurse, self.radiology)
        )

    def test_staff_can_participate_in_paused_department(self):
        self.assertTrue(
            _can_participate_in_department(self.emergency_admin, self.emergency)
        )

    def test_staff_cannot_participate_in_inactive_department(self):
        self.assertFalse(
            _can_participate_in_department(self.archived_admin, self.archived)
        )

    def test_observer_cannot_participate(self):
        self.assertFalse(
            can_participate_in_tasks(self.observer)
        )

    def test_unassigned_user_cannot_participate(self):
        self.assertFalse(
            can_participate_in_tasks(self.unassigned_user)
        )

    def test_superuser_without_membership_cannot_participate(self):
        self.assertFalse(
            can_participate_in_tasks(self.superuser)
        )

    def test_paused_department_staff_can_participate(self):
        self.assertTrue(
            can_participate_in_tasks(self.emergency_admin)
        )

    def test_inactive_department_staff_cannot_participate(self):
        self.assertFalse(
            can_participate_in_tasks(self.archived_admin)
        )

    def test_unrecognized_role_cannot_participate_in_department(self):
        self.assertFalse(
            _can_participate_in_department(self.observer, self.cardiology)
        )

    def test_removed_membership_revokes_participation(self):
        self.nurse_membership.delete()
        self.assertFalse(_can_participate_in_department(self.nurse, self.cardiology))
        self.assertFalse(can_participate_in_tasks(self.nurse))

    def test_deactivated_admin_cannot_manage(self):
        self.cardio_admin.is_active = False
        self.cardio_admin.save(update_fields=["is_active"])
        self.assertFalse(can_manage_department(self.cardio_admin, self.cardiology.pk))


class WorkflowPermissionTestData(PermissionTestData):
    """Real workflow fixtures shared by the object-level test classes."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.case = Case.objects.create(
            title="Cardiology case",
            case_type="examination",
            lead_department=cls.cardiology,
            created_by=cls.nurse,
            status=Case.Status.OPEN,
        )
        cls.task = Task.objects.create(
            case=cls.case,
            title="Perform scan",
            original_assigner=cls.nurse,
            current_assignee=cls.doctor,
            assigned_department=cls.radiology,
            status=Task.Status.ASSIGNED,
        )
        cls.empty_case = Case.objects.create(
            title="Empty case",
            case_type="examination",
            lead_department=cls.cardiology,
            created_by=cls.nurse,
        )

    def _set_task_status(self, status):
        self.task.status = status
        self.task.save(update_fields=["status"])

    def _set_case_status(self, status):
        self.case.status = status
        self.case.save(update_fields=["status"])

    def _create_blocker(self, status=Blocker.Status.OPEN, **extra):
        return Blocker.objects.create(
            task=self.task,
            reason="Equipment unavailable",
            reported_by=self.doctor,
            status=status,
            **extra,
        )

    def _deactivate(self, user):
        user.is_active = False
        user.save(update_fields=["is_active"])
        self.task.refresh_from_db()


class CasePermissionTests(WorkflowPermissionTestData):
    """Case creation, editing, closure and reopening."""

    def test_nurse_can_create_case(self):
        self.assertTrue(
            can_create_case(self.nurse, self.cardiology)
        )

    def test_doctor_can_create_case(self):
        self.assertTrue(
            can_create_case(self.doctor, self.radiology.pk)
        )

    def test_admin_can_create_case(self):
        self.assertTrue(
            can_create_case(self.cardio_admin, self.cardiology)
        )

    def test_staff_cannot_create_case_in_other_department(self):
        self.assertFalse(
            can_create_case(self.doctor, self.cardiology)
        )

    def test_observer_cannot_create_case(self):
        self.assertFalse(
            can_create_case(self.observer, self.cardiology)
        )

    def test_unassigned_staff_cannot_create_case(self):
        self.assertFalse(
            can_create_case(self.unassigned_user, self.cardiology)
        )

    def test_superuser_without_membership_cannot_create_case(self):
        self.assertFalse(
            can_create_case(self.superuser, self.cardiology)
        )

    def test_staff_can_create_case_in_paused_department(self):
        self.assertTrue(
            can_create_case(self.emergency_admin, self.emergency)
        )

    def test_inactive_department_cannot_receive_new_case(self):
        self.assertFalse(
            can_create_case(self.archived_admin, self.archived)
        )

    def test_invalid_department_cannot_receive_case(self):
        self.assertFalse(
            can_create_case(self.nurse, None)
        )

    def test_lead_department_staff_can_update_open_case(self):
        self.assertTrue(
            can_update_case(self.nurse, self.case)
        )

    def test_other_member_of_lead_department_can_update_case(self):
        self.assertTrue(
            can_update_case(self.cardio_admin, self.case)
        )

    def test_external_assignee_cannot_update_case(self):
        self.assertFalse(
            can_update_case(self.doctor, self.case)
        )

    def test_unrelated_admin_cannot_update_case(self):
        self.assertFalse(
            can_update_case(self.radio_admin, self.case)
        )

    def test_superuser_without_membership_cannot_update_case(self):
        self.assertFalse(
            can_update_case(self.superuser, self.case)
        )

    def test_empty_case_can_be_closed(self):
        self.assertTrue(
            can_close_case(self.nurse, self.empty_case)
        )

    def test_external_staff_cannot_close_empty_case(self):
        self.assertFalse(
            can_close_case(self.doctor, self.empty_case)
        )

    def test_open_case_cannot_be_reopened(self):
        self.assertFalse(
            can_reopen_case(self.nurse, self.case)
        )

    def test_case_closure_status_matrix(self):
        statuses = (Task.Status.ASSIGNED, Task.Status.IN_PROGRESS,
                    Task.Status.BLOCKED, Task.Status.COMPLETED, Task.Status.CANCELLED)
        expected = (False, False, False, True, True)
        i = 0
        while i < len(statuses):
            self._set_task_status(statuses[i])
            with self.subTest(status=statuses[i]):
                self.assertEqual(can_close_case(self.nurse, self.case), expected[i])
            i += 1

    def test_case_with_mixed_terminal_and_active_tasks_cannot_close(self):
        self._set_task_status(Task.Status.COMPLETED)
        other = Task.objects.create(
            case=self.case, title="Second task", original_assigner=self.nurse,
            current_assignee=self.doctor, assigned_department=self.radiology,
            status=Task.Status.BLOCKED,
        )
        self.assertFalse(can_close_case(self.nurse, self.case))
        other.status = Task.Status.CANCELLED
        other.save(update_fields=["status"])
        self.assertTrue(can_close_case(self.nurse, self.case))

    def test_closed_case_cannot_update_or_close_but_can_reopen(self):
        self._set_case_status(Case.Status.CLOSED)
        self.assertFalse(can_update_case(self.nurse, self.case))
        self.assertFalse(can_close_case(self.nurse, self.case))
        self.assertTrue(can_reopen_case(self.nurse, self.case))
        self.assertTrue(can_reopen_case(self.cardio_admin, self.case))
        self.assertFalse(can_reopen_case(self.doctor, self.case))
        self.assertFalse(can_reopen_case(self.radio_admin, self.case))

    def test_missing_case_denies_object_permissions(self):
        self.assertFalse(can_view_case(self.nurse, None))
        self.assertFalse(can_update_case(self.nurse, None))
        self.assertFalse(can_close_case(self.nurse, None))
        self.assertFalse(can_reopen_case(self.nurse, None))

    def test_ineligible_staff_cannot_manage_cases(self):
        states = ((False, "approved"), (True, "pending"), (True, "rejected"))
        i = 0
        while i < len(states):
            self.nurse.is_active, self.nurse.approval_status = states[i]
            self.nurse.save(update_fields=["is_active", "approval_status"])
            self.empty_case.status = Case.Status.OPEN
            self.empty_case.save(update_fields=["status"])
            with self.subTest(state=states[i]):
                self.assertFalse(can_create_case(self.nurse, self.cardiology))
                self.assertFalse(can_update_case(self.nurse, self.empty_case))
                self.assertFalse(can_close_case(self.nurse, self.empty_case))
                self.empty_case.status = Case.Status.CLOSED
                self.empty_case.save(update_fields=["status"])
                self.assertFalse(can_reopen_case(self.nurse, self.empty_case))
            i += 1

    def test_removed_membership_prevents_case_management(self):
        self.nurse_membership.delete()
        self.assertFalse(can_create_case(self.nurse, self.cardiology))
        self.assertFalse(can_update_case(self.nurse, self.case))
        self.assertFalse(can_close_case(self.nurse, self.empty_case))
        self._set_case_status(Case.Status.CLOSED)
        self.assertFalse(can_reopen_case(self.nurse, self.case))
        self.assertTrue(can_view_case(self.nurse, self.case))

    def test_inactive_department_prevents_case_management(self):
        self.cardiology.is_active = False
        self.cardiology.save(update_fields=["is_active"])
        self.assertFalse(can_update_case(self.nurse, self.case))
        self.assertFalse(can_close_case(self.nurse, self.empty_case))
        self._set_case_status(Case.Status.CLOSED)
        self.assertFalse(can_reopen_case(self.nurse, self.case))

    def test_paused_task_acceptance_does_not_prevent_case_management(self):
        self.cardiology.accepts_new_tasks = False
        self.cardiology.save(update_fields=["accepts_new_tasks"])
        self.assertTrue(can_update_case(self.nurse, self.case))
        self.assertTrue(can_close_case(self.nurse, self.empty_case))
        self._set_case_status(Case.Status.CLOSED)
        self.assertTrue(can_reopen_case(self.nurse, self.case))


class TaskPermissionTests(WorkflowPermissionTestData):
    """Task creation, ownership and allowed status transitions."""

    def test_lead_member_can_create_cross_department_task(self):
        self.assertTrue(
            can_create_task(self.nurse, self.case, self.doctor, self.radiology)
        )

    def test_lead_member_can_create_self_assigned_task(self):
        self.assertTrue(
            can_create_task(self.nurse, self.case, self.nurse, self.cardiology)
        )

    def test_lead_admin_can_create_task(self):
        self.assertTrue(
            can_create_task(self.cardio_admin, self.case, self.doctor, self.radiology)
        )

    def test_external_assignee_cannot_create_new_task_in_case(self):
        self.assertFalse(
            can_create_task(self.doctor, self.case, self.nurse, self.cardiology)
        )

    def test_unrelated_admin_cannot_create_task(self):
        self.assertFalse(
            can_create_task(self.radio_admin, self.case, self.doctor, self.radiology)
        )

    def test_observer_cannot_create_task(self):
        self.assertFalse(
            can_create_task(self.observer, self.case, self.doctor, self.radiology)
        )

    def test_task_cannot_be_created_without_assignee(self):
        self.assertFalse(
            can_create_task(self.nurse, self.case, None, self.radiology)
        )

    def test_task_cannot_be_created_without_case(self):
        self.assertFalse(
            can_create_task(self.nurse, None, self.doctor, self.radiology)
        )

    def test_task_cannot_be_created_for_wrong_department_recipient(self):
        self.assertFalse(
            can_create_task(self.nurse, self.case, self.doctor, self.cardiology)
        )

    def test_task_cannot_be_created_for_paused_destination(self):
        self.assertFalse(
            can_create_task(self.nurse, self.case, self.emergency_admin, self.emergency)
        )

    def test_task_cannot_be_created_for_inactive_destination(self):
        self.assertFalse(
            can_create_task(self.nurse, self.case, self.archived_admin, self.archived)
        )

    def test_task_cannot_be_created_for_unknown_role(self):
        self.assertFalse(
            can_create_task(self.nurse, self.case, self.observer, self.cardiology)
        )

    def test_task_cannot_be_created_for_invalid_destination(self):
        self.assertFalse(
            can_create_task(self.nurse, self.case, self.doctor, "invalid")
        )

    def test_task_cannot_be_created_by_anonymous_user(self):
        self.assertFalse(
            can_create_task(AnonymousUser(), self.case, self.doctor, self.radiology)
        )

    def test_unrelated_user_can_view_task(self):
        self.assertTrue(
            can_view_task(self.emergency_admin, self.task)
        )

    def test_user_without_membership_can_view_task(self):
        self.assertTrue(
            can_view_task(self.unassigned_user, self.task)
        )

    def test_anonymous_user_cannot_view_task(self):
        self.assertFalse(
            can_view_task(AnonymousUser(), self.task)
        )

    def test_missing_task_cannot_be_viewed(self):
        self.assertFalse(
            can_view_task(self.nurse, None)
        )

    def test_original_assigner_is_eligible(self):
        self.assertTrue(
            _is_eligible_original_assigner(self.nurse, self.task)
        )

    def test_current_assignee_is_eligible(self):
        self.assertTrue(
            _is_eligible_current_assignee(self.doctor, self.task)
        )

    def test_assignee_is_not_original_assigner(self):
        self.assertFalse(
            _is_eligible_original_assigner(self.doctor, self.task)
        )

    def test_assigner_is_not_current_assignee(self):
        self.assertFalse(
            _is_eligible_current_assignee(self.nurse, self.task)
        )

    def test_original_assigner_can_reassign_to_self(self):
        self.assertTrue(
            can_reassign_task(self.nurse, self.task, self.nurse, self.cardiology)
        )

    def test_current_assignee_can_reassign_across_departments(self):
        self.assertTrue(
            can_reassign_task(self.doctor, self.task, self.cardio_admin, self.cardiology)
        )

    def test_current_assignee_can_reassign_within_department(self):
        self.assertTrue(
            can_reassign_task(self.doctor, self.task, self.radio_admin, self.radiology)
        )

    def test_same_assignee_cannot_be_reassigned(self):
        self.assertFalse(
            can_reassign_task(self.nurse, self.task, self.doctor, self.radiology)
        )

    def test_unrelated_admin_cannot_normally_reassign(self):
        self.assertFalse(
            can_reassign_task(self.radio_admin, self.task, self.nurse, self.cardiology)
        )

    def test_superuser_cannot_normally_reassign(self):
        self.assertFalse(
            can_reassign_task(self.superuser, self.task, self.nurse, self.cardiology)
        )

    def test_reassign_to_wrong_department_denied(self):
        self.assertFalse(
            can_reassign_task(self.nurse, self.task, self.cardio_admin, self.radiology)
        )

    def test_reassign_to_paused_department_denied(self):
        self.assertFalse(
            can_reassign_task(self.nurse, self.task, self.emergency_admin, self.emergency)
        )

    def test_reassign_to_inactive_department_denied(self):
        self.assertFalse(
            can_reassign_task(self.nurse, self.task, self.archived_admin, self.archived)
        )

    def test_reassign_without_recipient_denied(self):
        self.assertFalse(
            can_reassign_task(self.nurse, self.task, None, self.radiology)
        )

    def test_reassign_to_invalid_department_denied(self):
        self.assertFalse(
            can_reassign_task(self.nurse, self.task, self.cardio_admin, True)
        )

    def test_closed_case_cannot_receive_new_tasks(self):
        self._set_case_status(Case.Status.CLOSED)
        self.assertFalse(can_create_task(self.nurse, self.case, self.doctor, self.radiology))

    def test_ineligible_task_creators_and_recipients_denied(self):
        states = ((False, "approved"), (True, "pending"), (True, "rejected"))
        i = 0
        while i < len(states):
            active, approval = states[i]
            self.nurse.is_active = active
            self.nurse.approval_status = approval
            self.nurse.save(update_fields=["is_active", "approval_status"])
            with self.subTest(actor="creator", state=states[i]):
                self.assertFalse(can_create_task(self.nurse, self.case, self.doctor, self.radiology))
            self.nurse.is_active = True
            self.nurse.approval_status = "approved"
            self.nurse.save(update_fields=["is_active", "approval_status"])
            self.doctor.is_active = active
            self.doctor.approval_status = approval
            self.doctor.save(update_fields=["is_active", "approval_status"])
            with self.subTest(actor="recipient", state=states[i]):
                self.assertFalse(can_create_task(self.nurse, self.case, self.doctor, self.radiology))
            self.doctor.is_active = True
            self.doctor.approval_status = "approved"
            self.doctor.save(update_fields=["is_active", "approval_status"])
            i += 1

    def test_task_status_permission_matrix(self):
        rows = (
            (Task.Status.ASSIGNED, True, True, True),
            (Task.Status.IN_PROGRESS, True, False, True),
            (Task.Status.BLOCKED, True, False, False),
            (Task.Status.COMPLETED, False, False, False),
            (Task.Status.CANCELLED, False, False, False),
        )
        i = 0
        while i < len(rows):
            status, active, start, complete = rows[i]
            self._set_task_status(status)
            with self.subTest(status=status):
                self.assertEqual(_is_active_task(self.task), active)
                self.assertTrue(can_view_task(self.unassigned_user, self.task))
                self.assertEqual(can_update_task(self.doctor, self.task), active)
                self.assertEqual(can_start_task(self.doctor, self.task), start)
                self.assertEqual(can_complete_task(self.doctor, self.task), complete)
                self.assertEqual(can_reassign_task(self.nurse, self.task, self.cardio_admin, self.cardiology), active)
                self.assertEqual(can_reassign_task(self.doctor, self.task, self.cardio_admin, self.cardiology), active)
                self.assertEqual(can_cancel_task(self.nurse, self.task), active)
            i += 1

    def test_task_ownership_permission_matrix(self):
        actors = (
            (self.nurse, False, True, True),
            (self.doctor, True, True, False),
            (self.cardio_admin, False, False, False),
            (self.radio_admin, False, False, False),
            (self.superuser, False, False, False),
            (self.unassigned_user, False, False, False),
            (AnonymousUser(), False, False, False),
            (None, False, False, False),
        )
        i = 0
        while i < len(actors):
            user, assignee, reassign, cancel = actors[i]
            with self.subTest(actor=i):
                self.assertEqual(can_update_task(user, self.task), assignee)
                self.assertEqual(can_start_task(user, self.task), assignee)
                self.assertEqual(can_complete_task(user, self.task), assignee)
                self.assertEqual(can_reassign_task(user, self.task, self.cardio_admin, self.cardiology), reassign)
                self.assertEqual(can_cancel_task(user, self.task), cancel)
            i += 1

    def test_self_assigned_task_grants_both_ownership_permissions(self):
        self.task.current_assignee = self.nurse
        self.task.assigned_department = self.cardiology
        self.task.save(update_fields=["current_assignee", "assigned_department"])
        self.assertTrue(can_update_task(self.nurse, self.task))
        self.assertTrue(can_start_task(self.nurse, self.task))
        self.assertTrue(can_complete_task(self.nurse, self.task))
        self.assertTrue(can_cancel_task(self.nurse, self.task))
        self.assertTrue(can_reassign_task(self.nurse, self.task, self.doctor, self.radiology))

    def test_open_blocker_prevents_completion_even_if_status_is_inconsistent(self):
        self._create_blocker()
        self.assertFalse(can_complete_task(self.doctor, self.task))
        self._set_task_status(Task.Status.IN_PROGRESS)
        self.assertFalse(can_complete_task(self.doctor, self.task))

    def test_resolved_blockers_do_not_prevent_completion(self):
        self._create_blocker(status=Blocker.Status.RESOLVED)
        self.assertTrue(can_complete_task(self.doctor, self.task))

    def test_one_open_blocker_prevents_completion(self):
        self._create_blocker(status=Blocker.Status.RESOLVED)
        self._create_blocker()
        self.assertFalse(can_complete_task(self.doctor, self.task))

    def test_after_reassignment_old_assignee_loses_ownership(self):
        self.task.current_assignee = self.radio_admin
        self.task.save(update_fields=["current_assignee"])
        self.assertFalse(can_update_task(self.doctor, self.task))
        self.assertFalse(can_complete_task(self.doctor, self.task))
        self.assertFalse(can_reassign_task(self.doctor, self.task, self.nurse, self.cardiology))
        self.assertTrue(can_update_task(self.radio_admin, self.task))
        self.assertTrue(can_complete_task(self.radio_admin, self.task))
        self.assertTrue(can_cancel_task(self.nurse, self.task))

    def test_assignee_deactivation_revokes_ordinary_permissions(self):
        self._deactivate(self.doctor)
        self.assertFalse(can_view_task(self.doctor, self.task))
        self.assertFalse(can_update_task(self.doctor, self.task))
        self.assertFalse(can_start_task(self.doctor, self.task))
        self.assertFalse(can_complete_task(self.doctor, self.task))
        self.assertFalse(can_reassign_task(self.doctor, self.task, self.nurse, self.cardiology))
        self.assertTrue(can_reassign_task(self.nurse, self.task, self.radio_admin, self.radiology))

    def test_assigner_deactivation_revokes_ordinary_permissions(self):
        self._deactivate(self.nurse)
        self.assertFalse(can_cancel_task(self.nurse, self.task))
        self.assertFalse(can_reassign_task(self.nurse, self.task, self.radio_admin, self.radiology))
        self.assertTrue(can_update_task(self.doctor, self.task))
        self.assertTrue(can_reassign_task(self.doctor, self.task, self.radio_admin, self.radiology))

    def test_assignee_membership_removal_revokes_task_permissions(self):
        DepartmentMembership.objects.filter(user=self.doctor, department=self.radiology).delete()
        self.assertFalse(can_update_task(self.doctor, self.task))
        self.assertFalse(can_start_task(self.doctor, self.task))
        self.assertFalse(can_complete_task(self.doctor, self.task))
        self.assertFalse(can_reassign_task(self.doctor, self.task, self.nurse, self.cardiology))
        self.assertTrue(can_view_task(self.doctor, self.task))

    def test_assigner_membership_removal_revokes_task_permissions(self):
        self.nurse_membership.delete()
        self.assertFalse(can_cancel_task(self.nurse, self.task))
        self.assertFalse(can_reassign_task(self.nurse, self.task, self.radio_admin, self.radiology))

    def test_pausing_destination_does_not_revoke_existing_task_permissions(self):
        self.radiology.accepts_new_tasks = False
        self.radiology.save(update_fields=["accepts_new_tasks"])
        self.assertTrue(can_update_task(self.doctor, self.task))
        self.assertTrue(can_start_task(self.doctor, self.task))
        self.assertTrue(can_complete_task(self.doctor, self.task))
        self.assertTrue(can_reassign_task(self.doctor, self.task, self.nurse, self.cardiology))

    def test_inactive_assigned_department_revokes_assignee_permissions(self):
        self.radiology.is_active = False
        self.radiology.save(update_fields=["is_active"])
        self.assertFalse(can_update_task(self.doctor, self.task))
        self.assertFalse(can_complete_task(self.doctor, self.task))
        self.assertTrue(can_reassign_task(self.nurse, self.task, self.cardio_admin, self.cardiology))

    def test_ineligible_new_assignee_cannot_receive_reassignment(self):
        states = ((False, "approved"), (True, "pending"), (True, "rejected"))
        i = 0
        while i < len(states):
            self.radio_admin.is_active, self.radio_admin.approval_status = states[i]
            self.radio_admin.save(update_fields=["is_active", "approval_status"])
            with self.subTest(state=states[i]):
                self.assertFalse(can_reassign_task(self.nurse, self.task, self.radio_admin, self.radiology))
            i += 1

    def test_missing_task_denies_all_mutations(self):
        self.assertFalse(_is_active_task(None))
        self.assertFalse(_is_eligible_original_assigner(self.nurse, None))
        self.assertFalse(_is_eligible_current_assignee(self.doctor, None))
        self.assertFalse(can_update_task(self.doctor, None))
        self.assertFalse(can_start_task(self.doctor, None))
        self.assertFalse(can_complete_task(self.doctor, None))
        self.assertFalse(can_reassign_task(self.nurse, None, self.doctor, self.radiology))
        self.assertFalse(can_cancel_task(self.nurse, None))


    def test_pending_and_rejected_owners_cannot_modify_tasks(self):
        states = ("pending", "rejected")
        i = 0
        while i < len(states):
            self.nurse.approval_status = states[i]
            self.nurse.save(update_fields=["approval_status"])
            self.doctor.approval_status = states[i]
            self.doctor.save(update_fields=["approval_status"])
            with self.subTest(approval_status=states[i]):
                self.assertFalse(can_view_task(self.doctor, self.task))
                self.assertFalse(can_update_task(self.doctor, self.task))
                self.assertFalse(can_start_task(self.doctor, self.task))
                self.assertFalse(can_complete_task(self.doctor, self.task))
                self.assertFalse(can_reassign_task(
                    self.doctor, self.task, self.radio_admin, self.radiology
                ))
                self.assertFalse(can_reassign_task(
                    self.nurse, self.task, self.radio_admin, self.radiology
                ))
                self.assertFalse(can_cancel_task(self.nurse, self.task))
            i += 1

    def test_paused_lead_department_can_assign_to_accepting_department(self):
        self.cardiology.accepts_new_tasks = False
        self.cardiology.save(update_fields=["accepts_new_tasks"])
        self.assertTrue(can_create_task(
            self.nurse, self.case, self.doctor, self.radiology
        ))
        self.assertFalse(can_create_task(
            self.nurse, self.case, self.nurse, self.cardiology
        ))


class BlockerPermissionTests(WorkflowPermissionTestData):
    """Blocker visibility, reporting and resolution."""

    def test_eligible_staff_can_view_blockers_including_external_staff(self):
        blocker = self._create_blocker()
        users = (self.nurse, self.doctor, self.cardio_admin, self.emergency_admin, self.unassigned_user)
        i = 0
        while i < len(users):
            with self.subTest(user=users[i].pk):
                self.assertTrue(can_view_blocker(users[i], blocker))
            i += 1

    def test_ineligible_staff_cannot_view_blockers(self):
        blocker = self._create_blocker()
        self._deactivate(self.doctor)
        self.assertFalse(can_view_blocker(self.doctor, blocker))
        self.assertFalse(can_view_blocker(AnonymousUser(), blocker))
        self.assertFalse(can_view_blocker(None, blocker))
        self.assertFalse(can_view_blocker(self.nurse, None))

    def test_blocker_reporting_status_matrix(self):
        rows = ((Task.Status.ASSIGNED, True), (Task.Status.IN_PROGRESS, True),
                (Task.Status.BLOCKED, True), (Task.Status.COMPLETED, False),
                (Task.Status.CANCELLED, False))
        i = 0
        while i < len(rows):
            status, allowed = rows[i]
            self._set_task_status(status)
            with self.subTest(status=status):
                self.assertEqual(can_report_blocker(self.doctor, self.task), allowed)
            i += 1

    def test_multiple_open_blockers_can_be_reported(self):
        self._set_task_status(Task.Status.BLOCKED)
        self._create_blocker()
        self._create_blocker()
        self.assertEqual(self.task.blockers.filter(status=Blocker.Status.OPEN).count(), 2)
        self.assertTrue(can_report_blocker(self.doctor, self.task))

    def test_only_current_assignee_can_report_and_resolve(self):
        self._set_task_status(Task.Status.BLOCKED)
        blocker = self._create_blocker()
        actors = (self.nurse, self.cardio_admin, self.radio_admin, self.superuser,
                  self.unassigned_user, AnonymousUser(), None)
        i = 0
        while i < len(actors):
            with self.subTest(actor=i):
                self.assertFalse(can_report_blocker(actors[i], self.task))
                self.assertFalse(can_resolve_blocker(actors[i], blocker))
            i += 1
        self.assertTrue(can_report_blocker(self.doctor, self.task))
        self.assertTrue(can_resolve_blocker(self.doctor, blocker))

    def test_blocker_resolution_status_matrix(self):
        blocker = self._create_blocker()
        rows = ((Task.Status.ASSIGNED, False), (Task.Status.IN_PROGRESS, False),
                (Task.Status.BLOCKED, True), (Task.Status.COMPLETED, False),
                (Task.Status.CANCELLED, False))
        i = 0
        while i < len(rows):
            status, allowed = rows[i]
            self._set_task_status(status)
            blocker.refresh_from_db()
            with self.subTest(status=status):
                self.assertEqual(can_resolve_blocker(self.doctor, blocker), allowed)
            i += 1

    def test_resolved_blocker_cannot_be_resolved_again(self):
        self._set_task_status(Task.Status.BLOCKED)
        blocker = self._create_blocker(status=Blocker.Status.RESOLVED)
        self.assertFalse(can_resolve_blocker(self.doctor, blocker))

    def test_new_assignee_can_resolve_old_assignee_blocker(self):
        self._set_task_status(Task.Status.BLOCKED)
        blocker = self._create_blocker()
        self.task.current_assignee = self.radio_admin
        self.task.save(update_fields=["current_assignee"])
        blocker.refresh_from_db()
        self.assertFalse(can_resolve_blocker(self.doctor, blocker))
        self.assertFalse(can_report_blocker(self.doctor, self.task))
        self.assertTrue(can_resolve_blocker(self.radio_admin, blocker))
        self.assertTrue(can_report_blocker(self.radio_admin, self.task))

    def test_designated_resolver_does_not_gain_resolution_permission(self):
        self._set_task_status(Task.Status.BLOCKED)
        blocker = self._create_blocker(resolver_user=self.cardio_admin, resolver_department=self.cardiology)
        self.assertFalse(can_resolve_blocker(self.cardio_admin, blocker))
        self.assertTrue(can_resolve_blocker(self.doctor, blocker))

    def test_ineligible_assignee_cannot_report_or_resolve(self):
        self._set_task_status(Task.Status.BLOCKED)
        blocker = self._create_blocker()
        states = ((False, "approved"), (True, "pending"), (True, "rejected"))
        i = 0
        while i < len(states):
            self.doctor.is_active, self.doctor.approval_status = states[i]
            self.doctor.save(update_fields=["is_active", "approval_status"])
            with self.subTest(state=states[i]):
                self.assertFalse(can_report_blocker(self.doctor, self.task))
                self.assertFalse(can_resolve_blocker(self.doctor, blocker))
            i += 1

    def test_removed_assignee_membership_denies_blocker_actions(self):
        self._set_task_status(Task.Status.BLOCKED)
        blocker = self._create_blocker()
        DepartmentMembership.objects.filter(user=self.doctor, department=self.radiology).delete()
        self.assertFalse(can_report_blocker(self.doctor, self.task))
        self.assertFalse(can_resolve_blocker(self.doctor, blocker))

    def test_missing_objects_deny_blocker_permissions(self):
        self.assertFalse(can_report_blocker(self.doctor, None))
        self.assertFalse(can_resolve_blocker(self.doctor, None))


class ExceptionalRecoveryPermissionTests(WorkflowPermissionTestData):
    """Department-scoped recovery only after account deactivation."""

    def _recover_reassign(self, actor, recipient=None, department=None, reason="Assignee deactivated"):
        if recipient is None:
            recipient = self.cardio_admin
        if department is None:
            department = self.cardiology
        return can_exceptionally_reassign_task(actor, self.task, recipient, department, reason)

    def _recover_cancel(self, actor, reason="Assigner deactivated"):
        return can_exceptionally_cancel_task(actor, self.task, reason)

    def test_recovery_helper_is_department_scoped(self):
        self.assertTrue(_can_perform_task_recovery(self.cardio_admin, self.cardiology.pk))
        self.assertFalse(_can_perform_task_recovery(self.cardio_admin, self.radiology.pk))
        self.assertFalse(_can_perform_task_recovery(self.superuser, self.cardiology.pk))
        self.assertFalse(_can_perform_task_recovery(self.nurse, self.cardiology.pk))
        self.assertFalse(_can_perform_task_recovery(self.archived_admin, self.archived.pk))

    def test_exceptional_recovery_deactivation_matrix(self):
        rows = ((True, True), (True, False), (False, True), (False, False))
        i = 0
        while i < len(rows):
            assigner_active, assignee_active = rows[i]
            self.nurse.is_active = assigner_active
            self.nurse.save(update_fields=["is_active"])
            self.doctor.is_active = assignee_active
            self.doctor.save(update_fields=["is_active"])
            self.task.refresh_from_db()
            with self.subTest(assigner_active=assigner_active, assignee_active=assignee_active):
                self.assertEqual(self._recover_reassign(self.radio_admin), not assignee_active)
                self.assertEqual(self._recover_cancel(self.cardio_admin), not assigner_active)
            i += 1

    def test_exceptional_reassignment_denies_wrong_department_and_non_admins(self):
        self._deactivate(self.doctor)
        actors = (self.cardio_admin, self.emergency_admin, self.archived_admin,
                  self.nurse, self.superuser, self.unassigned_user, AnonymousUser(), None)
        i = 0
        while i < len(actors):
            with self.subTest(actor=i):
                self.assertFalse(self._recover_reassign(actors[i]))
            i += 1
        self.assertTrue(self._recover_reassign(self.radio_admin))

    def test_exceptional_cancellation_denies_wrong_department_and_non_admins(self):
        self._deactivate(self.nurse)
        actors = (self.radio_admin, self.emergency_admin, self.archived_admin,
                  self.doctor, self.superuser, self.unassigned_user, AnonymousUser(), None)
        i = 0
        while i < len(actors):
            with self.subTest(actor=i):
                self.assertFalse(self._recover_cancel(actors[i]))
            i += 1
        self.assertTrue(self._recover_cancel(self.cardio_admin))

    def test_exceptional_recovery_status_matrix(self):
        self._deactivate(self.doctor)
        self._deactivate(self.nurse)
        rows = ((Task.Status.ASSIGNED, True), (Task.Status.IN_PROGRESS, True),
                (Task.Status.BLOCKED, True), (Task.Status.COMPLETED, False),
                (Task.Status.CANCELLED, False))
        i = 0
        while i < len(rows):
            status, allowed = rows[i]
            self._set_task_status(status)
            with self.subTest(status=status):
                self.assertEqual(self._recover_reassign(self.radio_admin), allowed)
                self.assertEqual(self._recover_cancel(self.cardio_admin), allowed)
            i += 1

    def test_exceptional_recovery_requires_nonblank_string_reason(self):
        self._deactivate(self.doctor)
        self._deactivate(self.nurse)
        invalid_reasons = (None, "", "   ", "\n\t", 123, True)
        i = 0
        while i < len(invalid_reasons):
            reason = invalid_reasons[i]
            with self.subTest(reason=reason):
                self.assertFalse(self._recover_reassign(self.radio_admin, reason=reason))
                self.assertFalse(self._recover_cancel(self.cardio_admin, reason=reason))
            i += 1
        self.assertTrue(self._recover_reassign(self.radio_admin, reason="  Coverage needed  "))
        self.assertTrue(self._recover_cancel(self.cardio_admin, reason="  Task no longer needed  "))

    def test_exceptional_reassignment_accepts_eligible_cross_department_recipient(self):
        self._deactivate(self.doctor)
        self.assertTrue(self._recover_reassign(self.radio_admin, self.nurse, self.cardiology))
        self.assertTrue(self._recover_reassign(self.radio_admin, self.radio_admin, self.radiology))

    def test_exceptional_reassignment_rejects_ineligible_recipients(self):
        self._deactivate(self.doctor)
        rows = ((self.doctor, self.radiology), (self.nurse, self.radiology),
                (self.emergency_admin, self.emergency), (self.archived_admin, self.archived),
                (self.observer, self.cardiology), (self.unassigned_user, self.cardiology),
                (None, self.cardiology), (self.nurse, None), (self.nurse, "invalid"))
        i = 0
        while i < len(rows):
            recipient, department = rows[i]
            with self.subTest(index=i):
                self.assertFalse(can_exceptionally_reassign_task(
                    self.radio_admin, self.task, recipient, department, "Recovery"
                ))
            i += 1

    def test_exceptional_reassignment_rejects_inactive_pending_and_rejected_recipients(self):
        self._deactivate(self.doctor)
        states = ((False, "approved"), (True, "pending"), (True, "rejected"))
        i = 0
        while i < len(states):
            self.cardio_admin.is_active, self.cardio_admin.approval_status = states[i]
            self.cardio_admin.save(update_fields=["is_active", "approval_status"])
            with self.subTest(state=states[i]):
                self.assertFalse(self._recover_reassign(self.radio_admin))
            i += 1

    def test_ineligible_administrators_cannot_recover_tasks(self):
        self._deactivate(self.doctor)
        self._deactivate(self.nurse)
        eligible_recipient = get_user_model().objects.create_user(
            email="recovery.recipient@example.com", name="Recovery recipient",
            password="SafePassword123!", is_active=True, approval_status="approved",
        )
        DepartmentMembership.objects.create(
            user=eligible_recipient, department=self.cardiology, role=self.nurse_role,
        )
        self.assertTrue(self._recover_reassign(self.radio_admin, eligible_recipient, self.cardiology))
        self.assertTrue(self._recover_cancel(self.cardio_admin))
        states = ((False, "approved"), (True, "pending"), (True, "rejected"))
        i = 0
        while i < len(states):
            self.radio_admin.is_active, self.radio_admin.approval_status = states[i]
            self.radio_admin.save(update_fields=["is_active", "approval_status"])
            self.cardio_admin.is_active, self.cardio_admin.approval_status = states[i]
            self.cardio_admin.save(update_fields=["is_active", "approval_status"])
            with self.subTest(state=states[i]):
                self.assertFalse(self._recover_reassign(self.radio_admin, eligible_recipient, self.cardiology))
                self.assertFalse(self._recover_cancel(self.cardio_admin))
            i += 1

    def test_inactive_departments_cannot_authorize_recovery(self):
        self._deactivate(self.doctor)
        self._deactivate(self.nurse)
        self.radiology.is_active = False
        self.radiology.save(update_fields=["is_active"])
        self.assertFalse(self._recover_reassign(self.radio_admin))
        self.cardiology.is_active = False
        self.cardiology.save(update_fields=["is_active"])
        self.assertFalse(self._recover_cancel(self.cardio_admin))

    def test_paused_department_can_still_authorize_recovery(self):
        self._deactivate(self.doctor)
        self._deactivate(self.nurse)
        self.radiology.accepts_new_tasks = False
        self.radiology.save(update_fields=["accepts_new_tasks"])
        self.assertTrue(self._recover_reassign(self.radio_admin))
        self.cardiology.accepts_new_tasks = False
        self.cardiology.save(update_fields=["accepts_new_tasks"])
        self.assertTrue(self._recover_cancel(self.cardio_admin))

    def test_membership_removal_alone_does_not_trigger_account_recovery(self):
        # Current policy: the exceptional functions check account is_active only.
        self.nurse_membership.delete()
        DepartmentMembership.objects.filter(user=self.doctor, department=self.radiology).delete()
        self.assertFalse(self._recover_reassign(self.radio_admin))
        self.assertFalse(self._recover_cancel(self.cardio_admin))

    def test_missing_task_cannot_be_recovered(self):
        self.assertFalse(can_exceptionally_reassign_task(
            self.radio_admin, None, self.cardio_admin, self.cardiology, "Recovery"
        ))
        self.assertFalse(can_exceptionally_cancel_task(self.cardio_admin, None, "Recovery"))


    def test_pending_or_rejected_owner_does_not_trigger_deactivation_recovery(self):
        # Recovery is limited to inactive accounts, not approval changes alone.
        states = ("pending", "rejected")
        i = 0
        while i < len(states):
            self.nurse.approval_status = states[i]
            self.nurse.save(update_fields=["approval_status"])
            self.doctor.approval_status = states[i]
            self.doctor.save(update_fields=["approval_status"])
            self.task.refresh_from_db()
            with self.subTest(approval_status=states[i]):
                self.assertFalse(self._recover_reassign(self.radio_admin))
                self.assertFalse(self._recover_cancel(self.cardio_admin))
            i += 1


class CommentPermissionTests(WorkflowPermissionTestData):
    """Case comment visibility and creation permissions."""

    def test_eligible_users_can_view_and_comment_on_open_case(self):
        users = (self.nurse, self.doctor, self.cardio_admin, self.emergency_admin,
                 self.superuser, self.unassigned_user)
        i = 0
        while i < len(users):
            with self.subTest(user=users[i].pk):
                self.assertTrue(can_view_case_comments(users[i], self.case))
                self.assertTrue(can_create_comment(users[i], self.case))
            i += 1

    def test_closed_case_comments_are_read_only(self):
        self._set_case_status(Case.Status.CLOSED)
        self.assertTrue(can_view_case_comments(self.doctor, self.case))
        self.assertFalse(can_create_comment(self.doctor, self.case))
        self.assertFalse(can_create_comment(self.cardio_admin, self.case))

    def test_ineligible_accounts_cannot_view_or_create_comments(self):
        states = ((False, "approved"), (True, "pending"), (True, "rejected"))
        i = 0
        while i < len(states):
            self.nurse.is_active, self.nurse.approval_status = states[i]
            self.nurse.save(update_fields=["is_active", "approval_status"])
            with self.subTest(state=states[i]):
                self.assertFalse(can_view_case_comments(self.nurse, self.case))
                self.assertFalse(can_create_comment(self.nurse, self.case))
            i += 1

    def test_anonymous_and_missing_objects_deny_comments(self):
        self.assertFalse(can_view_case_comments(AnonymousUser(), self.case))
        self.assertFalse(can_create_comment(AnonymousUser(), self.case))
        self.assertFalse(can_view_case_comments(None, self.case))
        self.assertFalse(can_create_comment(None, self.case))
        self.assertFalse(can_view_case_comments(self.nurse, None))
        self.assertFalse(can_create_comment(self.nurse, None))


class NotificationPermissionTests(PermissionTestData):
    """Notification list eligibility and strict recipient ownership."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.notification = Notification.objects.create(
            recipient=cls.nurse,
            message="A new task has been assigned to you.",
            is_read=False,
        )

    def test_eligible_staff_can_access_own_notification_list(self):
        self.assertTrue(
            can_view_notifications(self.nurse)
        )

    def test_eligible_staff_without_membership_can_access_notification_list(self):
        self.assertTrue(
            can_view_notifications(self.unassigned_user)
        )

    def test_recipient_can_view_notification(self):
        self.assertTrue(
            can_view_notification(self.nurse, self.notification)
        )

    def test_recipient_can_update_notification_state(self):
        self.assertTrue(
            can_update_notification_state(self.nurse, self.notification)
        )

    def test_missing_notification_cannot_be_viewed(self):
        self.assertFalse(
            can_view_notification(self.nurse, None)
        )

    def test_missing_notification_state_cannot_be_updated(self):
        self.assertFalse(
            can_update_notification_state(self.nurse, None)
        )

    def test_other_staff_and_admins_cannot_access_or_modify_notification(self):
        users = (self.doctor, self.cardio_admin, self.radio_admin, self.superuser,
                 self.unassigned_user, AnonymousUser(), None)
        i = 0
        while i < len(users):
            with self.subTest(actor=i):
                self.assertFalse(can_view_notification(users[i], self.notification))
                self.assertFalse(can_update_notification_state(users[i], self.notification))
            i += 1

    def test_recipient_can_access_notification_regardless_of_read_state(self):
        self.notification.is_read = True
        self.notification.save(update_fields=["is_read"])
        self.assertTrue(can_view_notification(self.nurse, self.notification))
        self.assertTrue(can_update_notification_state(self.nurse, self.notification))

    def test_ineligible_recipient_cannot_access_notifications(self):
        states = ((False, "approved"), (True, "pending"), (True, "rejected"))
        i = 0
        while i < len(states):
            self.nurse.is_active, self.nurse.approval_status = states[i]
            self.nurse.save(update_fields=["is_active", "approval_status"])
            with self.subTest(state=states[i]):
                self.assertFalse(can_view_notifications(self.nurse))
                self.assertFalse(can_view_notification(self.nurse, self.notification))
                self.assertFalse(can_update_notification_state(self.nurse, self.notification))
            i += 1

    def test_anonymous_and_none_users_cannot_access_notification_list(self):
        self.assertFalse(can_view_notifications(AnonymousUser()))
        self.assertFalse(can_view_notifications(None))


class AnalyticsPermissionTests(PermissionTestData):
    """Personal, department and hospital-wide analytics authorization."""

    def test_global_analytics_access_matrix(self):
        rows = ((self.nurse, False), (self.doctor, False), (self.cardio_admin, True),
                (self.radio_admin, True), (self.emergency_admin, True),
                (self.archived_admin, False), (self.superuser, True),
                (self.unassigned_user, False), (self.observer, False),
                (AnonymousUser(), False), (None, False))
        i = 0
        while i < len(rows):
            user, allowed = rows[i]
            with self.subTest(actor=i):
                self.assertEqual(_has_global_analytics_access(user), allowed)
                self.assertEqual(can_view_hospital_analytics(user), allowed)
            i += 1

    def test_all_eligible_users_can_view_own_personal_analytics(self):
        users = (self.nurse, self.doctor, self.cardio_admin, self.superuser,
                 self.unassigned_user, self.observer, self.archived_admin)
        i = 0
        while i < len(users):
            with self.subTest(user=users[i].pk):
                self.assertTrue(can_view_personal_analytics(users[i], users[i]))
            i += 1

    def test_only_global_analytics_actors_can_view_other_users_personal_analytics(self):
        rows = ((self.nurse, self.doctor, False), (self.doctor, self.nurse, False),
                (self.nurse, self.cardio_admin, False), (self.cardio_admin, self.nurse, True),
                (self.cardio_admin, self.doctor, True), (self.radio_admin, self.nurse, True),
                (self.superuser, self.nurse, True), (self.archived_admin, self.nurse, False),
                (self.unassigned_user, self.nurse, False), (self.observer, self.nurse, False))
        i = 0
        while i < len(rows):
            user, target, allowed = rows[i]
            with self.subTest(actor=user.pk, target=target.pk):
                self.assertEqual(can_view_personal_analytics(user, target), allowed)
            i += 1

    def test_global_analytics_can_view_deactivated_staff_history(self):
        self.nurse.is_active = False
        self.nurse.save(update_fields=["is_active"])
        self.assertTrue(can_view_personal_analytics(self.cardio_admin, self.nurse))
        self.assertTrue(can_view_personal_analytics(self.superuser, self.nurse))
        self.assertFalse(can_view_personal_analytics(self.nurse, self.nurse))

    def test_department_analytics_scope_matrix(self):
        departments = (self.cardiology, self.radiology, self.emergency, self.archived)
        rows = ((self.nurse, (True, False, False, False)),
                (self.doctor, (False, True, False, False)),
                (self.cardio_admin, (True, True, True, True)),
                (self.radio_admin, (True, True, True, True)),
                (self.emergency_admin, (True, True, True, True)),
                (self.superuser, (True, True, True, True)),
                (self.archived_admin, (False, False, False, False)),
                (self.observer, (False, False, False, False)),
                (self.unassigned_user, (False, False, False, False)))
        i = 0
        while i < len(rows):
            user, expected = rows[i]
            j = 0
            while j < len(departments):
                with self.subTest(user=user.pk, department=departments[j].pk):
                    self.assertEqual(can_view_department_analytics(user, departments[j]), expected[j])
                j += 1
            i += 1

    def test_staff_can_view_analytics_of_multiple_own_departments(self):
        DepartmentMembership.objects.create(user=self.nurse, department=self.radiology, role=self.nurse_role)
        self.assertTrue(can_view_department_analytics(self.nurse, self.cardiology))
        self.assertTrue(can_view_department_analytics(self.nurse, self.radiology))
        self.assertFalse(can_view_department_analytics(self.nurse, self.emergency))

    def test_paused_department_staff_can_view_own_analytics(self):
        DepartmentMembership.objects.create(user=self.nurse, department=self.emergency, role=self.nurse_role)
        self.assertTrue(can_view_department_analytics(self.nurse, self.emergency))

    def test_ordinary_staff_cannot_view_inactive_own_department_analytics(self):
        self.cardiology.is_active = False
        self.cardiology.save(update_fields=["is_active"])
        self.assertFalse(can_view_department_analytics(self.nurse, self.cardiology))

    def test_removed_administrator_membership_revokes_global_analytics(self):
        DepartmentMembership.objects.filter(user=self.cardio_admin, department=self.cardiology).delete()
        self.assertFalse(can_view_hospital_analytics(self.cardio_admin))
        self.assertFalse(can_view_personal_analytics(self.cardio_admin, self.doctor))
        self.assertFalse(can_view_department_analytics(self.cardio_admin, self.radiology))

    def test_ineligible_admin_and_superuser_cannot_access_analytics(self):
        actors = (self.cardio_admin, self.superuser)
        states = ((False, "approved"), (True, "pending"), (True, "rejected"))
        i = 0
        while i < len(actors):
            user = actors[i]
            j = 0
            while j < len(states):
                user.is_active, user.approval_status = states[j]
                user.save(update_fields=["is_active", "approval_status"])
                with self.subTest(user=user.pk, state=states[j]):
                    self.assertFalse(can_view_hospital_analytics(user))
                    self.assertFalse(can_view_department_analytics(user, self.cardiology))
                    self.assertFalse(can_view_personal_analytics(user, self.nurse))
                    self.assertFalse(can_view_personal_analytics(user, user))
                j += 1
            i += 1

    def test_invalid_analytics_targets_are_denied(self):
        self.assertFalse(can_view_personal_analytics(self.cardio_admin, None))
        self.assertFalse(can_view_personal_analytics(self.superuser, get_user_model()()))
        self.assertFalse(can_view_personal_analytics(AnonymousUser(), self.nurse))
        self.assertFalse(can_view_personal_analytics(None, self.nurse))
        invalid = (None, True, False, -1, 0, "invalid", 999999)
        i = 0
        while i < len(invalid):
            with self.subTest(department=invalid[i]):
                self.assertFalse(can_view_department_analytics(self.superuser, invalid[i]))
                self.assertFalse(can_view_department_analytics(self.nurse, invalid[i]))
            i += 1
