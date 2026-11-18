from django.test import TestCase
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from .csv_utils import summary_to_csv


class AnalyticsAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="analytics_test",
            password="test_password_123!"
        )

        self.client.force_authenticate(user=self.user)

    def test_valid_date_range(self):
        response = self.client.get(
            "/api/analytics/summary/",
            {
                "start_date": "2026-11-01",
                "end_date": "2026-12-15"
            }
        )

        self.assertEqual(response.status_code, 501)


class CSVExportTests(SimpleTestCase):
    def test_summary_to_csv(self):
        summary = {
            "total_cases": 7,
            "completed_cases": 3
        }

        response = summary_to_csv(summary)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        csv_text = response.content.decode("utf-8")

        self.assertIn("metric,value", csv_text)
        self.assertIn("total_cases,7", csv_text)
        self.assertIn("completed_cases,3", csv_text)





class AnalyticsExportAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="analytics_export_test",
            password="test_password_123!"
        )

        self.client.force_authenticate(user=self.user)
        self.url = "/api/analytics/export/"

    def test_export_without_dates(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 501)

    def test_export_with_valid_dates(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2026-11-01",
                "end_date": "2026-11-15"
            }
        )

        self.assertEqual(response.status_code, 501)

    def test_export_with_invalid_date(self):
        response = self.client.get(
            self.url,
            {"start_date": "hello"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("start_date", response.data)

    def test_export_with_reversed_dates(self):
        response = self.client.get(
            self.url,
            {
                "start_date": "2026-11-20",
                "end_date": "2026-11-01"
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("end_date", response.data)

    def test_export_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertIn(response.status_code, [401, 403])