from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0009_department_accepts_new_tasks"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Department",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "name",
                            models.CharField(
                                max_length=100,
                                unique=True,
                            ),
                        ),
                        (
                            "description",
                            models.TextField(blank=True),
                        ),
                        (
                            "is_active",
                            models.BooleanField(default=True),
                        ),
                        (
                            "accepts_new_tasks",
                            models.BooleanField(default=True),
                        ),
                    ],
                    options={
                        "db_table": "accounts_department",
                    },
                ),

                migrations.CreateModel(
                    name="Role",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "name",
                            models.CharField(
                                max_length=100,
                                unique=True,
                            ),
                        ),
                        (
                            "description",
                            models.TextField(blank=True),
                        ),
                    ],
                    options={
                        "db_table": "accounts_role",
                    },
                ),

                migrations.CreateModel(
                    name="DepartmentMembership",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "department",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                to="organizations.department",
                            ),
                        ),
                        (
                            "role",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                to="organizations.role",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "accounts_departmentmembership",
                        "constraints": [
                            models.UniqueConstraint(
                                fields=["user", "department"],
                                name="unique_user_department",
                            ),
                        ],
                    },
                ),

                migrations.CreateModel(
                    name="RolePermission",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "codename",
                            models.CharField(max_length=100),
                        ),
                        (
                            "role",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="permissions",
                                to="organizations.role",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "accounts_rolepermission",
                        "constraints": [
                            models.UniqueConstraint(
                                fields=["role", "codename"],
                                name="unique_role_permission",
                            ),
                        ],
                    },
                ),
            ],
        ),
    ]