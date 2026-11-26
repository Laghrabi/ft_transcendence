from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from organizations.models import Department


class DepartmentTimestampTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(
            name="Cardiology"
        )

    def test_creation_sets_timestamps(self):
        self.assertIsNotNone(
            self.department.created_at
        )
        self.assertIsNotNone(
            self.department.updated_at
        )

        self.assertGreaterEqual(
            self.department.updated_at,
            self.department.created_at,
        )

    def test_update_preserves_creation_timestamp(self):
        created_at = self.department.created_at

        self.department.name = "Updated Cardiology"
        self.department.save()
        self.department.refresh_from_db()

        self.assertEqual(
            self.department.created_at,
            created_at,
        )

    def test_save_updates_modification_timestamp(self):
        old_timestamp = (
            timezone.now() - timedelta(days=1)
        )

        Department.objects.filter(
            pk=self.department.pk
        ).update(updated_at=old_timestamp)

        self.department.refresh_from_db()

        self.department.description = (
            "Updated department description."
        )
        self.department.save()
        self.department.refresh_from_db()

        self.assertGreater(
            self.department.updated_at,
            old_timestamp,
        )

    def test_partial_save_updates_timestamp(self):
        old_timestamp = (
            timezone.now() - timedelta(days=1)
        )

        Department.objects.filter(
            pk=self.department.pk
        ).update(updated_at=old_timestamp)

        self.department.refresh_from_db()

        self.department.is_active = False

        self.department.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        self.department.refresh_from_db()

        self.assertGreater(
            self.department.updated_at,
            old_timestamp,
        )