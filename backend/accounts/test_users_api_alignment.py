from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from organizations.models import (
    Department,
    DepartmentMembership,
    Role,
)

from accounts.permissions import (
    can_view_inactive_staff,
    can_be_department_admin,
)


class UsersAPIAlignmentTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.cardiology = Department.objects.create(
            name="Cardiology"
        )

        cls.radiology = Department.objects.create(
            name="Radiology"
        )

        cls.doctor_role = Role.objects.get(name="Doctor")
        cls.nurse_role = Role.objects.get(name="Nurse")
        cls.admin_role = Role.objects.get(
            name="Administrator"
        )

        cls.admin = User.objects.create_user(
            email="admin@example.com",
            name="Cardiology Admin",
            password="StrongPassword123!",
            approval_status="approved",
            is_active=True,
            requested_role=cls.doctor_role,
        )

        cls.nurse = User.objects.create_user(
            email="nurse@example.com",
            name="Cardiology Nurse",
            password="StrongPassword123!",
            approval_status="approved",
            is_active=True,
            requested_role=cls.nurse_role,
        )

        cls.inactive_doctor = User.objects.create_user(
            email="inactive@example.com",
            name="Inactive Doctor",
            password="StrongPassword123!",
            approval_status="approved",
            is_active=False,
            requested_role=cls.doctor_role,
        )

        cls.pending_user = User.objects.create_user(
            email="pending@example.com",
            name="Pending Nurse",
            password="StrongPassword123!",
            approval_status="pending",
            is_active=False,
            requested_role=cls.nurse_role,
            requested_department=cls.cardiology,
        )

        DepartmentMembership.objects.create(
            user=cls.admin,
            department=cls.cardiology,
            role=cls.admin_role,
        )

        DepartmentMembership.objects.create(
            user=cls.nurse,
            department=cls.cardiology,
            role=cls.nurse_role,
        )

        DepartmentMembership.objects.create(
            user=cls.inactive_doctor,
            department=cls.radiology,
            role=cls.doctor_role,
        )

    def find_staff(self, data, user_id):
        index = 0

        while index < len(data):
            if data[index]["id"] == user_id:
                return data[index]

            index += 1

        return None

    def test_admin_can_view_inactive_staff(self):
        self.assertTrue(
            can_view_inactive_staff(self.admin)
        )

    def test_nurse_cannot_view_inactive_staff(self):
        self.assertFalse(
            can_view_inactive_staff(self.nurse)
        )

    def test_inactive_department_admin_loses_access(self):
        self.cardiology.is_active = False
        self.cardiology.save(update_fields=["is_active"])

        self.assertFalse(
            can_view_inactive_staff(self.admin)
        )

    def test_admin_can_list_external_inactive_staff(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/auth/users/")

        self.assertEqual(response.status_code, 200)

        staff = self.find_staff(
            response.data,
            self.inactive_doctor.id,
        )

        self.assertIsNotNone(staff)
        self.assertFalse(staff["is_active"])
        self.assertTrue(staff["can_activate"])
        self.assertFalse(staff["can_deactivate"])

    def test_regular_staff_cannot_list_inactive_staff(self):
        self.client.force_authenticate(user=self.nurse)

        response = self.client.get("/api/auth/users/")

        self.assertEqual(response.status_code, 200)

        self.assertIsNone(
            self.find_staff(
                response.data,
                self.inactive_doctor.id,
            )
        )

    def test_admin_profession_and_badge(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/auth/users/")

        self.assertEqual(response.status_code, 200)

        staff = self.find_staff(
            response.data,
            self.admin.id,
        )

        self.assertEqual(staff["profession"], "Doctor")
        self.assertTrue(staff["is_department_admin"])
        self.assertFalse(staff["can_deactivate"])

    def test_admin_can_deactivate_own_department_staff(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/auth/users/")

        self.assertEqual(response.status_code, 200)

        staff = self.find_staff(
            response.data,
            self.nurse.id,
        )

        self.assertTrue(staff["can_deactivate"])
        self.assertFalse(staff["can_activate"])

    def test_admin_cannot_deactivate_external_staff(self):
        self.inactive_doctor.is_active = True
        self.inactive_doctor.save(
            update_fields=["is_active"]
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/auth/users/")

        self.assertEqual(response.status_code, 200)

        staff = self.find_staff(
            response.data,
            self.inactive_doctor.id,
        )

        self.assertFalse(staff["can_deactivate"])

    def test_pending_staff_excluded_from_directory(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/auth/users/")

        self.assertEqual(response.status_code, 200)

        self.assertIsNone(
            self.find_staff(
                response.data,
                self.pending_user.id,
            )
        )

    def test_admin_can_view_inactive_staff_details(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            f"/api/auth/users/{self.inactive_doctor.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_active"])

        memberships = response.data["department_memberships"]

        self.assertEqual(len(memberships), 1)
        self.assertEqual(
            memberships[0]["department_name"],
            "Radiology",
        )
        self.assertEqual(
            memberships[0]["role_name"],
            "Doctor",
        )

    def test_regular_staff_cannot_view_inactive_details(self):
        self.client.force_authenticate(user=self.nurse)

        response = self.client.get(
            f"/api/auth/users/{self.inactive_doctor.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_me_returns_administrative_information(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_superuser"])
        self.assertTrue(response.data["is_department_admin"])
        self.assertEqual(response.data["profession"], "Doctor")

    def test_pending_registration_contains_new_fields(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            "/api/auth/registrations/pending/"
        )

        self.assertEqual(response.status_code, 200)

        staff = self.find_staff(
            response.data,
            self.pending_user.id,
        )

        self.assertIsNotNone(staff)
        self.assertIn("avatar", staff)
        self.assertIn("date_joined", staff)

    def test_doctor_can_be_department_admin(self):
        self.assertTrue(
            can_be_department_admin(self.admin)
        )

    def test_nurse_can_be_department_admin(self):
        self.assertTrue(
            can_be_department_admin(self.nurse)
        )

    def test_inactive_staff_cannot_be_department_admin(self):
        self.assertFalse(
            can_be_department_admin(self.inactive_doctor)
        )

    def test_pending_staff_cannot_be_department_admin(self):
        self.assertFalse(
            can_be_department_admin(self.pending_user)
        )

    def test_staff_without_profession_cannot_be_department_admin(self):
        self.nurse.requested_role = None

        self.assertFalse(
            can_be_department_admin(self.nurse)
        )

    def test_superuser_can_be_department_admin(self):
        User = get_user_model()

        superuser = User.objects.create_superuser(
            email="superuser@example.com",
            name="System Superuser",
            password="StrongPassword123!",
        )

        self.assertTrue(
            can_be_department_admin(superuser)
        )

    def test_staff_list_returns_admin_candidate_eligibility(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/auth/users/")

        self.assertEqual(response.status_code, 200)

        active_staff = self.find_staff(
            response.data,
            self.nurse.id,
        )

        inactive_staff = self.find_staff(
            response.data,
            self.inactive_doctor.id,
        )

        self.assertTrue(
            active_staff["can_be_department_admin"]
        )

        self.assertFalse(
            inactive_staff["can_be_department_admin"]
        )