from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import UserManager

class User(AbstractUser):
    APPROVAL_CHOICES = [
        ("approved", "Approved"),
        ("pending", "Pending"),
        ("rejected", "Rejected"),
    ]

    username = None

    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    avatar = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=20, default="offline")
    approval_status = models.CharField(max_length=10, choices=APPROVAL_CHOICES, default="pending")
    phone_number = models.CharField(max_length=20, blank=True, default="")
    show_phone_number = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self):
        return self.email


class Department(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True
    )
    description = models.TextField(
        blank=True
    )

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True
    )
    description = models.TextField(
        blank=True
    )

    def __str__(self):
        return self.name


class DepartmentMembership(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "department"],
                name="unique_user_department"
            )
        ]

    def __str__(self):
        return f"{self.user.name} - {self.department.name} - {self.role.name}"
