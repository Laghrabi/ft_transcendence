from django.db import migrations


TASK_PERMISSIONS = (
    "tasks.view",
    "tasks.create",
    "tasks.assign",
    "tasks.reassign",
    "tasks.update_assigned",
    "tasks.complete",
    "tasks.cancel",
)


def seed_default_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    role_names = (
        "Nurse",
        "Doctor",
        "Administrator",
    )

    descriptions = (
        "Provides nursing care.",
        "Provides medical care.",
        "Manages staff and registrations within an assigned department.",
    )

    database = schema_editor.connection.alias

    i = 0
    while i < len(role_names):
        role, created = Role.objects.using(database).get_or_create(
            name=role_names[i],
            defaults={
                "description": descriptions[i]
            }
        )

        j = 0
        while j < len(TASK_PERMISSIONS):
            RolePermission.objects.using(database).get_or_create(
                role_id=role.id,
                codename=TASK_PERMISSIONS[j]
            )

            j += 1

        i += 1


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_user_requested_department_user_requested_role"),
    ]

    operations = [
        migrations.RunPython(
            seed_default_roles,
            migrations.RunPython.noop
        ),
    ]
