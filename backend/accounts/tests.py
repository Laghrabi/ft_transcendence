from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework import status
from django.test import TestCase, Client, override_settings
import json
from types import SimpleNamespace
from django.contrib.auth.models import AnonymousUser
from .serializers import UserProfileSerializer
from django.urls import reverse


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

        self.valid_data = {
            "name": "Sara",
            "email": "sara.new@example.com",
            "password": "SecurePassword123!"
        }

    # Helpers

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
                "password": password
            }),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.get_csrf_token()
        )

    # 1. Successful registration

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

        self.assertEqual(response.json()["id"], user.id)
        self.assertEqual(
            response.json()["message"],
            "Registration successful. Awaiting administrator approval."
        )

        self.assertEqual(self.User.objects.count(), 1)

    # 2. Password security

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

    # 3. Prevent privilege escalation

    def test_client_cannot_assign_admin_privileges(self):
        data = self.valid_data.copy()

        data.update({
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
            "approval_status": "approved"
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

    # 4. Login restrictions

    def test_pending_user_cannot_login(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)

        login_response = self.login(
            self.valid_data["email"],
            self.valid_data["password"]
        )

        # UPDATED: Pending accounts return 403 instead of 401
        self.assertEqual(login_response.status_code, 403)

        # NEW: Verify the correct error message
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

        # UPDATED: Pending accounts return 403 instead of 401
        self.assertEqual(login_response.status_code, 403)

        # NEW: Verify the correct error message
        self.assertEqual(
            login_response.json()["error"],
        "Your account is awaiting administrator approval."
        )

    # 5. Email validation

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

    # 6. Required fields

    def test_missing_required_fields_are_rejected(self):
        fields = ("name", "email", "password")
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
        fields = ("name", "email", "password")
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

    # 7. Password validation

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
            "sara.new@example.com"
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

    # 8. CSRF protection

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

    # 9. HTTP method restrictions

    def test_get_registration_is_not_allowed(self):
        response = self.client.get(self.register_url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.User.objects.count(), 0)


class PendingRegistrationsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.pending_url = "/api/auth/registrations/pending/"

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
            name="Sara"
        )

        cls.pending_lina = User.objects.create_user(
            email="lina@example.com",
            password="Lina123!Test",
            name="Lina"
        )

        cls.rejected_user = User.objects.create_user(
            email="rejected@example.com",
            password="Rejected123!Test",
            name="Rejected User",
            approval_status="rejected"
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    # 1. Administrator can access the endpoint

    def test_admin_can_list_pending_registrations(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    # 2. Only pending registrations are returned

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

    # 3. Response contains only permitted fields

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
            "approval_status"
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
            index += 1

    # 4. Regular authenticated users cannot access

    def test_regular_user_cannot_list_pending_registrations(self):
        self.client.force_login(self.nurse)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["message"],
            "Administrator access required."
        )

    # 5. is_staff alone does not grant administrator access

    def test_staff_user_without_superuser_cannot_access(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["message"],
            "Administrator access required."
        )

    # 6. Unauthenticated users cannot access

    def test_unauthenticated_user_cannot_access(self):
        response = self.client.get(self.pending_url)

        self.assertIn(response.status_code, [401, 403])

    # 7. Empty pending list returns an empty array

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
            name="Sara"
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

    # Helpers

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

    # 1. Successful approval

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

    # 2. Approved user can log in

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

    # 3. Regular user cannot approve

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

    # 4. is_staff alone is not enough

    def test_staff_user_cannot_approve(self):
        self.client.force_login(self.staff_user)

        response = self.approve(self.pending_user.id)

        self.assertEqual(response.status_code, 403)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )

    # 5. Unauthenticated users cannot approve

    def test_unauthenticated_user_cannot_approve(self):
        response = self.approve(self.pending_user.id)

        self.assertIn(response.status_code, [401, 403])

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )
        self.assertFalse(self.pending_user.is_active)

    # 6. Nonexistent user returns 404

    def test_approve_nonexistent_user(self):
        self.client.force_login(self.admin)

        response = self.approve(999999)

        self.assertEqual(response.status_code, 404)

    # 7. Already approved user returns 409

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

    # 8. Rejected user cannot be approved

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

    # 9. Approving twice returns 409

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

    # 10. Missing CSRF token returns 403

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

    # 11. Invalid CSRF token returns 403

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

    # 12. GET requests are not allowed

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
            name="Pending User"
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

    # Helpers

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

    # 1. Successful rejection

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

    # 2. Rejected user cannot log in

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

    # 3. Regular users cannot reject registrations

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

    # 4. is_staff does not grant approval privileges

    def test_staff_user_cannot_reject(self):
        self.client.force_login(self.staff_user)

        response = self.reject(self.pending_user.id)

        self.assertEqual(response.status_code, 403)

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )

    # 5. Unauthenticated users cannot reject

    def test_unauthenticated_user_cannot_reject(self):
        response = self.reject(self.pending_user.id)

        self.assertIn(response.status_code, [401, 403])

        self.pending_user.refresh_from_db()

        self.assertEqual(
            self.pending_user.approval_status,
            "pending"
        )
        self.assertFalse(self.pending_user.is_active)

    # 6. Nonexistent user returns 404

    def test_reject_nonexistent_user(self):
        self.client.force_login(self.admin)

        response = self.reject(999999)

        self.assertEqual(response.status_code, 404)

    # 7. Approved registration cannot be rejected

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

    # 8. Already rejected registration returns 409

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

    # 9. Rejecting the same account twice

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

    # 10. CSRF token is required

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

    # 11. Invalid CSRF token is rejected

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

    # 12. GET requests are not allowed

    def test_get_request_is_not_allowed(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            self.rejection_url(self.pending_user.id)
        )

        self.assertEqual(response.status_code, 405)

    # 13. Rejected users disappear from pending list

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
