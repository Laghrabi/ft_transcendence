from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import User, Role, Department, DepartmentMembership
from organizations.views import (
    DepartmentMembershipListCreateView,
    DepartmentMembershipDetailView,
    TransferDepartmentAdministratorView,
)


class DepartmentMembershipRoleTests(TestCase):

    def setUp(self):

        self.factory = APIRequestFactory()

        self.doctor_role, _ = Role.objects.get_or_create(
            name="Doctor"
        )

        self.nurse_role, _ = Role.objects.get_or_create(
            name="Nurse"
        )

        self.administrator_role, _ = Role.objects.get_or_create(
            name="Administrator"
        )

        self.department = Department.objects.create(
            name="Emergency",
            is_active=True
        )

        self.administrator = User.objects.create_user(
            email="administrator@test.com",
            password="TestPassword123!",
            name="Administrator",
            requested_role=self.doctor_role,
            approval_status="approved",
            is_active=True
        )

        self.doctor = User.objects.create_user(
            email="doctor@test.com",
            password="TestPassword123!",
            name="Sara",
            requested_role=self.doctor_role,
            approval_status="approved",
            is_active=True
        )

        self.nurse = User.objects.create_user(
            email="nurse@test.com",
            password="TestPassword123!",
            name="Fatima",
            requested_role=self.nurse_role,
            approval_status="approved",
            is_active=True
        )

        self.administrator_membership = DepartmentMembership.objects.create(
            user=self.administrator,
            department=self.department,
            role=self.administrator_role
        )

        self.audit_patcher = patch(
            "organizations.views.record_audit_event"
        )

        self.audit_mock = self.audit_patcher.start()

        self.addCleanup(
            self.audit_patcher.stop
        )

    def create_membership_request(self, data):

        request = self.factory.post(
            "/memberships/",
            data,
            format="json"
        )

        force_authenticate(
            request,
            user=self.administrator
        )

        return DepartmentMembershipListCreateView.as_view()(
            request
        )

    def transfer_request(self, actor, department, new_administrator):

        request = self.factory.post(
            "/transfer-administrator/",
            {
                "new_administrator": new_administrator.id
            },
            format="json"
        )

        force_authenticate(
            request,
            user=actor
        )

        return TransferDepartmentAdministratorView.as_view()(
            request,
            department_id=department.id
        )

    def test_adding_doctor_assigns_doctor_role(self):

        response = self.create_membership_request({
            "user": self.doctor.id,
            "department": self.department.id
        })

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        membership = DepartmentMembership.objects.get(
            user=self.doctor,
            department=self.department
        )

        self.assertEqual(
            membership.role,
            self.doctor_role
        )

        self.doctor.refresh_from_db()

        self.assertEqual(
            self.doctor.requested_role,
            self.doctor_role
        )

    def test_adding_nurse_assigns_nurse_role(self):

        response = self.create_membership_request({
            "user": self.nurse.id,
            "department": self.department.id
        })

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        membership = DepartmentMembership.objects.get(
            user=self.nurse,
            department=self.department
        )

        self.assertEqual(
            membership.role,
            self.nurse_role
        )

    def test_explicit_role_id_is_rejected(self):

        response = self.create_membership_request({
            "user": self.doctor.id,
            "department": self.department.id,
            "role": self.nurse_role.id
        })

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.doctor,
                department=self.department
            ).exists()
        )

    def test_changing_membership_role_with_patch_is_rejected(self):

        membership = DepartmentMembership.objects.create(
            user=self.nurse,
            department=self.department,
            role=self.nurse_role
        )

        request = self.factory.patch(
            "/memberships/",
            {
                "role": self.doctor_role.id
            },
            format="json"
        )

        force_authenticate(
            request,
            user=self.administrator
        )

        response = DepartmentMembershipDetailView.as_view()(
            request,
            membership_id=membership.id
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

        membership.refresh_from_db()

        self.assertEqual(
            membership.role,
            self.nurse_role
        )

    def test_transfer_restores_previous_administrator_clinical_role(self):

        cardiology = Department.objects.create(
            name="Cardiology",
            is_active=True
        )

        cardiology_membership = DepartmentMembership.objects.create(
            user=self.administrator,
            department=cardiology,
            role=self.doctor_role
        )

        nurse_membership = DepartmentMembership.objects.create(
            user=self.nurse,
            department=self.department,
            role=self.nurse_role
        )

        original_membership_id = self.administrator_membership.id

        response = self.transfer_request(
            self.administrator,
            self.department,
            self.nurse
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.administrator_membership.refresh_from_db()
        nurse_membership.refresh_from_db()
        cardiology_membership.refresh_from_db()

        self.assertEqual(
            self.administrator_membership.id,
            original_membership_id
        )

        self.assertEqual(
            self.administrator_membership.role,
            self.doctor_role
        )

        self.assertEqual(
            nurse_membership.role,
            self.administrator_role
        )

        self.assertEqual(
            cardiology_membership.role,
            self.doctor_role
        )

        self.administrator.refresh_from_db()
        self.nurse.refresh_from_db()

        self.assertEqual(
            self.administrator.requested_role,
            self.doctor_role
        )

        self.assertEqual(
            self.nurse.requested_role,
            self.nurse_role
        )

    def test_superuser_without_profession_loses_temporary_membership(self):

        superuser = User.objects.create_superuser(
            email="superuser@test.com",
            password="TestPassword123!",
            name="Superuser",
            approval_status="approved"
        )

        pediatrics = Department.objects.create(
            name="Pediatrics",
            is_active=True
        )

        temporary_membership = DepartmentMembership.objects.create(
            user=superuser,
            department=pediatrics,
            role=self.administrator_role
        )

        response = self.transfer_request(
            superuser,
            pediatrics,
            self.doctor
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                id=temporary_membership.id
            ).exists()
        )

        self.assertTrue(
            User.objects.filter(
                id=superuser.id
            ).exists()
        )

        new_membership = DepartmentMembership.objects.get(
            user=self.doctor,
            department=pediatrics
        )

        self.assertEqual(
            new_membership.role,
            self.administrator_role
        )

    def test_successful_transfer_calls_audit_service(self):

        response = self.transfer_request(
            self.administrator,
            self.department,
            self.nurse
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.audit_mock.assert_called_once()

        audit_arguments = self.audit_mock.call_args.kwargs

        self.assertEqual(
            audit_arguments["action"],
            "department.administrator.transferred"
        )

        self.assertEqual(
            audit_arguments["metadata"]["previous_administrator_id"],
            self.administrator.id
        )

        self.assertEqual(
            audit_arguments["metadata"]["new_administrator_id"],
            self.nurse.id
        )

        self.assertTrue(
            audit_arguments["metadata"][
                "previous_administrator_remained_member"
            ]
        )

        self.assertEqual(
            audit_arguments["metadata"]["previous_restored_role_id"],
            self.doctor_role.id
        )

    def test_audit_failure_rolls_back_transfer(self):

        self.audit_mock.side_effect = RuntimeError(
            "Audit write failed"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Audit write failed"
        ):
            self.transfer_request(
                self.administrator,
                self.department,
                self.nurse
            )

        self.administrator_membership.refresh_from_db()

        self.assertEqual(
            self.administrator_membership.role,
            self.administrator_role
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.nurse,
                department=self.department
            ).exists()
        )

        self.assertEqual(
            DepartmentMembership.objects.filter(
                department=self.department,
                role=self.administrator_role
            ).count(),
            1
        )
