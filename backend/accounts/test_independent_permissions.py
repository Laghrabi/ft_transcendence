
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from accounts.models import Department, DepartmentMembership, Role
from accounts.permissions import (
    can_initiate_task_assignment_to_department,
    can_receive_task_in_department,
    can_view_department_analytics,
    can_view_case,
)


class IndependentPermissionTests(TestCase):

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

    def test_administrator_cannot_view_other_department_analytics(self):
        self.assertFalse(
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

    def test_nurse_cannot_view_department_wide_analytics(self):
        self.assertFalse(
            can_view_department_analytics(
                self.nurse, self.cardiology
            )
        )

    def test_doctor_cannot_view_department_wide_analytics(self):
        self.assertFalse(
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

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="fatima@example.com",
            name="Fatima",
            password="StrongPassword123!",
            is_active=True,
            approval_status="approved",
        )

        # Placeholder until Member 2 implements the Case model.
        self.case = object()

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