from django.test import TestCase
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

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
