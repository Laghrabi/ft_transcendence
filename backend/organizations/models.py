from django.conf import settings
from django.db import models

class Department(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(default=True)

    accepts_new_tasks = models.BooleanField(default=True)

    class Meta:
        db_table = "accounts_department"

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

    class Meta:
        db_table = "accounts_role"

    def __str__(self):
        return self.name


class DepartmentMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
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
        db_table = "accounts_departmentmembership"

        constraints = [
            models.UniqueConstraint(
                fields=["user", "department"],
                name="unique_user_department"
            )
        ]

    def __str__(self):
        return f"{self.user.name} - {self.department.name} - {self.role.name}"


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="permissions"
    )

    codename = models.CharField(max_length=100)

    class Meta:
        db_table = "accounts_rolepermission"

        constraints = [
            models.UniqueConstraint(
                fields=["role", "codename"],
                name="unique_role_permission"
            )
        ]

    def __str__(self):
        return f"{self.role.name} - {self.codename}"
