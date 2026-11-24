
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from organizations.models import Department, DepartmentMembership, Role


class Command(BaseCommand):
    help = "Create temporary CareFlow development data."

    def add_arguments(self, parser):
        parser.add_argument("--confirm-local", action="store_true")
        parser.add_argument("--with-staff", action="store_true")

    def handle(self, *args, **options):
        if not settings.DEBUG or not options["confirm_local"]:
            raise CommandError(
                "Development seed requires DEBUG=True and --confirm-local."
            )

        with transaction.atomic():
            admin = self.ensure_superuser()

            department, created = Department.objects.get_or_create(
                name="Emergency",
                defaults={"description": "Emergency medical services"},
            )

            if not department.is_active:
                raise CommandError("Emergency department is inactive.")

            self.ensure_department_admin(admin, department)

            if options["with_staff"]:
                self.ensure_staff(
                    "Doctor",
                    "Development Doctor",
                    "dev.doctor@example.test",
                    department,
                )
                self.ensure_staff(
                    "Nurse",
                    "Development Nurse",
                    "dev.nurse@example.test",
                    department,
                )

        self.stdout.write(
            self.style.SUCCESS("Development data is ready.")
        )

    def ensure_superuser(self):
        User = get_user_model()

        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()
        name = os.getenv("DJANGO_SUPERUSER_NAME", "").strip()

        if not email or not name:
            raise CommandError(
                "DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_NAME are required."
            )

        user = User.objects.filter(email__iexact=email).first()

        if user is not None:
            if not (
                user.is_superuser
                and user.is_staff
                and user.is_active
                and user.approval_status == "approved"
            ):
                raise CommandError(
                    "Configured email already belongs to a non-active "
                    "or non-approved superuser account."
                )
            return user

        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "")

        if not password:
            raise CommandError("DJANGO_SUPERUSER_PASSWORD is required.")

        self.check_password(password, User(email=email, name=name))

        return User.objects.create_superuser(
            email=email,
            name=name,
            password=password,
        )

    def ensure_department_admin(self, admin, department):
        try:
            role = Role.objects.get(name="Administrator")
        except Role.DoesNotExist as exc:
            raise CommandError("Run database migrations first.") from exc

        current_admin = DepartmentMembership.objects.filter(
            department=department,
            role=role,
        ).first()

        if current_admin is not None:
            self.stdout.write("Existing department Administrator preserved.")
            return

        membership, created = DepartmentMembership.objects.get_or_create(
            user=admin,
            department=department,
            defaults={"role": role},
        )

        if membership.role_id != role.id:
            raise CommandError(
                "Superuser already has a different role in Emergency."
            )

    def ensure_staff(self, role_name, name, email, department):
        User = get_user_model()

        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist as exc:
            raise CommandError("Run database migrations first.") from exc

        user = User.objects.filter(email__iexact=email).first()

        if user is not None:
            valid_membership = DepartmentMembership.objects.filter(
                user=user,
                department=department,
                role=role,
            ).exists()

            if not (
                user.is_active
                and user.approval_status == "approved"
                and valid_membership
            ):
                raise CommandError(
                    f"Existing account {email} conflicts with seed data."
                )
            return

        password = os.getenv("DEV_STAFF_PASSWORD", "")

        if not password:
            raise CommandError("DEV_STAFF_PASSWORD is required.")

        self.check_password(password, User(email=email, name=name))

        user = User.objects.create_user(
            email=email,
            name=name,
            password=password,
            is_active=True,
            approval_status="approved",
            requested_department=department,
            requested_role=role,
        )

        DepartmentMembership.objects.create(
            user=user,
            department=department,
            role=role,
        )

    def check_password(self, password, user):
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
