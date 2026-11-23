from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_seed_default_roles_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]