from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework import status
from django.test import TestCase, Client, override_settings
import json
from types import SimpleNamespace
from django.contrib.auth.models import AnonymousUser
from .serializers import UserProfileSerializer
from django.urls import reverse
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from .models import Department, Role, DepartmentMembership, RolePermission
from unittest.mock import patch


class AuthenticationTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.password = "Sara123!Test"
        self.user = User.objects.create_user("sara@example.com", "Sara123!Test", name="Sara",
                                             is_active=True, approval_status="approved")
    
    # 1. Login succeeds with valid credentials
    def test_login_success(self):
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": self.user.email,
                "password": "Sara123!Test"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Login successful.")
        self.assertIn("sessionid", self.client.cookies)
    
    # 2. CSRF endpoint returns a token
    def test_csrf_token_endpoint(self):
        response = self.client.get("/api/auth/csrf/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrf_token", response.json())
        self.assertIn("csrftoken", response.cookies)
    
    # 3. Login fails with an incorrect password
    def test_login_invalid_password(self):
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": self.user.email,
                "password": "WrongPassword"
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    # 4. Inactive accounts cannot log in
    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            "/api/auth/login/",
            {
                "email": self.user.email,
                "password": self.password
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["error"],
            "Your account is disabled."
        )
    
    # 5. Authenticated users can access /me/
    def test_me_authenticated(self):
        self.client.post(
            "/api/auth/login/",
            {
                "email": self.user.email,
                "password": self.password
            },
            format="json"
        )

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(response.data["name"], self.user.name)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertNotIn("password", response.data)
    
    # 6. Unauthenticated users cannot access /me/
    def test_me_unauthenticated(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    # 7. Logout invalidates the session
    def test_logout_invalidates_session(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {
                "email": self.user.email,
                "password": self.password
            },
            format="json"
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        response = self.client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Logout successful")

        me_response = self.client.get("/api/auth/me/")

        self.assertEqual(me_response.status_code, status.HTTP_403_FORBIDDEN)
    
    # 8. Login rejects requests without CSRF protection
    def test_login_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)

        response = client.post(
            "/api/auth/login/",
            {
                "email": self.user.email,
                "password": self.password
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    # 9. Logout rejects requests without a CSRF token
    def test_logout_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)

        csrf_response = client.get("/api/auth/csrf/")
        csrf_token = csrf_response.json()["csrf_token"]

        login_response = client.post(
            "/api/auth/login/",
            {
                "email": self.user.email,
                "password": self.password
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        logout_response = client.post("/api/auth/logout/")

        self.assertEqual(logout_response.status_code, status.HTTP_403_FORBIDDEN)

        me_response = client.get("/api/auth/me/")

        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
    
    # 10. Login and logout succeed with valid CSRF tokens
    def test_login_logout_with_valid_csrf(self):
        client = APIClient(enforce_csrf_checks=True)

        csrf_response = client.get("/api/auth/csrf/")
        csrf_token = csrf_response.json()["csrf_token"]

        login_response = client.post(
            "/api/auth/login/",
            {
                "email": self.user.email,
                "password": self.password
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        csrf_response = client.get("/api/auth/csrf/")
        csrf_token = csrf_response.json()["csrf_token"]

        logout_response = client.post(
            "/api/auth/logout/",
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        me_response = client.get("/api/auth/me/")

        self.assertEqual(me_response.status_code, status.HTTP_403_FORBIDDEN)


class UserManagerTests(TestCase):

    def test_create_user_without_email(self):
        User = get_user_model()

        with self.assertRaisesMessage(ValueError, "An email address is required"):
            User.objects.create_user(
                email=None,
                password="Sara123!Test",
                name="Sara"
            )

    def test_create_user_without_name(self):
        User = get_user_model()

        with self.assertRaisesMessage(ValueError, "A name is required"):
            User.objects.create_user(
                email="sara@example.com",
                password="Sara123!Test"
            )

    def test_create_superuser_without_staff_permission(self):
        User = get_user_model()

        with self.assertRaisesMessage(ValueError, "Superuser must have is_staff=True"):
            User.objects.create_superuser(
                email="admin@example.com",
                password="Admin123!Test",
                name="Admin",
                is_staff=False
            )

    def test_create_superuser_without_superuser_permission(self):
        User = get_user_model()

        with self.assertRaisesMessage(ValueError, "Superuser must have is_superuser=True"):
            User.objects.create_superuser(
                email="admin@example.com",
                password="Admin123!Test",
                name="Admin",
                is_superuser=False
            )


class RegistrationTests(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.User = get_user_model()

        self.register_url = "/api/auth/register/"
        self.login_url = "/api/auth/login/"
        self.csrf_url = "/api/auth/csrf/"

        self.emergency = Department.objects.create(
            name="Emergency",
            description="Emergency medical services",
        )

        self.nurse = Role.objects.get(name="Nurse")

        self.valid_data = {
            "name": "Sara",
            "email": "sara.new@example.com",
            "password": "SecurePassword123!",
            "requested_department": self.emergency.id,
            "requested_role": self.nurse.id,
        }

    # =====================================================
    # Helpers
    # =====================================================

    def get_csrf_token(self):
        response = self.client.get(self.csrf_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", self.client.cookies)

        return response.json()["csrf_token"]

    def register(self, data=None, include_csrf=True):
        if data is None:
            data = self.valid_data.copy()

        headers = {}

        if include_csrf:
            headers["HTTP_X_CSRFTOKEN"] = self.get_csrf_token()

        return self.client.post(
            self.register_url,
            data=json.dumps(data),
            content_type="application/json",
            **headers
        )

    def login(self, email, password):
        return self.client.post(
            self.login_url,
            data=json.dumps({
                "email": email,
                "password": password,
            }),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.get_csrf_token(),
        )

    # =====================================================
    # 1. Successful registration
    # =====================================================

    def test_successful_registration(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(
            email=self.valid_data["email"]
        )

        self.assertEqual(user.name, "Sara")
        self.assertEqual(user.approval_status, "pending")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        self.assertEqual(
            user.requested_department,
            self.emergency
        )

        self.assertEqual(
            user.requested_role,
            self.nurse
        )

        self.assertEqual(response.json()["id"], user.id)

        self.assertEqual(
            response.json()["message"],
            "Registration successful. Awaiting administrator approval."
        )

        self.assertEqual(self.User.objects.count(), 1)

    def test_registration_does_not_create_membership(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(
            email=self.valid_data["email"]
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=user
            ).exists()
        )

        self.assertEqual(user.approval_status, "pending")
        self.assertFalse(user.is_active)

    # =====================================================
    # 2. Password security
    # =====================================================

    def test_password_is_hashed(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(
            email=self.valid_data["email"]
        )

        self.assertNotEqual(
            user.password,
            self.valid_data["password"]
        )

        self.assertTrue(
            user.check_password(self.valid_data["password"])
        )

    def test_password_is_not_returned(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(
            email=self.valid_data["email"]
        )

        self.assertNotIn("password", response.json())

        self.assertNotIn(
            self.valid_data["password"],
            response.content.decode()
        )

        self.assertNotIn(
            user.password,
            response.content.decode()
        )

    # =====================================================
    # 3. Prevent privilege escalation
    # =====================================================

    def test_client_cannot_assign_admin_privileges(self):
        data = self.valid_data.copy()

        data.update({
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
            "approval_status": "approved",
        })

        response = self.register(data)

        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(
            email=self.valid_data["email"]
        )

        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.approval_status, "pending")

    def test_administrator_role_cannot_be_requested(self):
        admin_role = Role.objects.create(
            name="Hospital Administrator",
            description="Reserved administrator role.",
        )

        data = self.valid_data.copy()
        data["requested_role"] = admin_role.id

        response = self.register(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("requested_role", response.json())
        self.assertEqual(self.User.objects.count(), 0)

    # =====================================================
    # 4. Login restrictions
    # =====================================================

    def test_pending_user_cannot_login(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)

        login_response = self.login(
            self.valid_data["email"],
            self.valid_data["password"]
        )

        self.assertEqual(login_response.status_code, 403)

        self.assertEqual(
            login_response.json()["error"],
            "Your account is awaiting administrator approval."
        )

    def test_approved_user_can_login(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(
            email=self.valid_data["email"]
        )

        user.approval_status = "approved"
        user.is_active = True

        user.save(
            update_fields=["approval_status", "is_active"]
        )

        login_response = self.login(
            self.valid_data["email"],
            self.valid_data["password"]
        )

        self.assertEqual(login_response.status_code, 200)

    def test_pending_user_cannot_login_even_if_active(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(
            email=self.valid_data["email"]
        )

        user.is_active = True
        user.save(update_fields=["is_active"])

        login_response = self.login(
            self.valid_data["email"],
            self.valid_data["password"]
        )

        self.assertEqual(login_response.status_code, 403)

        self.assertEqual(
            login_response.json()["error"],
            "Your account is awaiting administrator approval."
        )

    # =====================================================
    # 5. Email validation
    # =====================================================

    def test_duplicate_email_is_rejected(self):
        first_response = self.register()

        self.assertEqual(first_response.status_code, 201)

        second_response = self.register()

        self.assertEqual(second_response.status_code, 400)
        self.assertIn("email", second_response.json())
        self.assertEqual(self.User.objects.count(), 1)

    def test_invalid_email_is_rejected(self):
        data = self.valid_data.copy()
        data["email"] = "not-an-email"

        response = self.register(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        self.assertEqual(self.User.objects.count(), 0)

    # =====================================================
    # 6. Required fields
    # =====================================================

    def test_missing_required_fields_are_rejected(self):
        fields = (
            "name",
            "email",
            "password",
            "requested_department",
            "requested_role",
        )

        index = 0

        while index < len(fields):
            field = fields[index]

            with self.subTest(missing_field=field):
                data = self.valid_data.copy()
                del data[field]

                response = self.register(data)

                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
                self.assertEqual(self.User.objects.count(), 0)

            index += 1

    def test_blank_required_fields_are_rejected(self):
        fields = (
            "name",
            "email",
            "password",
            "requested_department",
            "requested_role",
        )

        index = 0

        while index < len(fields):
            field = fields[index]

            with self.subTest(blank_field=field):
                data = self.valid_data.copy()
                data[field] = ""

                response = self.register(data)

                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
                self.assertEqual(self.User.objects.count(), 0)

            index += 1

    # =====================================================
    # 7. Department validation
    # =====================================================

    def test_nonexistent_department_is_rejected(self):
        data = self.valid_data.copy()
        data["requested_department"] = 999999

        response = self.register(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("requested_department", response.json())
        self.assertEqual(self.User.objects.count(), 0)

    def test_invalid_department_type_is_rejected(self):
        data = self.valid_data.copy()
        data["requested_department"] = "not-an-id"

        response = self.register(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("requested_department", response.json())
        self.assertEqual(self.User.objects.count(), 0)

    def test_null_department_is_rejected(self):
        data = self.valid_data.copy()
        data["requested_department"] = None

        response = self.register(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("requested_department", response.json())
        self.assertEqual(self.User.objects.count(), 0)

    # =====================================================
    # 8. Role validation
    # =====================================================

    def test_nonexistent_role_is_rejected(self):
        data = self.valid_data.copy()
        data["requested_role"] = 999999

        response = self.register(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("requested_role", response.json())
        self.assertEqual(self.User.objects.count(), 0)

    def test_invalid_role_type_is_rejected(self):
        data = self.valid_data.copy()
        data["requested_role"] = "not-an-id"

        response = self.register(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("requested_role", response.json())
        self.assertEqual(self.User.objects.count(), 0)

    def test_null_role_is_rejected(self):
        data = self.valid_data.copy()
        data["requested_role"] = None

        response = self.register(data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("requested_role", response.json())
        self.assertEqual(self.User.objects.count(), 0)

    # =====================================================
    # 9. Password validation
    # =====================================================

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[
            {
                "NAME": (
                    "django.contrib.auth.password_validation."
                    "MinimumLengthValidator"
                ),
                "OPTIONS": {"min_length": 8}
            },
            {
                "NAME": (
                    "django.contrib.auth.password_validation."
                    "NumericPasswordValidator"
                )
            },
            {
                "NAME": (
                    "django.contrib.auth.password_validation."
                    "UserAttributeSimilarityValidator"
                )
            }
        ]
    )
    def test_weak_passwords_are_rejected(self):
        weak_passwords = (
            "abc",
            "123456789",
            "sara.new@example.com",
        )

        index = 0

        while index < len(weak_passwords):
            password = weak_passwords[index]

            with self.subTest(password=password):
                data = self.valid_data.copy()
                data["password"] = password

                response = self.register(data)

                self.assertEqual(response.status_code, 400)
                self.assertIn("password", response.json())
                self.assertEqual(self.User.objects.count(), 0)

            index += 1

    # =====================================================
    # 10. CSRF protection
    # =====================================================

    def test_registration_without_csrf_is_rejected(self):
        response = self.register(include_csrf=False)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.User.objects.count(), 0)

    def test_csrf_cookie_without_header_is_rejected(self):
        self.get_csrf_token()

        response = self.register(include_csrf=False)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.User.objects.count(), 0)

    def test_invalid_csrf_token_is_rejected(self):
        self.get_csrf_token()

        response = self.client.post(
            self.register_url,
            data=json.dumps(self.valid_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN="invalid-token"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.User.objects.count(), 0)

    # =====================================================
    # 11. HTTP method restrictions
    # =====================================================

    def test_get_registration_is_not_allowed(self):
        response = self.client.get(self.register_url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.User.objects.count(), 0)



class PendingRegistrationsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.pending_url = "/api/auth/registrations/pending/"

        cls.emergency = Department.objects.create(
            name="Emergency",
            description="Emergency medical services",
        )

        cls.cardiology = Department.objects.create(
            name="Cardiology",
            description="Heart-related medical services",
        )

        cls.nurse_role = Role.objects.get(name="Nurse")

        cls.doctor_role = Role.objects.get(name="Doctor")

        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="Admin123!Test",
            name="Admin"
        )

        cls.nurse = User.objects.create_user(
            email="nurse@example.com",
            password="Nurse123!Test",
            name="Nurse",
            is_active=True,
            approval_status="approved"
        )

        cls.staff_user = User.objects.create_user(
            email="staff@example.com",
            password="Staff123!Test",
            name="Staff Member",
            is_active=True,
            is_staff=True,
            approval_status="approved"
        )

        cls.pending_sara = User.objects.create_user(
            email="sara@example.com",
            password="Sara123!Test",
            name="Sara",
            requested_department=cls.emergency,
            requested_role=cls.nurse_role,
        )

        cls.pending_lina = User.objects.create_user(
            email="lina@example.com",
            password="Lina123!Test",
            name="Lina",
            requested_department=cls.cardiology,
            requested_role=cls.doctor_role,
        )

        cls.rejected_user = User.objects.create_user(
            email="rejected@example.com",
            password="Rejected123!Test",
            name="Rejected User",
            approval_status="rejected"
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    # =====================================================
    # 1. Administrator can access the endpoint
    # =====================================================

    def test_admin_can_list_pending_registrations(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    # =====================================================
    # 2. Only pending registrations are returned
    # =====================================================

    def test_only_pending_users_are_returned(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        received_ids = set()

        index = 0
        while index < len(data):
            received_ids.add(data[index]["id"])
            index += 1

        expected_ids = {
            self.pending_sara.id,
            self.pending_lina.id
        }

        self.assertEqual(received_ids, expected_ids)

    # =====================================================
    # 3. Response contains permitted fields
    # =====================================================

    def test_pending_list_excludes_sensitive_fields(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(len(data), 2)

        expected_fields = {
            "id",
            "name",
            "email",
            "approval_status",
            "requested_department",
            "requested_department_name",
            "requested_role",
            "requested_role_name",
        }

        index = 0
        while index < len(data):
            self.assertEqual(
                set(data[index].keys()),
                expected_fields
            )

            self.assertEqual(
                data[index]["approval_status"],
                "pending"
            )

            self.assertNotIn("password", data[index])
            self.assertNotIn("is_superuser", data[index])
            self.assertNotIn("is_staff", data[index])

            index += 1

    # =====================================================
    # 4. Requested department and role are returned
    # =====================================================

    def test_pending_users_include_requested_department_and_role(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        registrations = {}

        index = 0
        while index < len(data):
            registrations[data[index]["id"]] = data[index]
            index += 1

        sara_data = registrations[self.pending_sara.id]

        self.assertEqual(
            sara_data["requested_department"],
            self.emergency.id
        )

        self.assertEqual(
            sara_data["requested_department_name"],
            "Emergency"
        )

        self.assertEqual(
            sara_data["requested_role"],
            self.nurse_role.id
        )

        self.assertEqual(
            sara_data["requested_role_name"],
            "Nurse"
        )

        lina_data = registrations[self.pending_lina.id]

        self.assertEqual(
            lina_data["requested_department"],
            self.cardiology.id
        )

        self.assertEqual(
            lina_data["requested_department_name"],
            "Cardiology"
        )

        self.assertEqual(
            lina_data["requested_role"],
            self.doctor_role.id
        )

        self.assertEqual(
            lina_data["requested_role_name"],
            "Doctor"
        )

    # =====================================================
    # 5. Older registrations with missing choices
    # =====================================================

    def test_pending_user_without_department_or_role(self):
        User = get_user_model()

        old_user = User.objects.create_user(
            email="old@example.com",
            password="OldUser123!Test",
            name="Old Pending User",
        )

        self.client.force_login(self.admin)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        old_user_data = None

        index = 0
        while index < len(data):
            if data[index]["id"] == old_user.id:
                old_user_data = data[index]
                break

            index += 1

        self.assertIsNotNone(old_user_data)

        self.assertIsNone(
            old_user_data["requested_department"]
        )

        self.assertIsNone(
            old_user_data["requested_department_name"]
        )

        self.assertIsNone(
            old_user_data["requested_role"]
        )

        self.assertIsNone(
            old_user_data["requested_role_name"]
        )

    # =====================================================
    # 6. Regular users cannot access
    # =====================================================

    def test_regular_user_cannot_list_pending_registrations(self):
        self.client.force_login(self.nurse)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            response.json()["message"],
            "Administrator access required."
        )

    # =====================================================
    # 7. is_staff alone does not grant administrator access
    # =====================================================

    def test_staff_user_without_superuser_cannot_access(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            response.json()["message"],
            "Administrator access required."
        )

    # =====================================================
    # 8. Unauthenticated users cannot access
    # =====================================================

    def test_unauthenticated_user_cannot_access(self):
        response = self.client.get(self.pending_url)

        self.assertIn(response.status_code, [401, 403])

    # =====================================================
    # 9. Empty pending list returns an empty array
    # =====================================================

    def test_empty_pending_registrations(self):
        User = get_user_model()

        User.objects.filter(
            approval_status="pending"
        ).delete()

        self.client.force_login(self.admin)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])



class ApproveRegistrationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.emergency = Department.objects.create(
            name="Emergency",
            description="Emergency medical services",
        )

        cls.nurse_role = Role.objects.get(
            name="Nurse"
        )

        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="Admin123!Test",
            name="Admin"
        )

        cls.nurse = User.objects.create_user(
            email="nurse@example.com",
            password="Nurse123!Test",
            name="Nurse",
            approval_status="approved",
            is_active=True
        )

        cls.staff_user = User.objects.create_user(
            email="staff@example.com",
            password="Staff123!Test",
            name="Staff Member",
            approval_status="approved",
            is_active=True,
            is_staff=True
        )

        cls.pending_user = User.objects.create_user(
            email="sara@example.com",
            password="Sara123!Test",
            name="Sara",
            requested_department=cls.emergency,
            requested_role=cls.nurse_role
        )

        cls.approved_user = User.objects.create_user(
            email="approved@example.com",
            password="Approved123!Test",
            name="Approved User",
            approval_status="approved",
            is_active=True
        )

        cls.rejected_user = User.objects.create_user(
            email="rejected@example.com",
            password="Rejected123!Test",
            name="Rejected User",
            approval_status="rejected",
            is_active=False
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    # =====================================================
    # Helpers
    # =====================================================

    def approval_url(self, user_id):
        return f"/api/auth/registrations/{user_id}/approve/"

    def get_csrf_token(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        return response.json()["csrf_token"]

    def approve(self, user_id, include_csrf=True):
        headers = {}

        if include_csrf:
            headers["HTTP_X_CSRFTOKEN"] = self.get_csrf_token()

        return self.client.post(
            self.approval_url(user_id),
            **headers
        )

    # =====================================================
    # 1. Successful approval
    # =====================================================

    def test_admin_can_approve_pending_registration(self):
        self.client.force_login(self.admin)

        response = self.approve(self.pending_user.id)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json()["message"],
            "Registration approved successfully."
        )

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "approved"
        )
        self.assertTrue(self.pending_user.is_active)

        self.assertFalse(self.pending_user.is_staff)
        self.assertFalse(self.pending_user.is_superuser)

    # =====================================================
    # 2. Approval creates the correct membership
    # =====================================================

    def test_approval_creates_department_membership(self):
        self.client.force_login(self.admin)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

        response = self.approve(self.pending_user.id)

        self.assertEqual(response.status_code, 200)

        memberships = DepartmentMembership.objects.filter(
            user=self.pending_user
        )

        self.assertEqual(memberships.count(), 1)

        membership = memberships.get()

        self.assertEqual(
            membership.department,
            self.emergency
        )

        self.assertEqual(
            membership.role,
            self.nurse_role
        )

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.requested_department,
            self.emergency
        )

        self.assertEqual(
            self.pending_user.requested_role,
            self.nurse_role
        )

    # =====================================================
    # 3. Approved user can log in
    # =====================================================

    def test_approved_user_can_login_after_approval(self):
        self.client.force_login(self.admin)

        response = self.approve(self.pending_user.id)
        self.assertEqual(response.status_code, 200)

        self.client.logout()

        login_response = self.client.post(
            "/api/auth/login/",
            data=json.dumps({
                "email": "sara@example.com",
                "password": "Sara123!Test"
            }),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.get_csrf_token()
        )

        self.assertEqual(login_response.status_code, 200)

    # =====================================================
    # 4. Regular user cannot approve
    # =====================================================

    def test_regular_user_cannot_approve(self):
        self.client.force_login(self.nurse)

        response = self.approve(self.pending_user.id)

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            response.json()["message"],
            "Administrator access required."
        )

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )
        self.assertFalse(self.pending_user.is_active)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 5. is_staff alone is not enough
    # =====================================================

    def test_staff_user_cannot_approve(self):
        self.client.force_login(self.staff_user)

        response = self.approve(self.pending_user.id)

        self.assertEqual(response.status_code, 403)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 6. Unauthenticated users cannot approve
    # =====================================================

    def test_unauthenticated_user_cannot_approve(self):
        response = self.approve(self.pending_user.id)

        self.assertIn(response.status_code, [401, 403])

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )
        self.assertFalse(self.pending_user.is_active)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 7. Nonexistent user returns 404
    # =====================================================

    def test_approve_nonexistent_user(self):
        self.client.force_login(self.admin)

        response = self.approve(999999)

        self.assertEqual(response.status_code, 404)

    # =====================================================
    # 8. Already approved user returns 409
    # =====================================================

    def test_cannot_approve_already_approved_user(self):
        self.client.force_login(self.admin)

        response = self.approve(self.approved_user.id)

        self.assertEqual(response.status_code, 409)

        self.assertEqual(
            response.json()["message"],
            "Only pending registrations can be approved."
        )

        self.approved_user.refresh_from_db()

        self.assertEqual(
            self.approved_user.approval_status,
            "approved"
        )

    # =====================================================
    # 9. Rejected user cannot be approved
    # =====================================================

    def test_cannot_approve_rejected_user(self):
        self.client.force_login(self.admin)

        response = self.approve(self.rejected_user.id)

        self.assertEqual(response.status_code, 409)

        self.rejected_user.refresh_from_db()

        self.assertEqual(
            self.rejected_user.approval_status,
            "rejected"
        )
        self.assertFalse(self.rejected_user.is_active)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.rejected_user
            ).exists()
        )

    # =====================================================
    # 10. Approving twice returns 409
    # =====================================================

    def test_cannot_approve_same_user_twice(self):
        self.client.force_login(self.admin)

        first_response = self.approve(self.pending_user.id)
        second_response = self.approve(self.pending_user.id)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "approved"
        )
        self.assertTrue(self.pending_user.is_active)

        self.assertEqual(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).count(),
            1
        )

    # =====================================================
    # 11. Missing requested department
    # =====================================================

    def test_cannot_approve_without_requested_department(self):
        self.pending_user.requested_department = None
        self.pending_user.save(
            update_fields=["requested_department"]
        )

        self.client.force_login(self.admin)

        response = self.approve(self.pending_user.id)

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json()["message"],
            (
                "Registration must have a requested "
                "department and role before approval."
            )
        )

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )
        self.assertFalse(self.pending_user.is_active)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 12. Missing requested role
    # =====================================================

    def test_cannot_approve_without_requested_role(self):
        self.pending_user.requested_role = None
        self.pending_user.save(
            update_fields=["requested_role"]
        )

        self.client.force_login(self.admin)

        response = self.approve(self.pending_user.id)

        self.assertEqual(response.status_code, 400)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )
        self.assertFalse(self.pending_user.is_active)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 13. Existing membership prevents approval
    # =====================================================

    def test_cannot_approve_user_with_existing_membership(self):
        DepartmentMembership.objects.create(
            user=self.pending_user,
            department=self.emergency,
            role=self.nurse_role
        )

        self.client.force_login(self.admin)

        response = self.approve(self.pending_user.id)

        self.assertEqual(response.status_code, 409)

        self.assertEqual(
            response.json()["message"],
            "This user already has a department membership."
        )

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )
        self.assertFalse(self.pending_user.is_active)

        self.assertEqual(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).count(),
            1
        )

    # =====================================================
    # 14. Transaction rollback on save failure
    # =====================================================

    def test_approval_rolls_back_if_user_save_fails(self):
        self.client.force_login(self.admin)

        with patch(
            "accounts.views.User.save",
            side_effect=RuntimeError("Simulated save failure")
        ):
            with self.assertRaisesMessage(
                RuntimeError,
                "Simulated save failure"
            ):
                self.approve(self.pending_user.id)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )
        self.assertFalse(self.pending_user.is_active)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 15. Missing CSRF token returns 403
    # =====================================================

    def test_approval_requires_csrf(self):
        self.client.force_login(self.admin)
        self.get_csrf_token()

        response = self.approve(
            self.pending_user.id,
            include_csrf=False
        )

        self.assertEqual(response.status_code, 403)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 16. Invalid CSRF token returns 403
    # =====================================================

    def test_invalid_csrf_token_is_rejected(self):
        self.client.force_login(self.admin)
        self.get_csrf_token()

        response = self.client.post(
            self.approval_url(self.pending_user.id),
            HTTP_X_CSRFTOKEN="invalid-token"
        )

        self.assertEqual(response.status_code, 403)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 17. GET requests are not allowed
    # =====================================================

    def test_get_request_is_not_allowed(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            self.approval_url(self.pending_user.id)
        )

        self.assertEqual(response.status_code, 405)



class RejectRegistrationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.emergency = Department.objects.create(
            name="Emergency",
            description="Emergency medical services",
        )

        cls.nurse_role = Role.objects.get(
            name="Nurse",)

        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="Admin123!Test",
            name="Admin"
        )

        cls.nurse = User.objects.create_user(
            email="nurse@example.com",
            password="Nurse123!Test",
            name="Nurse",
            approval_status="approved",
            is_active=True
        )

        cls.staff_user = User.objects.create_user(
            email="staff@example.com",
            password="Staff123!Test",
            name="Staff",
            approval_status="approved",
            is_active=True,
            is_staff=True
        )

        cls.pending_user = User.objects.create_user(
            email="pending@example.com",
            password="Pending123!Test",
            name="Pending User",
            requested_department=cls.emergency,
            requested_role=cls.nurse_role
        )

        cls.approved_user = User.objects.create_user(
            email="approved@example.com",
            password="Approved123!Test",
            name="Approved User",
            approval_status="approved",
            is_active=True
        )

        cls.rejected_user = User.objects.create_user(
            email="rejected@example.com",
            password="Rejected123!Test",
            name="Rejected User",
            approval_status="rejected",
            is_active=False
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    # =====================================================
    # Helpers
    # =====================================================

    def rejection_url(self, user_id):
        return f"/api/auth/registrations/{user_id}/reject/"

    def get_csrf_token(self):
        response = self.client.get("/api/auth/csrf/")

        self.assertEqual(response.status_code, 200)

        return response.json()["csrf_token"]

    def reject(self, user_id, include_csrf=True):
        headers = {}

        if include_csrf:
            headers["HTTP_X_CSRFTOKEN"] = self.get_csrf_token()

        return self.client.post(
            self.rejection_url(user_id),
            **headers
        )

    # =====================================================
    # 1. Successful rejection
    # =====================================================

    def test_admin_can_reject_pending_registration(self):
        self.client.force_login(self.admin)

        response = self.reject(self.pending_user.id)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json()["message"],
            "Registration rejected successfully."
        )

        self.assertEqual(
            response.json()["id"],
            self.pending_user.id
        )

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "rejected"
        )

        self.assertFalse(self.pending_user.is_active)

    # =====================================================
    # 2. Rejection preserves requested department and role
    # =====================================================

    def test_rejection_preserves_requested_department_and_role(self):
        self.client.force_login(self.admin)

        response = self.reject(self.pending_user.id)

        self.assertEqual(response.status_code, 200)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.requested_department,
            self.emergency
        )

        self.assertEqual(
            self.pending_user.requested_role,
            self.nurse_role
        )

        self.assertEqual(
            self.pending_user.approval_status,
            "rejected"
        )

        self.assertFalse(self.pending_user.is_active)

    # =====================================================
    # 3. Rejection does not create a membership
    # =====================================================

    def test_rejection_does_not_create_department_membership(self):
        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

        self.client.force_login(self.admin)

        response = self.reject(self.pending_user.id)

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "rejected"
        )

        self.assertFalse(self.pending_user.is_active)

    # =====================================================
    # 4. Older registrations can still be rejected
    # =====================================================

    def test_reject_pending_user_without_department_or_role(self):
        User = get_user_model()

        old_user = User.objects.create_user(
            email="old@example.com",
            password="OldUser123!Test",
            name="Old Pending User"
        )

        self.assertIsNone(old_user.requested_department)
        self.assertIsNone(old_user.requested_role)

        self.client.force_login(self.admin)

        response = self.reject(old_user.id)

        self.assertEqual(response.status_code, 200)

        old_user.refresh_from_db()

        self.assertEqual(
            old_user.approval_status,
            "rejected"
        )

        self.assertFalse(old_user.is_active)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=old_user
            ).exists()
        )

    # =====================================================
    # 5. Rejected user cannot log in
    # =====================================================

    def test_rejected_user_cannot_login_after_rejection(self):
        self.client.force_login(self.admin)

        response = self.reject(self.pending_user.id)

        self.assertEqual(response.status_code, 200)

        self.client.logout()

        login_response = self.client.post(
            "/api/auth/login/",
            data=json.dumps({
                "email": "pending@example.com",
                "password": "Pending123!Test"
            }),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.get_csrf_token()
        )

        self.assertEqual(login_response.status_code, 403)

        self.assertEqual(
            login_response.json()["error"],
            "Your registration request was rejected."
        )

    # =====================================================
    # 6. Regular users cannot reject registrations
    # =====================================================

    def test_regular_user_cannot_reject(self):
        self.client.force_login(self.nurse)

        response = self.reject(self.pending_user.id)

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            response.json()["message"],
            "Administrator access required."
        )

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )

        self.assertFalse(self.pending_user.is_active)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 7. is_staff does not grant administrator privileges
    # =====================================================

    def test_staff_user_cannot_reject(self):
        self.client.force_login(self.staff_user)

        response = self.reject(self.pending_user.id)

        self.assertEqual(response.status_code, 403)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 8. Unauthenticated users cannot reject
    # =====================================================

    def test_unauthenticated_user_cannot_reject(self):
        response = self.reject(self.pending_user.id)

        self.assertIn(response.status_code, [401, 403])

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )

        self.assertFalse(self.pending_user.is_active)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 9. Nonexistent user returns 404
    # =====================================================

    def test_reject_nonexistent_user(self):
        self.client.force_login(self.admin)

        response = self.reject(999999)

        self.assertEqual(response.status_code, 404)

    # =====================================================
    # 10. Approved registration cannot be rejected
    # =====================================================

    def test_cannot_reject_approved_user(self):
        self.client.force_login(self.admin)

        response = self.reject(self.approved_user.id)

        self.assertEqual(response.status_code, 409)

        self.assertEqual(
            response.json()["message"],
            "Only pending registrations can be rejected."
        )

        self.approved_user.refresh_from_db()

        self.assertEqual(
            self.approved_user.approval_status,
            "approved"
        )

        self.assertTrue(self.approved_user.is_active)

    # =====================================================
    # 11. Already rejected registration returns 409
    # =====================================================

    def test_cannot_reject_already_rejected_user(self):
        self.client.force_login(self.admin)

        response = self.reject(self.rejected_user.id)

        self.assertEqual(response.status_code, 409)

        self.rejected_user.refresh_from_db()

        self.assertEqual(
            self.rejected_user.approval_status,
            "rejected"
        )

        self.assertFalse(self.rejected_user.is_active)

    # =====================================================
    # 12. Rejecting the same account twice
    # =====================================================

    def test_cannot_reject_same_user_twice(self):
        self.client.force_login(self.admin)

        first_response = self.reject(self.pending_user.id)
        second_response = self.reject(self.pending_user.id)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "rejected"
        )

        self.assertFalse(self.pending_user.is_active)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 13. CSRF token is required
    # =====================================================

    def test_rejection_requires_csrf(self):
        self.client.force_login(self.admin)
        self.get_csrf_token()

        response = self.reject(
            self.pending_user.id,
            include_csrf=False
        )

        self.assertEqual(response.status_code, 403)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 14. Invalid CSRF token is rejected
    # =====================================================

    def test_invalid_csrf_token_is_rejected(self):
        self.client.force_login(self.admin)
        self.get_csrf_token()

        response = self.client.post(
            self.rejection_url(self.pending_user.id),
            HTTP_X_CSRFTOKEN="invalid-token"
        )

        self.assertEqual(response.status_code, 403)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=self.pending_user
            ).exists()
        )

    # =====================================================
    # 15. GET requests are not allowed
    # =====================================================

    def test_get_request_is_not_allowed(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            self.rejection_url(self.pending_user.id)
        )

        self.assertEqual(response.status_code, 405)

    # =====================================================
    # 16. Rejected users disappear from pending list
    # =====================================================

    def test_rejected_user_removed_from_pending_list(self):
        self.client.force_login(self.admin)

        rejection_response = self.reject(self.pending_user.id)

        self.assertEqual(rejection_response.status_code, 200)

        list_response = self.client.get(
            "/api/auth/registrations/pending/"
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json(), [])

class ApprovedUserPermissionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="Admin123!Test",
            name="Admin"
        )

        cls.nurse = User.objects.create_user(
            email="nurse@example.com",
            password="Nurse123!Test",
            name="Sara",
            is_active=True,
            approval_status="approved"
        )

        cls.pending_user = User.objects.create_user(
            email="pending@example.com",
            password="Pending123!Test",
            name="Pending User"
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

        self.me_url = "/api/auth/me/"
        self.logout_url = "/api/auth/logout/"
        self.pending_url = "/api/auth/registrations/pending/"

        self.approve_url = (
            f"/api/auth/registrations/{self.pending_user.id}/approve/"
        )

        self.reject_url = (
            f"/api/auth/registrations/{self.pending_user.id}/reject/"
        )

    def get_csrf_token(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        return response.json()["csrf_token"]

    def protected_post(self, url):
        token = self.get_csrf_token()

        return self.client.post(
            url,
            HTTP_X_CSRFTOKEN=token
        )

    # 1. Approved users can access their profile

    def test_approved_user_can_access_me(self):
        self.client.force_login(self.nurse)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["id"],
            self.nurse.id
        )

    # 2. Anonymous users cannot access their profile

    def test_anonymous_user_cannot_access_me(self):
        response = self.client.get(self.me_url)

        self.assertIn(response.status_code, [401, 403])

    # 3. Pending approval blocks an existing session

    def test_pending_user_with_existing_session_is_denied(self):
        self.client.force_login(self.nurse)

        first_response = self.client.get(self.me_url)
        self.assertEqual(first_response.status_code, 200)

        self.nurse.approval_status = "pending"
        self.nurse.save(update_fields=["approval_status"])

        second_response = self.client.get(self.me_url)

        self.assertEqual(second_response.status_code, 403)

    # 4. Rejected approval blocks an existing session

    def test_rejected_user_with_existing_session_is_denied(self):
        self.client.force_login(self.nurse)

        first_response = self.client.get(self.me_url)
        self.assertEqual(first_response.status_code, 200)

        self.nurse.approval_status = "rejected"
        self.nurse.save(update_fields=["approval_status"])

        second_response = self.client.get(self.me_url)

        self.assertEqual(second_response.status_code, 403)

    # 5. Disabled accounts lose access

    def test_inactive_user_with_existing_session_is_denied(self):
        self.client.force_login(self.nurse)

        first_response = self.client.get(self.me_url)
        self.assertEqual(first_response.status_code, 200)

        self.nurse.is_active = False
        self.nurse.save(update_fields=["is_active"])

        second_response = self.client.get(self.me_url)

        self.assertIn(second_response.status_code, [401, 403])

    # 6. Revoked superusers cannot list registrations

    def test_revoked_admin_cannot_list_pending_registrations(self):
        self.client.force_login(self.admin)

        first_response = self.client.get(self.pending_url)
        self.assertEqual(first_response.status_code, 200)

        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        second_response = self.client.get(self.pending_url)

        self.assertEqual(second_response.status_code, 403)

    # 7. Revoked superusers cannot approve accounts

    def test_revoked_admin_cannot_approve_registration(self):
        self.client.force_login(self.admin)

        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        response = self.protected_post(self.approve_url)

        self.assertEqual(response.status_code, 403)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )
        self.assertFalse(self.pending_user.is_active)

    # 8. Revoked superusers cannot reject accounts

    def test_revoked_admin_cannot_reject_registration(self):
        self.client.force_login(self.admin)

        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        response = self.protected_post(self.reject_url)

        self.assertEqual(response.status_code, 403)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )
        self.assertFalse(self.pending_user.is_active)

    # 9. Inactive superusers cannot access admin endpoints

    def test_inactive_admin_cannot_access_pending_registrations(self):
        self.client.force_login(self.admin)

        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        response = self.client.get(self.pending_url)

        self.assertIn(response.status_code, [401, 403])

    # 10. Revoked users can still log out

    def test_revoked_user_can_still_logout(self):
        self.client.force_login(self.nurse)

        self.nurse.approval_status = "rejected"
        self.nurse.save(update_fields=["approval_status"])

        response = self.protected_post(self.logout_url)

        self.assertEqual(response.status_code, 200)

        me_response = self.client.get(self.me_url)

        self.assertIn(me_response.status_code, [401, 403])

class UserProfileTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.owner = User.objects.create_user(
            email="owner@example.com",
            name="Profile Owner",
            password="StrongTestPassword123!",
            phone_number="+212612345678",
            show_phone_number=False,
            approval_status="approved",
            is_active=True,
        )

        self.viewer = User.objects.create_user(
            email="viewer@example.com",
            name="Other Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.url = "/api/auth/me/"

    def serialize_profile(self, viewer):
        request = SimpleNamespace(user=viewer)

        serializer = UserProfileSerializer(
            self.owner,
            context={"request": request},
        )

        return serializer.data

    def test_approved_user_can_get_own_profile(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.owner.id)
        self.assertEqual(response.data["name"], self.owner.name)
        self.assertEqual(response.data["email"], self.owner.email)
        self.assertEqual(response.data["status"], "offline")
        self.assertIn("avatar", response.data)
        self.assertIn("date_joined", response.data)

    def test_owner_can_see_private_phone_number(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["phone_number"],
            "+212612345678",
        )
        self.assertFalse(response.data["show_phone_number"])

    def test_unauthenticated_user_cannot_get_profile(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, [401, 403])

    def test_pending_user_cannot_get_profile(self):
        self.owner.approval_status = "pending"
        self.owner.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_rejected_user_cannot_get_profile(self):
        self.owner.approval_status = "rejected"
        self.owner.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_inactive_user_cannot_get_profile(self):
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_other_staff_cannot_see_private_phone(self):
        data = self.serialize_profile(self.viewer)

        self.assertNotIn("phone_number", data)
        self.assertNotIn("show_phone_number", data)
        self.assertEqual(data["name"], self.owner.name)

    def test_other_staff_can_see_public_phone(self):
        self.owner.show_phone_number = True
        self.owner.save(update_fields=["show_phone_number"])

        data = self.serialize_profile(self.viewer)

        self.assertEqual(
            data["phone_number"],
            "+212612345678",
        )
        self.assertNotIn("show_phone_number", data)

    def test_pending_viewer_cannot_see_public_phone(self):
        self.owner.show_phone_number = True
        self.owner.save(update_fields=["show_phone_number"])

        self.viewer.approval_status = "pending"
        self.viewer.save(update_fields=["approval_status"])

        data = self.serialize_profile(self.viewer)

        self.assertNotIn("phone_number", data)
        self.assertNotIn("show_phone_number", data)

    def test_anonymous_viewer_cannot_see_public_phone(self):
        self.owner.show_phone_number = True
        self.owner.save(update_fields=["show_phone_number"])

        data = self.serialize_profile(AnonymousUser())

        self.assertNotIn("phone_number", data)
        self.assertNotIn("show_phone_number", data)

    def test_missing_request_hides_private_information(self):
        serializer = UserProfileSerializer(self.owner)

        data = serializer.data

        self.assertNotIn("phone_number", data)
        self.assertNotIn("show_phone_number", data)


class UpdateProfileTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="owner@example.com",
            name="Original Name",
            password="StrongTestPassword123!",
            avatar="https://example.com/old.png",
            phone_number="+212612345678",
            show_phone_number=False,
            approval_status="approved",
            is_active=True,
        )

        self.url = "/api/auth/me/"

    def test_user_can_update_multiple_fields(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {
                "name": "Updated Name",
                "avatar": "https://example.com/new.png",
                "phone_number": "+212698765432",
                "show_phone_number": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()

        self.assertEqual(self.user.name, "Updated Name")
        self.assertEqual(
            self.user.avatar,
            "https://example.com/new.png",
        )
        self.assertEqual(
            self.user.phone_number,
            "+212698765432",
        )
        self.assertTrue(self.user.show_phone_number)

        self.assertEqual(
            response.data["name"],
            "Updated Name",
        )
        self.assertTrue(
            response.data["show_phone_number"]
        )

    def test_partial_update_preserves_other_fields(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"name": "New Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()

        self.assertEqual(self.user.name, "New Name")
        self.assertEqual(
            self.user.phone_number,
            "+212612345678",
        )
        self.assertFalse(self.user.show_phone_number)
        self.assertEqual(
            self.user.avatar,
            "https://example.com/old.png",
        )

    def test_user_can_remove_optional_phone_number(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"phone_number": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()

        self.assertEqual(self.user.phone_number, "")

    def test_user_can_change_phone_visibility(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"show_phone_number": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.show_phone_number)

        response = self.client.patch(
            self.url,
            {"show_phone_number": False},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertFalse(self.user.show_phone_number)

    def test_empty_name_is_rejected(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"name": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Original Name")

    def test_phone_number_exceeding_max_length_is_rejected(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"phone_number": "1" * 21},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("phone_number", response.data)

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.phone_number,
            "+212612345678",
        )

    def test_invalid_phone_visibility_is_rejected(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"show_phone_number": "invalid-value"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("show_phone_number", response.data)

        self.user.refresh_from_db()
        self.assertFalse(self.user.show_phone_number)

    def test_user_cannot_modify_protected_fields(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {
                "email": "hacker@example.com",
                "approval_status": "rejected",
                "is_active": False,
                "is_staff": True,
                "is_superuser": True,
                "status": "online",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "owner@example.com",
        )
        self.assertEqual(
            self.user.approval_status,
            "approved",
        )
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.status, "offline")

    def test_user_can_only_update_own_profile(self):
        User = get_user_model()

        other_user = User.objects.create_user(
            email="other@example.com",
            name="Other User",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {
                "name": "Changed Name",
                "id": other_user.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        other_user.refresh_from_db()

        self.assertEqual(self.user.name, "Changed Name")
        self.assertEqual(other_user.name, "Other User")

    def test_unauthenticated_user_cannot_update_profile(self):
        response = self.client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertIn(response.status_code, [401, 403])

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Original Name")

    def test_pending_user_cannot_update_profile(self):
        self.user.approval_status = "pending"
        self.user.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Original Name")

    def test_rejected_user_cannot_update_profile(self):
        self.user.approval_status = "rejected"
        self.user.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Original Name")

    def test_inactive_user_cannot_update_profile(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Original Name")

    def test_patch_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)

        response = client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Original Name")

    def test_patch_with_valid_csrf_token_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)

        client.get("/api/auth/csrf/")

        self.assertIn("csrftoken", client.cookies)

        csrf_token = client.cookies["csrftoken"].value

        response = client.patch(
            self.url,
            {"name": "CSRF Protected Update"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.name,
            "CSRF Protected Update",
        )


class StaffProfileTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.viewer = User.objects.create_user(
            email="viewer@example.com",
            name="Approved Viewer",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.target = User.objects.create_user(
            email="target@example.com",
            name="Target Staff",
            password="StrongTestPassword123!",
            phone_number="+212612345678",
            show_phone_number=False,
            approval_status="approved",
            is_active=True,
        )

        self.url = reverse(
            "staff-profile",
            kwargs={"user_id": self.target.id},
        )

    def test_approved_staff_can_view_another_profile(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.target.id)
        self.assertEqual(response.data["name"], self.target.name)
        self.assertEqual(response.data["email"], self.target.email)
        self.assertIn("avatar", response.data)
        self.assertIn("status", response.data)
        self.assertIn("date_joined", response.data)

    def test_private_phone_is_hidden_from_other_staff(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("phone_number", response.data)

    def test_public_phone_is_visible_to_approved_staff(self):
        self.target.show_phone_number = True
        self.target.save(update_fields=["show_phone_number"])

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["phone_number"],
            "+212612345678",
        )

    def test_phone_visibility_setting_is_hidden_from_other_staff(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("show_phone_number", response.data)

    def test_owner_can_view_own_private_phone(self):
        self.client.force_authenticate(user=self.target)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["phone_number"],
            "+212612345678",
        )
        self.assertFalse(response.data["show_phone_number"])

    def test_nonexistent_staff_returns_404(self):
        self.client.force_authenticate(user=self.viewer)

        url = reverse(
            "staff-profile",
            kwargs={"user_id": 999999},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_pending_staff_profile_is_not_accessible(self):
        self.target.approval_status = "pending"
        self.target.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_rejected_staff_profile_is_not_accessible(self):
        self.target.approval_status = "rejected"
        self.target.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_inactive_staff_profile_is_not_accessible(self):
        self.target.is_active = False
        self.target.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_cannot_view_staff_profile(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, [401, 403])

    def test_pending_user_cannot_view_staff_profile(self):
        self.viewer.approval_status = "pending"
        self.viewer.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_rejected_user_cannot_view_staff_profile(self):
        self.viewer.approval_status = "rejected"
        self.viewer.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_inactive_user_cannot_view_staff_profile(self):
        self.viewer.is_active = False
        self.viewer.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)


class StaffListTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.viewer = User.objects.create_user(
            email="viewer@example.com",
            name="Approved Viewer",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.approved_staff = User.objects.create_user(
            email="staff@example.com",
            name="Approved Staff",
            password="StrongTestPassword123!",
            phone_number="+212612345678",
            show_phone_number=True,
            approval_status="approved",
            is_active=True,
        )

        self.pending_staff = User.objects.create_user(
            email="pending@example.com",
            name="Pending Staff",
            password="StrongTestPassword123!",
            approval_status="pending",
            is_active=True,
        )

        self.rejected_staff = User.objects.create_user(
            email="rejected@example.com",
            name="Rejected Staff",
            password="StrongTestPassword123!",
            approval_status="rejected",
            is_active=True,
        )

        self.inactive_staff = User.objects.create_user(
            email="inactive@example.com",
            name="Inactive Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=False,
        )

        self.url = reverse("staff-list")

    def find_user(self, data, user_id):
        index = 0

        while index < len(data):
            if data[index]["id"] == user_id:
                return data[index]
            index += 1

        return None

    def test_approved_user_can_get_staff_directory(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_directory_contains_only_active_approved_staff(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        self.assertIsNotNone(
            self.find_user(response.data, self.viewer.id)
        )
        self.assertIsNotNone(
            self.find_user(response.data, self.approved_staff.id)
        )

        self.assertIsNone(
            self.find_user(response.data, self.pending_staff.id)
        )
        self.assertIsNone(
            self.find_user(response.data, self.rejected_staff.id)
        )
        self.assertIsNone(
            self.find_user(response.data, self.inactive_staff.id)
        )

    def test_directory_returns_correct_fields(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        staff = self.find_user(
            response.data,
            self.approved_staff.id,
        )

        self.assertIsNotNone(staff)
        self.assertEqual(
            set(staff.keys()),
            {"id", "name", "email", "avatar", "status"},
        )

        self.assertEqual(
            staff["name"],
            self.approved_staff.name,
        )
        self.assertEqual(
            staff["email"],
            self.approved_staff.email,
        )

    def test_directory_does_not_expose_phone_numbers(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        staff = self.find_user(
            response.data,
            self.approved_staff.id,
        )

        self.assertIsNotNone(staff)
        self.assertNotIn("phone_number", staff)
        self.assertNotIn("show_phone_number", staff)

    def test_directory_does_not_expose_sensitive_fields(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        staff = self.find_user(
            response.data,
            self.approved_staff.id,
        )

        self.assertNotIn("password", staff)
        self.assertNotIn("is_staff", staff)
        self.assertNotIn("is_superuser", staff)
        self.assertNotIn("is_active", staff)
        self.assertNotIn("approval_status", staff)

    def test_unauthenticated_user_cannot_access_directory(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, [401, 403])

    def test_pending_user_cannot_access_directory(self):
        self.client.force_authenticate(user=self.pending_staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_rejected_user_cannot_access_directory(self):
        self.client.force_authenticate(user=self.rejected_staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_inactive_user_cannot_access_directory(self):
        self.client.force_authenticate(user=self.inactive_staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_post_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.url,
            {"name": "New Staff"},
            format="json",
        )

        self.assertEqual(response.status_code, 405)

    
    def test_admin_can_see_active_and_inactive_staff(self):
        User = get_user_model()

        admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        self.client.force_authenticate(user=admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

        self.assertIsNotNone(
            self.find_user(response.data, admin.id)
        )
        self.assertIsNotNone(
            self.find_user(response.data, self.viewer.id)
        )
        self.assertIsNotNone(
            self.find_user(response.data, self.approved_staff.id)
        )
        self.assertIsNotNone(
            self.find_user(response.data, self.inactive_staff.id)
        )

        self.assertIsNone(
            self.find_user(response.data, self.pending_staff.id)
        )
        self.assertIsNone(
            self.find_user(response.data, self.rejected_staff.id)
        )

    def test_admin_receives_account_activation_status(self):
        User = get_user_model()

        admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        self.client.force_authenticate(user=admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        active_staff = self.find_user(
            response.data,
            self.approved_staff.id,
        )
        inactive_staff = self.find_user(
            response.data,
            self.inactive_staff.id,
        )

        self.assertIsNotNone(active_staff)
        self.assertIsNotNone(inactive_staff)

        self.assertTrue(active_staff["is_active"])
        self.assertFalse(inactive_staff["is_active"])

        self.assertEqual(
            set(active_staff.keys()),
            {
                "id",
                "name",
                "email",
                "avatar",
                "status",
                "is_active",
            },
        )

    def test_admin_directory_does_not_expose_private_fields(self):
        User = get_user_model()

        admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        self.client.force_authenticate(user=admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        staff = self.find_user(
            response.data,
            self.approved_staff.id,
        )

        self.assertIsNotNone(staff)
        self.assertNotIn("phone_number", staff)
        self.assertNotIn("show_phone_number", staff)
        self.assertNotIn("password", staff)
        self.assertNotIn("is_superuser", staff)
        self.assertNotIn("approval_status", staff)



class AdminStaffUpdateTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        self.staff = User.objects.create_user(
            email="staff@example.com",
            name="Original Staff",
            password="StrongTestPassword123!",
            phone_number="+212612345678",
            show_phone_number=False,
            approval_status="approved",
            is_active=True,
        )

        self.regular_user = User.objects.create_user(
            email="regular@example.com",
            name="Regular Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.inactive_staff = User.objects.create_user(
            email="inactive@example.com",
            name="Inactive Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=False,
        )

        self.url = reverse(
            "admin-staff-update",
            kwargs={"user_id": self.staff.id},
        )

    def test_admin_can_update_name_and_email(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {
                "name": "Updated Staff",
                "email": "updated@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.staff.refresh_from_db()

        self.assertEqual(self.staff.name, "Updated Staff")
        self.assertEqual(self.staff.email, "updated@example.com")
        self.assertEqual(response.data["name"], "Updated Staff")
        self.assertEqual(response.data["email"], "updated@example.com")

    def test_partial_update_preserves_email(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"name": "New Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.staff.refresh_from_db()

        self.assertEqual(self.staff.name, "New Name")
        self.assertEqual(self.staff.email, "staff@example.com")

    def test_admin_can_update_inactive_approved_staff(self):
        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "admin-staff-update",
            kwargs={"user_id": self.inactive_staff.id},
        )

        response = self.client.patch(
            url,
            {"name": "Corrected Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.inactive_staff.refresh_from_db()

        self.assertEqual(self.inactive_staff.name, "Corrected Name")
        self.assertFalse(self.inactive_staff.is_active)

    def test_pending_target_returns_404(self):
        self.staff.approval_status = "pending"
        self.staff.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"name": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.name, "Original Staff")

    def test_rejected_target_returns_404(self):
        self.staff.approval_status = "rejected"
        self.staff.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"name": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.name, "Original Staff")

    def test_nonexistent_target_returns_404(self):
        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "admin-staff-update",
            kwargs={"user_id": 999999},
        )

        response = self.client.patch(
            url,
            {"name": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_regular_user_cannot_update_staff(self):
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.name, "Original Staff")

    def test_unauthenticated_user_cannot_update_staff(self):
        response = self.client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertIn(response.status_code, [401, 403])

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.name, "Original Staff")

    def test_pending_admin_cannot_update_staff(self):
        self.admin.approval_status = "pending"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.name, "Original Staff")

    def test_rejected_admin_cannot_update_staff(self):
        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.name, "Original Staff")

    def test_inactive_admin_cannot_update_staff(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.name, "Original Staff")

    def test_duplicate_email_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"email": "regular@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "staff@example.com")

    def test_invalid_email_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"email": "invalid-email"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "staff@example.com")

    def test_empty_name_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"name": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.name, "Original Staff")

    def test_empty_email_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"email": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "staff@example.com")

    def test_admin_cannot_modify_protected_fields(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {
                "name": "Updated Name",
                "is_superuser": True,
                "is_staff": True,
                "is_active": False,
                "approval_status": "rejected",
                "phone_number": "+212699999999",
                "show_phone_number": True,
                "status": "online",
                "password": "HackedPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.staff.refresh_from_db()

        self.assertEqual(self.staff.name, "Updated Name")
        self.assertFalse(self.staff.is_superuser)
        self.assertFalse(self.staff.is_staff)
        self.assertTrue(self.staff.is_active)
        self.assertEqual(self.staff.approval_status, "approved")
        self.assertEqual(self.staff.phone_number, "+212612345678")
        self.assertFalse(self.staff.show_phone_number)
        self.assertEqual(self.staff.status, "offline")
        self.assertTrue(
            self.staff.check_password("StrongTestPassword123!")
        )

    def test_response_contains_only_allowed_fields(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"name": "Updated Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.data.keys()),
            {"name", "email"},
        )

    def test_post_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {"name": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, 405)

    def test_patch_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        response = client.patch(
            self.url,
            {"name": "Unauthorized Change"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.name, "Original Staff")

    def test_patch_with_valid_csrf_token_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        client.get("/api/auth/csrf/")

        self.assertIn("csrftoken", client.cookies)

        csrf_token = client.cookies["csrftoken"].value

        response = client.patch(
            self.url,
            {"name": "CSRF Protected Update"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)

        self.staff.refresh_from_db()
        self.assertEqual(
            self.staff.name,
            "CSRF Protected Update",
        )


class DeactivateStaffTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        self.staff = User.objects.create_user(
            email="staff@example.com",
            name="Approved Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.regular_user = User.objects.create_user(
            email="regular@example.com",
            name="Regular Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.url = reverse(
            "admin-staff-deactivate",
            kwargs={"user_id": self.staff.id},
        )

    def test_admin_can_deactivate_approved_staff(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"message": "Staff account deactivated successfully."},
        )

        self.staff.refresh_from_db()

        self.assertFalse(self.staff.is_active)
        self.assertEqual(
            self.staff.approval_status,
            "approved",
        )

    def test_deactivating_twice_returns_409(self):
        self.client.force_authenticate(user=self.admin)

        first_response = self.client.post(self.url)
        second_response = self.client.post(self.url)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(
            second_response.data["message"],
            "This account is already deactivated.",
        )

    def test_deactivated_staff_loses_access(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)

        self.staff.refresh_from_db()
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, 403)

    def test_regular_user_cannot_deactivate_staff(self):
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_unauthenticated_user_cannot_deactivate_staff(self):
        response = self.client.post(self.url)

        self.assertIn(response.status_code, [401, 403])

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_pending_admin_cannot_deactivate_staff(self):
        self.admin.approval_status = "pending"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_rejected_admin_cannot_deactivate_staff(self):
        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_inactive_admin_cannot_deactivate_staff(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_admin_cannot_deactivate_own_account(self):
        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "admin-staff-deactivate",
            kwargs={"user_id": self.admin.id},
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["message"],
            "You cannot deactivate your own account.",
        )

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_pending_target_returns_404(self):
        self.staff.approval_status = "pending"
        self.staff.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 404)

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_rejected_target_returns_404(self):
        self.staff.approval_status = "rejected"
        self.staff.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 404)

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_nonexistent_target_returns_404(self):
        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "admin-staff-deactivate",
            kwargs={"user_id": 999999},
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_already_inactive_staff_returns_409(self):
        self.staff.is_active = False
        self.staff.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 409)

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)
        self.assertEqual(
            self.staff.approval_status,
            "approved",
        )

    def test_get_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_patch_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, 405)

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_post_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        response = client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_post_with_valid_csrf_token_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        client.get(reverse("csrf"))

        self.assertIn("csrftoken", client.cookies)

        csrf_token = client.cookies["csrftoken"].value

        response = client.post(
            self.url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)

        self.staff.refresh_from_db()

        self.assertFalse(self.staff.is_active)
        self.assertEqual(
            self.staff.approval_status,
            "approved",
        )


class ActivateStaffTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        self.staff = User.objects.create_user(
            email="staff@example.com",
            name="Deactivated Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=False,
        )

        self.active_staff = User.objects.create_user(
            email="active@example.com",
            name="Active Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.regular_user = User.objects.create_user(
            email="regular@example.com",
            name="Regular Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.url = reverse(
            "admin-staff-activate",
            kwargs={"user_id": self.staff.id},
        )

    def test_admin_can_activate_deactivated_staff(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"message": "Staff account activated successfully."},
        )

        self.staff.refresh_from_db()

        self.assertTrue(self.staff.is_active)
        self.assertEqual(
            self.staff.approval_status,
            "approved",
        )

    def test_activated_staff_regains_access(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)

        self.staff.refresh_from_db()
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["id"],
            self.staff.id,
        )

    def test_already_active_staff_returns_409(self):
        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "admin-staff-activate",
            kwargs={"user_id": self.active_staff.id},
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["message"],
            "This account is already activated.",
        )

        self.active_staff.refresh_from_db()
        self.assertTrue(self.active_staff.is_active)

    def test_activating_twice_returns_409(self):
        self.client.force_authenticate(user=self.admin)

        first_response = self.client.post(self.url)
        second_response = self.client.post(self.url)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(
            second_response.data["message"],
            "This account is already activated.",
        )

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_pending_target_returns_404(self):
        self.staff.approval_status = "pending"
        self.staff.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 404)

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_rejected_target_returns_404(self):
        self.staff.approval_status = "rejected"
        self.staff.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 404)

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_nonexistent_target_returns_404(self):
        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "admin-staff-activate",
            kwargs={"user_id": 999999},
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_regular_user_cannot_activate_staff(self):
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_unauthenticated_user_cannot_activate_staff(self):
        response = self.client.post(self.url)

        self.assertIn(response.status_code, [401, 403])

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_pending_admin_cannot_activate_staff(self):
        self.admin.approval_status = "pending"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_rejected_admin_cannot_activate_staff(self):
        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_inactive_admin_cannot_activate_staff(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_inactive_admin_cannot_reactivate_self(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "admin-staff-activate",
            kwargs={"user_id": self.admin.id},
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_active)

    def test_get_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_patch_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, 405)

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_post_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        response = client.post(self.url)

        self.assertEqual(response.status_code, 403)

        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_post_with_valid_csrf_token_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        client.get(reverse("csrf"))

        self.assertIn("csrftoken", client.cookies)

        csrf_token = client.cookies["csrftoken"].value

        response = client.post(
            self.url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)

        self.staff.refresh_from_db()

        self.assertTrue(self.staff.is_active)
        self.assertEqual(
            self.staff.approval_status,
            "approved",
        )


class DepartmentRoleMembershipModelTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="sara@example.com",
            name="Sara",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.other_user = User.objects.create_user(
            email="youssef@example.com",
            name="Youssef",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.emergency = Department.objects.create(
            name="Emergency",
            description="Emergency medical services",
        )

        self.cardiology = Department.objects.create(
            name="Cardiology",
            description="Heart-related medical services",
        )

        self.nurse = Role.objects.get(
            name="Nurse")

        self.doctor = Role.objects.get(
            name="Doctor")

    def create_membership(self):
        return DepartmentMembership.objects.create(
            user=self.user,
            department=self.emergency,
            role=self.nurse,
        )

    # Department tests

    def test_department_creation(self):
        self.assertEqual(self.emergency.name, "Emergency")
        self.assertEqual(
            self.emergency.description,
            "Emergency medical services",
        )
        self.assertIsNotNone(self.emergency.id)
        self.assertEqual(str(self.emergency), "Emergency")

    def test_department_description_is_optional(self):
        department = Department.objects.create(
            name="Pediatrics",
        )

        self.assertEqual(department.description, "")

    def test_duplicate_department_name_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Department.objects.create(
                    name="Emergency",
                )

        self.assertEqual(
            Department.objects.filter(name="Emergency").count(),
            1,
        )

    # Role tests

    def test_role_creation(self):
        role = Role.objects.create(
            name="Test Role",
            description="A role created for testing.",
        )

        self.assertEqual(role.name, "Test Role")
        self.assertEqual(
            role.description,
            "A role created for testing.",
        )
        self.assertIsNotNone(role.id)
        self.assertEqual(str(role), "Test Role")

    def test_role_description_is_optional(self):
        role = Role.objects.create(
            name="Coordinator",
        )

        self.assertEqual(role.description, "")

    def test_duplicate_role_name_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Role.objects.create(
                    name="Nurse",
                )

        self.assertEqual(
            Role.objects.filter(name="Nurse").count(),
            1,
        )

    # DepartmentMembership tests

    def test_membership_creation(self):
        membership = self.create_membership()

        self.assertIsNotNone(membership.id)
        self.assertEqual(membership.user, self.user)
        self.assertEqual(
            membership.department,
            self.emergency,
        )
        self.assertEqual(membership.role, self.nurse)

    def test_membership_string_representation(self):
        membership = self.create_membership()

        self.assertEqual(
            str(membership),
            "Sara - Emergency - Nurse",
        )

    def test_user_can_belong_to_multiple_departments(self):
        self.create_membership()

        DepartmentMembership.objects.create(
            user=self.user,
            department=self.cardiology,
            role=self.doctor,
        )

        memberships = DepartmentMembership.objects.filter(
            user=self.user,
        )

        self.assertEqual(memberships.count(), 2)

    def test_different_users_can_join_same_department(self):
        self.create_membership()

        DepartmentMembership.objects.create(
            user=self.other_user,
            department=self.emergency,
            role=self.doctor,
        )

        self.assertEqual(
            DepartmentMembership.objects.filter(
                department=self.emergency,
            ).count(),
            2,
        )

    def test_duplicate_membership_is_rejected(self):
        self.create_membership()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DepartmentMembership.objects.create(
                    user=self.user,
                    department=self.emergency,
                    role=self.nurse,
                )

        self.assertEqual(
            DepartmentMembership.objects.count(),
            1,
        )

    def test_same_department_with_different_role_is_rejected(self):
        self.create_membership()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DepartmentMembership.objects.create(
                    user=self.user,
                    department=self.emergency,
                    role=self.doctor,
                )

        self.assertEqual(
            DepartmentMembership.objects.count(),
            1,
        )

    # CASCADE and PROTECT tests

    def test_deleting_user_cascades_to_memberships(self):
        self.create_membership()

        DepartmentMembership.objects.create(
            user=self.user,
            department=self.cardiology,
            role=self.doctor,
        )

        self.user.delete()

        self.assertEqual(
            DepartmentMembership.objects.count(),
            0,
        )

        self.assertTrue(
            Department.objects.filter(
                id=self.emergency.id
            ).exists()
        )
        self.assertTrue(
            Role.objects.filter(id=self.nurse.id).exists()
        )

    def test_deleting_assigned_department_is_protected(self):
        self.create_membership()

        with self.assertRaises(ProtectedError):
            self.emergency.delete()

        self.assertTrue(
            Department.objects.filter(
                id=self.emergency.id,
            ).exists()
        )
        self.assertEqual(
            DepartmentMembership.objects.count(),
            1,
        )

    def test_deleting_assigned_role_is_protected(self):
        self.create_membership()

        with self.assertRaises(ProtectedError):
            self.nurse.delete()

        self.assertTrue(
            Role.objects.filter(id=self.nurse.id).exists()
        )
        self.assertEqual(
            DepartmentMembership.objects.count(),
            1,
        )

    def test_unassigned_department_and_role_can_be_deleted(self):
        department_id = self.cardiology.id
        role_id = self.doctor.id

        self.cardiology.delete()
        self.doctor.delete()

        self.assertFalse(
            Department.objects.filter(
                id=department_id,
            ).exists()
        )
        self.assertFalse(
            Role.objects.filter(id=role_id).exists()
        )

    def test_deleting_membership_preserves_related_objects(self):
        membership = self.create_membership()
        membership_id = membership.id

        membership.delete()

        self.assertFalse(
            DepartmentMembership.objects.filter(
                id=membership_id,
            ).exists()
        )
        self.assertTrue(
            Department.objects.filter(
                id=self.emergency.id,
            ).exists()
        )
        self.assertTrue(
            Role.objects.filter(id=self.nurse.id).exists()
        )
        self.assertTrue(
            get_user_model().objects.filter(
                id=self.user.id,
            ).exists()
        )



class DepartmentListCreateTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        self.staff = User.objects.create_user(
            email="staff@example.com",
            name="Approved Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        self.pending_user = User.objects.create_user(
            email="pending@example.com",
            name="Pending Staff",
            password="StrongTestPassword123!",
            approval_status="pending",
            is_active=True,
        )

        self.rejected_user = User.objects.create_user(
            email="rejected@example.com",
            name="Rejected Staff",
            password="StrongTestPassword123!",
            approval_status="rejected",
            is_active=True,
        )

        self.inactive_user = User.objects.create_user(
            email="inactive@example.com",
            name="Inactive Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=False,
        )

        self.emergency = Department.objects.create(
            name="Emergency",
            description="Emergency medical services",
        )

        self.cardiology = Department.objects.create(
            name="Cardiology",
            description="Heart-related medical services",
        )

        self.url = reverse("department-list-create")

    # =====================================================
    # GET: Public department listing
    # =====================================================

    def test_approved_staff_can_list_departments(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        self.assertEqual(
            response.data[0]["id"],
            self.emergency.id,
        )

        self.assertEqual(
            response.data[1]["id"],
            self.cardiology.id,
        )

        self.assertEqual(
            response.data[0]["name"],
            "Emergency",
        )

    def test_admin_can_list_departments(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        self.assertEqual(
            set(response.data[0].keys()),
            {"id", "name", "description"},
        )

    def test_unauthenticated_user_can_list_departments(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_pending_user_can_list_departments(self):
        self.client.force_authenticate(user=self.pending_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_rejected_user_can_list_departments(self):
        self.client.force_authenticate(user=self.rejected_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_inactive_user_can_list_departments(self):
        self.client.force_authenticate(user=self.inactive_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    # =====================================================
    # POST: Successful department creation
    # =====================================================

    def test_admin_can_create_department(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "name": "Pediatrics",
                "description": "Healthcare for children",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Pediatrics")

        self.assertEqual(
            response.data["description"],
            "Healthcare for children",
        )

        self.assertIn("id", response.data)

        self.assertTrue(
            Department.objects.filter(
                name="Pediatrics"
            ).exists()
        )

        self.assertEqual(Department.objects.count(), 3)

    def test_admin_can_create_department_without_description(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {"name": "Neurology"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Neurology")
        self.assertEqual(response.data["description"], "")

        self.assertTrue(
            Department.objects.filter(
                name="Neurology"
            ).exists()
        )

    def test_department_id_is_read_only(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "id": 999999,
                "name": "Surgery",
                "description": "Surgical services",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.assertNotEqual(
            response.data["id"],
            999999,
        )

        self.assertEqual(
            response.data["name"],
            "Surgery",
        )

    # =====================================================
    # POST: Permissions
    # =====================================================

    def test_regular_staff_cannot_create_department(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            self.url,
            {"name": "Neurology"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            response.data["message"],
            "Administrator access required.",
        )

        self.assertFalse(
            Department.objects.filter(
                name="Neurology"
            ).exists()
        )

    def test_unauthenticated_user_cannot_create_department(self):
        response = self.client.post(
            self.url,
            {"name": "Neurology"},
            format="json",
        )

        self.assertIn(response.status_code, [401, 403])
        self.assertEqual(Department.objects.count(), 2)

    def test_pending_admin_cannot_create_department(self):
        self.admin.approval_status = "pending"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {"name": "Neurology"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Department.objects.count(), 2)

    def test_rejected_admin_cannot_create_department(self):
        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {"name": "Neurology"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Department.objects.count(), 2)

    def test_inactive_admin_cannot_create_department(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {"name": "Neurology"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Department.objects.count(), 2)

    # =====================================================
    # POST: Validation
    # =====================================================

    def test_duplicate_department_name_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "name": "Emergency",
                "description": "Another department",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)
        self.assertEqual(Department.objects.count(), 2)

    def test_missing_department_name_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {"description": "No department name"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)
        self.assertEqual(Department.objects.count(), 2)

    def test_empty_department_name_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "name": "",
                "description": "Invalid department",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)
        self.assertEqual(Department.objects.count(), 2)

    def test_department_name_exceeding_max_length_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {"name": "A" * 101},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)
        self.assertEqual(Department.objects.count(), 2)

    # =====================================================
    # POST: CSRF protection
    # =====================================================

    def test_post_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        response = client.post(
            self.url,
            {"name": "Neurology"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            Department.objects.filter(
                name="Neurology"
            ).exists()
        )

    def test_post_with_valid_csrf_token_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        client.get(reverse("csrf"))

        self.assertIn("csrftoken", client.cookies)

        csrf_token = client.cookies["csrftoken"].value

        response = client.post(
            self.url,
            {
                "name": "Neurology",
                "description": "Nervous system care",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 201)

        self.assertTrue(
            Department.objects.filter(
                name="Neurology"
            ).exists()
        )

    # =====================================================
    # Unsupported HTTP methods
    # =====================================================

    def test_patch_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"name": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Department.objects.count(), 2)


class DepartmentDeleteTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        cls.staff = User.objects.create_user(
            email="staff@example.com",
            name="Approved Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        cls.emergency = Department.objects.create(
            name="Emergency",
            description="Emergency services",
        )

        cls.cardiology = Department.objects.create(
            name="Cardiology",
            description="Cardiology services",
        )

        cls.nurse = Role.objects.get(
            name="Nurse",
        )

        cls.membership = DepartmentMembership.objects.create(
            user=cls.staff,
            department=cls.emergency,
            role=cls.nurse,
        )

        cls.url = reverse(
            "department-detail",
            kwargs={"department_id": cls.cardiology.id},
        )

        cls.protected_url = reverse(
            "department-detail",
            kwargs={"department_id": cls.emergency.id},
        )

    # Successful deletion

    def test_admin_can_delete_unassigned_department(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

        self.assertFalse(
            Department.objects.filter(
                id=self.cardiology.id,
            ).exists()
        )

    def test_deleting_department_preserves_other_departments(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 204)

        self.assertTrue(
            Department.objects.filter(
                id=self.emergency.id,
            ).exists()
        )

        self.assertEqual(Department.objects.count(), 1)

    def test_deleting_same_department_twice_returns_404(self):
        self.client.force_authenticate(user=self.admin)

        first_response = self.client.delete(self.url)
        second_response = self.client.delete(self.url)

        self.assertEqual(first_response.status_code, 204)
        self.assertEqual(second_response.status_code, 404)

    # PROTECT constraint

    def test_department_with_memberships_cannot_be_deleted(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.protected_url)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["message"],
            "Cannot delete a department with assigned staff members.",
        )

        self.assertTrue(
            Department.objects.filter(
                id=self.emergency.id,
            ).exists()
        )

    def test_protected_deletion_preserves_memberships(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.protected_url)

        self.assertEqual(response.status_code, 409)

        self.assertTrue(
            DepartmentMembership.objects.filter(
                id=self.membership.id,
            ).exists()
        )

        self.assertTrue(
            Role.objects.filter(
                id=self.nurse.id,
            ).exists()
        )

        self.assertTrue(
            get_user_model().objects.filter(
                id=self.staff.id,
            ).exists()
        )

    # Missing department

    def test_nonexistent_department_returns_404(self):
        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "department-detail",
            kwargs={"department_id": 999999},
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Department.objects.count(), 2)

    # Permissions

    def test_regular_staff_cannot_delete_department(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["message"],
            "Administrator access required.",
        )

        self.assertTrue(
            Department.objects.filter(
                id=self.cardiology.id,
            ).exists()
        )

    def test_unauthenticated_user_cannot_delete_department(self):
        response = self.client.delete(self.url)

        self.assertIn(response.status_code, [401, 403])

        self.assertTrue(
            Department.objects.filter(
                id=self.cardiology.id,
            ).exists()
        )

    def test_pending_admin_cannot_delete_department(self):
        self.admin.approval_status = "pending"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            Department.objects.filter(
                id=self.cardiology.id,
            ).exists()
        )

    def test_rejected_admin_cannot_delete_department(self):
        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            Department.objects.filter(
                id=self.cardiology.id,
            ).exists()
        )

    def test_inactive_admin_cannot_delete_department(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            Department.objects.filter(
                id=self.cardiology.id,
            ).exists()
        )

    # CSRF protection

    def test_delete_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        response = client.delete(self.url)

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            Department.objects.filter(
                id=self.cardiology.id,
            ).exists()
        )

    def test_delete_with_valid_csrf_token_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        client.get(reverse("csrf"))

        self.assertIn("csrftoken", client.cookies)

        csrf_token = client.cookies["csrftoken"].value

        response = client.delete(
            self.url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            Department.objects.filter(
                id=self.cardiology.id,
            ).exists()
        )

    # Unsupported HTTP method

    def test_get_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)


class DepartmentMembershipListCreateTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        cls.viewer = User.objects.create_user(
            email="viewer@example.com",
            name="Approved Viewer",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        cls.staff = User.objects.create_user(
            email="staff@example.com",
            name="Approved Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        cls.inactive_staff = User.objects.create_user(
            email="inactive@example.com",
            name="Inactive Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=False,
        )

        cls.pending_staff = User.objects.create_user(
            email="pending@example.com",
            name="Pending Staff",
            password="StrongTestPassword123!",
            approval_status="pending",
            is_active=True,
        )

        cls.rejected_staff = User.objects.create_user(
            email="rejected@example.com",
            name="Rejected Staff",
            password="StrongTestPassword123!",
            approval_status="rejected",
            is_active=True,
        )

        cls.emergency = Department.objects.create(
            name="Emergency",
        )

        cls.cardiology = Department.objects.create(
            name="Cardiology",
        )

        cls.nurse = Role.objects.get(name="Nurse")
        cls.doctor = Role.objects.get(name="Doctor")

        cls.active_membership = DepartmentMembership.objects.create(
            user=cls.staff,
            department=cls.emergency,
            role=cls.nurse,
        )

        cls.inactive_membership = DepartmentMembership.objects.create(
            user=cls.inactive_staff,
            department=cls.emergency,
            role=cls.doctor,
        )

        cls.pending_membership = DepartmentMembership.objects.create(
            user=cls.pending_staff,
            department=cls.cardiology,
            role=cls.nurse,
        )

        cls.rejected_membership = DepartmentMembership.objects.create(
            user=cls.rejected_staff,
            department=cls.cardiology,
            role=cls.doctor,
        )

        cls.url = reverse("membership-list-create")

    def valid_payload(self):
        return {
            "user": self.viewer.id,
            "department": self.cardiology.id,
            "role": self.doctor.id,
        }

    # GET: Membership listing

    def test_approved_staff_can_list_memberships(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            self.active_membership.id,
        )

    def test_admin_can_list_all_memberships(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

        ids = set(item["id"] for item in response.data)

        self.assertEqual(
            ids,
            {
                self.active_membership.id,
                self.inactive_membership.id,
                self.pending_membership.id,
                self.rejected_membership.id,
            },
        )

    def test_regular_staff_can_filter_by_department(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(
            self.url,
            {"department_id": self.emergency.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["department"],
            self.emergency.id,
        )

    def test_admin_can_filter_by_department(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            self.url,
            {"department_id": self.emergency.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_nonexistent_department_filter_returns_empty_list(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            self.url,
            {"department_id": 999999},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_membership_response_contains_correct_fields(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        membership = response.data[0]

        self.assertEqual(
            set(membership.keys()),
            {"id", "user", "department", "role"},
        )
        self.assertEqual(membership["user"], self.staff.id)
        self.assertEqual(
            membership["department"],
            self.emergency.id,
        )
        self.assertEqual(membership["role"], self.nurse.id)

    # GET: Query parameter validation

    def test_non_numeric_department_id_is_rejected(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(
            self.url,
            {"department_id": "abc"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("department_id", response.data)

    def test_zero_department_id_is_rejected(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(
            self.url,
            {"department_id": "0"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("department_id", response.data)

    def test_negative_department_id_is_rejected(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(
            self.url,
            {"department_id": "-5"},
        )

        self.assertEqual(response.status_code, 400)

    def test_empty_department_id_is_rejected(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(
            self.url,
            {"department_id": ""},
        )

        self.assertEqual(response.status_code, 400)

    # GET: Permissions

    def test_unauthenticated_user_cannot_list(self):
        response = self.client.get(self.url)

        self.assertIn(response.status_code, [401, 403])

    def test_pending_user_cannot_list(self):
        self.client.force_authenticate(user=self.pending_staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_rejected_user_cannot_list(self):
        self.client.force_authenticate(user=self.rejected_staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_inactive_user_cannot_list(self):
        self.client.force_authenticate(user=self.inactive_staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    # POST: Successful creation

    def test_admin_can_create_membership(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertEqual(
            response.data["user"],
            self.viewer.id,
        )
        self.assertEqual(
            response.data["department"],
            self.cardiology.id,
        )
        self.assertEqual(
            response.data["role"],
            self.doctor.id,
        )

        self.assertTrue(
            DepartmentMembership.objects.filter(
                user=self.viewer,
                department=self.cardiology,
                role=self.doctor,
            ).exists()
        )

    def test_user_can_have_multiple_departments(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "user": self.staff.id,
                "department": self.cardiology.id,
                "role": self.nurse.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.assertEqual(
            DepartmentMembership.objects.filter(
                user=self.staff,
            ).count(),
            2,
        )

    # POST: Uniqueness

    def test_duplicate_membership_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "user": self.staff.id,
                "department": self.emergency.id,
                "role": self.nurse.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            DepartmentMembership.objects.count(),
            4,
        )

    def test_same_department_different_role_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "user": self.staff.id,
                "department": self.emergency.id,
                "role": self.doctor.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            DepartmentMembership.objects.count(),
            4,
        )

    # POST: Staff eligibility

    def test_inactive_staff_cannot_be_assigned(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "user": self.inactive_staff.id,
                "department": self.cardiology.id,
                "role": self.nurse.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("user", response.data)

    def test_pending_staff_cannot_be_assigned(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "user": self.pending_staff.id,
                "department": self.emergency.id,
                "role": self.nurse.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("user", response.data)

    def test_rejected_staff_cannot_be_assigned(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "user": self.rejected_staff.id,
                "department": self.emergency.id,
                "role": self.nurse.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("user", response.data)

    # POST: Invalid references and missing fields

    def test_nonexistent_user_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        payload = self.valid_payload()
        payload["user"] = 999999

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("user", response.data)

    def test_nonexistent_department_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        payload = self.valid_payload()
        payload["department"] = 999999

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("department", response.data)

    def test_nonexistent_role_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        payload = self.valid_payload()
        payload["role"] = 999999

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("role", response.data)

    def test_missing_role_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        payload = self.valid_payload()
        payload.pop("role")

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("role", response.data)

    # POST: Permissions

    def test_regular_staff_cannot_create_membership(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["message"],
            "Administrator access required.",
        )
        self.assertEqual(
            DepartmentMembership.objects.count(),
            4,
        )

    def test_unauthenticated_user_cannot_create(self):
        response = self.client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertIn(response.status_code, [401, 403])

    def test_pending_admin_cannot_create(self):
        self.admin.approval_status = "pending"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_rejected_admin_cannot_create(self):
        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_inactive_admin_cannot_create(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    # POST: CSRF protection

    def test_post_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        response = client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            DepartmentMembership.objects.count(),
            4,
        )

    def test_post_with_valid_csrf_token_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        client.get(reverse("csrf"))

        self.assertIn("csrftoken", client.cookies)

        csrf_token = client.cookies["csrftoken"].value

        response = client.post(
            self.url,
            self.valid_payload(),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 201)

        self.assertTrue(
            DepartmentMembership.objects.filter(
                user=self.viewer,
                department=self.cardiology,
            ).exists()
        )

    # Unsupported HTTP methods

    def test_patch_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertEqual(response.status_code, 405)


class DepartmentMembershipDetailTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        cls.staff = User.objects.create_user(
            email="staff@example.com",
            name="Approved Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        cls.other_staff = User.objects.create_user(
            email="other@example.com",
            name="Other Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        cls.emergency = Department.objects.create(
            name="Emergency",
        )

        cls.cardiology = Department.objects.create(
            name="Cardiology",
        )

        cls.nurse = Role.objects.get(name="Nurse")
        cls.doctor = Role.objects.get(name="Doctor")

        cls.membership = DepartmentMembership.objects.create(
            user=cls.staff,
            department=cls.emergency,
            role=cls.nurse,
        )

        cls.other_membership = DepartmentMembership.objects.create(
            user=cls.other_staff,
            department=cls.cardiology,
            role=cls.doctor,
        )

        cls.url = reverse(
            "membership-detail",
            kwargs={"membership_id": cls.membership.id},
        )

    # =====================================================
    # PATCH: Successful updates
    # =====================================================

    def test_admin_can_update_membership_role(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], self.doctor.id)

        self.membership.refresh_from_db()

        self.assertEqual(self.membership.role, self.doctor)

    def test_patch_does_not_change_user_or_department(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.membership.refresh_from_db()

        self.assertEqual(self.membership.user, self.staff)
        self.assertEqual(
            self.membership.department,
            self.emergency,
        )

    def test_updating_to_same_role_succeeds(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": self.nurse.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], self.nurse.id)

    def test_patch_response_contains_correct_fields(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            set(response.data.keys()),
            {"id", "user", "department", "role"},
        )

        self.assertEqual(
            response.data["id"],
            self.membership.id,
        )

        self.assertEqual(
            response.data["user"],
            self.staff.id,
        )

        self.assertEqual(
            response.data["department"],
            self.emergency.id,
        )

    # =====================================================
    # PATCH: Invalid role
    # =====================================================

    def test_nonexistent_role_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": 999999},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("role", response.data)

        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, self.nurse)

    def test_invalid_role_type_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": "abc"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("role", response.data)

    def test_null_role_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": None},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("role", response.data)

    def test_empty_patch_is_rejected(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.data["message"],
            "Only the role field can be updated.",
        )

    # =====================================================
    # PATCH: Forbidden field updates
    # =====================================================

    def test_cannot_change_membership_user(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"user": self.other_staff.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.membership.refresh_from_db()
        self.assertEqual(self.membership.user, self.staff)

    def test_cannot_change_membership_department(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"department": self.cardiology.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.membership.refresh_from_db()

        self.assertEqual(
            self.membership.department,
            self.emergency,
        )

    def test_cannot_update_role_and_user_together(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {
                "role": self.doctor.id,
                "user": self.other_staff.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.membership.refresh_from_db()

        self.assertEqual(self.membership.role, self.nurse)
        self.assertEqual(self.membership.user, self.staff)

    def test_cannot_change_membership_id(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {
                "role": self.doctor.id,
                "id": 999999,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertTrue(
            DepartmentMembership.objects.filter(
                id=self.membership.id,
            ).exists()
        )

    # =====================================================
    # PATCH: Nonexistent membership
    # =====================================================

    def test_patch_nonexistent_membership_returns_404(self):
        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "membership-detail",
            kwargs={"membership_id": 999999},
        )

        response = self.client.patch(
            url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    # =====================================================
    # PATCH: Permissions
    # =====================================================

    def test_regular_staff_cannot_patch(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            response.data["message"],
            "Administrator access required.",
        )

    def test_unauthenticated_user_cannot_patch(self):
        response = self.client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertIn(response.status_code, [401, 403])

    def test_pending_admin_cannot_patch(self):
        self.admin.approval_status = "pending"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_rejected_admin_cannot_patch(self):
        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_inactive_admin_cannot_patch(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    # =====================================================
    # PATCH: CSRF protection
    # =====================================================

    def test_patch_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        response = client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, self.nurse)

    def test_patch_with_valid_csrf_token_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        client.get(reverse("csrf"))

        self.assertIn("csrftoken", client.cookies)

        csrf_token = client.cookies["csrftoken"].value

        response = client.patch(
            self.url,
            {"role": self.doctor.id},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)

        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, self.doctor)

    # =====================================================
    # DELETE: Successful deletion
    # =====================================================

    def test_admin_can_delete_membership(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

        self.assertFalse(
            DepartmentMembership.objects.filter(
                id=self.membership.id,
            ).exists()
        )

    def test_delete_preserves_user_department_and_role(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 204)

        User = get_user_model()

        self.assertTrue(
            User.objects.filter(id=self.staff.id).exists()
        )

        self.assertTrue(
            Department.objects.filter(
                id=self.emergency.id,
            ).exists()
        )

        self.assertTrue(
            Role.objects.filter(id=self.nurse.id).exists()
        )

    def test_delete_preserves_other_memberships(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 204)

        self.assertTrue(
            DepartmentMembership.objects.filter(
                id=self.other_membership.id,
            ).exists()
        )

        self.assertEqual(
            DepartmentMembership.objects.count(),
            1,
        )

    # =====================================================
    # DELETE: Missing membership
    # =====================================================

    def test_delete_nonexistent_membership_returns_404(self):
        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "membership-detail",
            kwargs={"membership_id": 999999},
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 404)

    def test_deleting_same_membership_twice_returns_404(self):
        self.client.force_authenticate(user=self.admin)

        first_response = self.client.delete(self.url)
        second_response = self.client.delete(self.url)

        self.assertEqual(first_response.status_code, 204)
        self.assertEqual(second_response.status_code, 404)

    # =====================================================
    # DELETE: Permissions
    # =====================================================

    def test_regular_staff_cannot_delete_membership(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            response.data["message"],
            "Administrator access required.",
        )

        self.assertTrue(
            DepartmentMembership.objects.filter(
                id=self.membership.id,
            ).exists()
        )

    def test_unauthenticated_user_cannot_delete(self):
        response = self.client.delete(self.url)

        self.assertIn(response.status_code, [401, 403])

        self.assertTrue(
            DepartmentMembership.objects.filter(
                id=self.membership.id,
            ).exists()
        )

    def test_pending_admin_cannot_delete(self):
        self.admin.approval_status = "pending"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 403)

    def test_rejected_admin_cannot_delete(self):
        self.admin.approval_status = "rejected"
        self.admin.save(update_fields=["approval_status"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 403)

    def test_inactive_admin_cannot_delete(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 403)

    # =====================================================
    # DELETE: CSRF protection
    # =====================================================

    def test_delete_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        response = client.delete(self.url)

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            DepartmentMembership.objects.filter(
                id=self.membership.id,
            ).exists()
        )

    def test_delete_with_valid_csrf_token_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)

        client.get(reverse("csrf"))

        self.assertIn("csrftoken", client.cookies)

        csrf_token = client.cookies["csrftoken"].value

        response = client.delete(
            self.url,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(
            DepartmentMembership.objects.filter(
                id=self.membership.id,
            ).exists()
        )

    # =====================================================
    # Unsupported HTTP methods
    # =====================================================

    def test_get_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)



class RoleListCreateTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.admin = User.objects.create_superuser(
        email="admin@example.com",
            name="Hospital Admin",
            password="StrongTestPassword123!",
        )

        cls.staff = User.objects.create_user(
            email="staff@example.com",
            name="Approved Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        cls.pending_staff = User.objects.create_user(
            email="pending@example.com",
            name="Pending Staff",
            password="StrongTestPassword123!",
            approval_status="pending",
            is_active=True,
        )

        cls.rejected_staff = User.objects.create_user(
            email="rejected@example.com",
            name="Rejected Staff",
            password="StrongTestPassword123!",
            approval_status="rejected",
            is_active=True,
        )

        cls.inactive_staff = User.objects.create_user(
            email="inactive@example.com",
            name="Inactive Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=False,
        )

        cls.nurse = Role.objects.get(name="Nurse")

        cls.doctor = Role.objects.get(name="Doctor")

        cls.url = reverse("role-list-create")

    # =====================================================
    # GET: Public role listing
    # =====================================================

    def test_unauthenticated_user_can_list_roles(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_approved_staff_can_list_roles(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_admin_can_list_roles(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_pending_user_can_list_roles(self):
        self.client.force_authenticate(user=self.pending_staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_rejected_user_can_list_roles(self):
        self.client.force_authenticate(user=self.rejected_staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_inactive_user_can_list_roles(self):
        self.client.force_authenticate(user=self.inactive_staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    # =====================================================
    # GET: Response validation
    # =====================================================

    def test_roles_are_ordered_by_id(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], self.nurse.id)
        self.assertEqual(response.data[1]["id"], self.doctor.id)

    def test_role_response_contains_correct_fields(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        role = response.data[0]

        self.assertEqual(
            set(role.keys()),
            {"id", "name", "description"},
        )

        self.assertEqual(role["id"], self.nurse.id)
        self.assertEqual(role["name"], "Nurse")
        self.assertEqual(
            role["description"],
            "Provides nursing care.",
        )

    def test_empty_role_list_returns_empty_array(self):
        Role.objects.all().delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    # =====================================================
    # POST: Role creation is disabled
    # =====================================================

    def test_admin_cannot_create_role(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {
                "name": "Coordinator",
                "description": "Coordinates tasks.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 405)

        self.assertFalse(
            Role.objects.filter(
                name="Coordinator",
            ).exists()
        )

        self.assertEqual(Role.objects.count(), 3)

    def test_unauthenticated_user_cannot_create_role(self):
        response = self.client.post(
            self.url,
            {"name": "Coordinator"},
            format="json",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Role.objects.count(), 3)

    # =====================================================
    # Unsupported HTTP methods
    # =====================================================

    def test_patch_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"name": "Updated Role"},
            format="json",
        )

        self.assertEqual(response.status_code, 405)

    def test_delete_method_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 405)

        self.assertEqual(Role.objects.count(), 3)

class RolePermissionModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.staff = User.objects.create_user(
            email="staff@example.com",
            name="Approved Staff",
            password="StrongTestPassword123!",
            approval_status="approved",
            is_active=True,
        )

        cls.nurse = Role.objects.get(name="Nurse")

        # Test-only role, not part of CareFlow's predefined roles
        cls.coordinator = Role.objects.create(
            name="Coordinator",
            description="Coordinates departmental tasks.",
        )

        cls.emergency = Department.objects.create(
            name="Emergency",
        )

    # =====================================================
    # Creating permissions
    # =====================================================

    def test_can_create_role_permission(self):
        permission = RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.view",
        )

        self.assertIsNotNone(permission.id)
        self.assertEqual(permission.role, self.coordinator)
        self.assertEqual(permission.codename, "tasks.view")

        self.assertTrue(
            RolePermission.objects.filter(
                role=self.coordinator,
                codename="tasks.view",
            ).exists()
        )

    def test_role_can_have_multiple_permissions(self):
        RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.view",
        )

        RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.assign",
        )

        RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.reassign",
        )

        self.assertEqual(
            RolePermission.objects.filter(
                role=self.coordinator,
            ).count(),
            3,
        )

    def test_different_roles_can_share_same_permission(self):
        # Nurse already has tasks.view from migration 0007.
        nurse_permission = RolePermission.objects.get(
            role=self.nurse,
            codename="tasks.view",
        )

        coordinator_permission = RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.view",
        )

        self.assertEqual(
            nurse_permission.codename,
            coordinator_permission.codename,
        )

        self.assertNotEqual(
            nurse_permission.role,
            coordinator_permission.role,
        )

        self.assertEqual(
            RolePermission.objects.filter(
                role__in=[self.nurse, self.coordinator],
                codename="tasks.view",
            ).count(),
            2,
        )

    # =====================================================
    # UniqueConstraint
    # =====================================================

    def test_duplicate_role_permission_is_rejected(self):
        RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.assign",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RolePermission.objects.create(
                    role=self.coordinator,
                    codename="tasks.assign",
                )

        self.assertEqual(
            RolePermission.objects.filter(
                role=self.coordinator,
                codename="tasks.assign",
            ).count(),
            1,
        )

    # =====================================================
    # String representation
    # =====================================================

    def test_role_permission_string_representation(self):
        permission = RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.assign",
        )

        self.assertEqual(
            str(permission),
            "Coordinator - tasks.assign",
        )

    # =====================================================
    # Reverse relationship
    # =====================================================

    def test_role_permissions_related_name(self):
        permission1 = RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.view",
        )

        permission2 = RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.assign",
        )

        self.assertEqual(
            self.coordinator.permissions.count(),
            2,
        )

        self.assertIn(
            permission1,
            self.coordinator.permissions.all(),
        )

        self.assertIn(
            permission2,
            self.coordinator.permissions.all(),
        )

    # =====================================================
    # CASCADE: Deleting an unused role
    # =====================================================

    def test_deleting_unused_role_deletes_permissions(self):
        permission = RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.assign",
        )

        permission_id = permission.id
        role_id = self.coordinator.id

        self.coordinator.delete()

        self.assertFalse(
            Role.objects.filter(id=role_id).exists()
        )

        self.assertFalse(
            RolePermission.objects.filter(
                id=permission_id,
            ).exists()
        )

    def test_cascade_preserves_other_roles_permissions(self):
        coordinator_permission = RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.assign",
        )

        # Retrieve the permission inserted by migration 0007.
        nurse_permission = RolePermission.objects.get(
            role=self.nurse,
            codename="tasks.view",
        )

        total_before = RolePermission.objects.count()

        self.coordinator.delete()

        self.assertFalse(
            RolePermission.objects.filter(
                id=coordinator_permission.id,
            ).exists()
        )

        self.assertTrue(
            Role.objects.filter(
                id=self.nurse.id,
            ).exists()
        )

        self.assertTrue(
            RolePermission.objects.filter(
                id=nurse_permission.id,
            ).exists()
        )

        self.assertEqual(
            RolePermission.objects.count(),
            total_before - 1,
        )

    # =====================================================
    # PROTECT: Role assigned to staff
    # =====================================================

    def test_cannot_delete_role_assigned_to_staff(self):
        DepartmentMembership.objects.create(
            user=self.staff,
            department=self.emergency,
            role=self.nurse,
        )

        with self.assertRaises(ProtectedError):
            self.nurse.delete()

        self.assertTrue(
            Role.objects.filter(
                id=self.nurse.id,
            ).exists()
        )

    def test_protected_role_deletion_preserves_permissions(self):
        membership = DepartmentMembership.objects.create(
            user=self.staff,
            department=self.emergency,
            role=self.nurse,
        )

        # This permission already exists.
        permission = RolePermission.objects.get(
            role=self.nurse,
            codename="tasks.view",
        )

        with self.assertRaises(ProtectedError):
            self.nurse.delete()

        self.assertTrue(
            Role.objects.filter(
                id=self.nurse.id,
            ).exists()
        )

        self.assertTrue(
            RolePermission.objects.filter(
                id=permission.id,
            ).exists()
        )

        self.assertTrue(
            DepartmentMembership.objects.filter(
                id=membership.id,
            ).exists()
        )

    # =====================================================
    # Deleting a permission directly
    # =====================================================

    def test_deleting_permission_does_not_delete_role(self):
        permission = RolePermission.objects.create(
            role=self.coordinator,
            codename="tasks.assign",
        )

        permission_id = permission.id

        permission.delete()

        self.assertFalse(
            RolePermission.objects.filter(
                id=permission_id,
            ).exists()
        )

        self.assertTrue(
            Role.objects.filter(
                id=self.coordinator.id,
            ).exists()
        )


class RegistrationWorkflowIntegrationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            name="Hospital Admin",
            password="Admin123!Test",
        )

        cls.emergency = Department.objects.create(
            name="Emergency",
            description="Emergency medical services",
        )

        cls.nurse_role = Role.objects.get(
            name="Nurse"
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

        self.register_url = "/api/auth/register/"
        self.login_url = "/api/auth/login/"
        self.pending_url = "/api/auth/registrations/pending/"
        self.csrf_url = "/api/auth/csrf/"

        self.registration_data = {
            "name": "Sara",
            "email": "sara@example.com",
            "password": "SecurePassword123!",
            "requested_department": self.emergency.id,
            "requested_role": self.nurse_role.id,
        }

    # =====================================================
    # Helpers
    # =====================================================

    def get_csrf_token(self):
        response = self.client.get(self.csrf_url)

        self.assertEqual(response.status_code, 200)

        return response.json()["csrf_token"]

    def post_with_csrf(self, url, data=None):
        token = self.get_csrf_token()

        if data is None:
            return self.client.post(
                url,
                HTTP_X_CSRFTOKEN=token,
            )

        return self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

    def register_sara(self):
        return self.post_with_csrf(
            self.register_url,
            self.registration_data,
        )

    def login_sara(self):
        return self.post_with_csrf(
            self.login_url,
            {
                "email": self.registration_data["email"],
                "password": self.registration_data["password"],
            },
        )

    # =====================================================
    # 1. Complete registration and approval workflow
    # =====================================================

    def test_complete_registration_approval_workflow(self):
        User = get_user_model()

        # Step 1: Registration options are publicly accessible.

        roles_response = self.client.get("/api/auth/roles/")
        departments_response = self.client.get(
            "/api/auth/departments/"
        )

        self.assertEqual(roles_response.status_code, 200)
        self.assertEqual(departments_response.status_code, 200)

        # Step 2: Sara registers.

        register_response = self.register_sara()

        self.assertEqual(register_response.status_code, 201)

        sara = User.objects.get(
            email=self.registration_data["email"]
        )

        self.assertEqual(sara.approval_status, "pending")
        self.assertFalse(sara.is_active)

        self.assertEqual(
            sara.requested_department,
            self.emergency
        )

        self.assertEqual(
            sara.requested_role,
            self.nurse_role
        )

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=sara
            ).exists()
        )

        # Step 3: Sara cannot log in before approval.

        pending_login_response = self.login_sara()

        self.assertEqual(pending_login_response.status_code, 403)

        # Step 4: Administrator views the pending registration.

        self.client.force_login(self.admin)

        pending_response = self.client.get(self.pending_url)

        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(len(pending_response.json()), 1)

        pending_data = pending_response.json()[0]

        self.assertEqual(pending_data["id"], sara.id)

        self.assertEqual(
            pending_data["requested_department_name"],
            "Emergency"
        )

        self.assertEqual(
            pending_data["requested_role_name"],
            "Nurse"
        )

        # Step 5: Administrator approves Sara.

        approve_url = (
            f"/api/auth/registrations/{sara.id}/approve/"
        )

        approve_response = self.post_with_csrf(approve_url)

        self.assertEqual(approve_response.status_code, 200)

        # Step 6: Verify account activation.

        sara.refresh_from_db()

        self.assertEqual(sara.approval_status, "approved")
        self.assertTrue(sara.is_active)
        self.assertFalse(sara.is_staff)
        self.assertFalse(sara.is_superuser)

        # Step 7: Verify confirmed department membership.

        memberships = DepartmentMembership.objects.filter(
            user=sara
        )

        self.assertEqual(memberships.count(), 1)

        membership = memberships.get()

        self.assertEqual(
            membership.department,
            self.emergency
        )

        self.assertEqual(
            membership.role,
            self.nurse_role
        )

        # Step 8: Sara disappears from pending registrations.

        pending_response = self.client.get(self.pending_url)

        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(pending_response.json(), [])

        # Step 9: Sara can now log in.

        self.client.logout()

        approved_login_response = self.login_sara()

        self.assertEqual(
            approved_login_response.status_code,
            200
        )

        self.assertIn("sessionid", self.client.cookies)

        # Step 10: Sara can access her protected profile.

        profile_response = self.client.get("/api/auth/me/")

        self.assertEqual(profile_response.status_code, 200)

    # =====================================================
    # 2. Complete registration and rejection workflow
    # =====================================================

    def test_complete_registration_rejection_workflow(self):
        User = get_user_model()

        # Step 1: Sara registers.

        register_response = self.register_sara()

        self.assertEqual(register_response.status_code, 201)

        sara = User.objects.get(
            email=self.registration_data["email"]
        )

        self.assertEqual(sara.approval_status, "pending")
        self.assertFalse(sara.is_active)

        # Step 2: Administrator rejects the registration.

        self.client.force_login(self.admin)

        reject_url = (
            f"/api/auth/registrations/{sara.id}/reject/"
        )

        reject_response = self.post_with_csrf(reject_url)

        self.assertEqual(reject_response.status_code, 200)

        # Step 3: Account remains inactive.

        sara.refresh_from_db()

        self.assertEqual(sara.approval_status, "rejected")
        self.assertFalse(sara.is_active)

        # Step 4: Requested information remains available.

        self.assertEqual(
            sara.requested_department,
            self.emergency
        )

        self.assertEqual(
            sara.requested_role,
            self.nurse_role
        )

        # Step 5: No confirmed membership exists.

        self.assertFalse(
            DepartmentMembership.objects.filter(
                user=sara
            ).exists()
        )

        # Step 6: Sara disappears from pending registrations.

        pending_response = self.client.get(self.pending_url)

        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(pending_response.json(), [])

        # Step 7: Sara cannot log in.

        self.client.logout()

        login_response = self.login_sara()

        self.assertEqual(login_response.status_code, 403)

        self.assertEqual(
            login_response.json()["error"],
            "Your registration request was rejected."
        )
