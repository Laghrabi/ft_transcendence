from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework import status
from django.test import TestCase, Client, override_settings
import json


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
