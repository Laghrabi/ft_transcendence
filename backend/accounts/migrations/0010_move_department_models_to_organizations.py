from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_department_accepts_new_tasks"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="user",
                    name="requested_department",
                    field=models.ForeignKey(
                        to="organizations.department",
                        on_delete=django.db.models.deletion.PROTECT,
                        null=True,
                        blank=True,
                        related_name="registration_requests",
                    ),
                ),

                migrations.AlterField(
                    model_name="user",
                    name="requested_role",
                    field=models.ForeignKey(
                        to="organizations.role",
                        on_delete=django.db.models.deletion.PROTECT,
                        null=True,
                        blank=True,
                        related_name="registration_requests",
                    ),
                ),

                migrations.DeleteModel(
                    name="DepartmentMembership",
                ),

                migrations.DeleteModel(
                    name="RolePermission",
                ),

                migrations.DeleteModel(
                    name="Department",
                ),

                migrations.DeleteModel(
                    name="Role",
                ),
            ],
        ),
    ]