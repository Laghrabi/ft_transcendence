from django.test import TestCase
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from .models import Case, Comment
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from .models import Notification
from django.test import TestCase
from collaboration.services.notifications import create_notification
from collaboration.services.events import handle_event
from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from channels.testing import WebsocketCommunicator
from collaboration.consumers import NotificationConsumer

# class CommentAPITests(APITestCase):

#     def setUp(self):
#         # This runs before EACH test.
#         User = get_user_model()

#         self.user = User.objects.create_user(
#             username="test_doctor",
#             password="test_password_123!"
#         )

#         self.other_user = User.objects.create_user(
#             username="other_doctor",
#             password="test_password_456!"
#         )

#         self.case = Case.objects.create(
#             title="Patient transfer"
#         )

#         self.other_case = Case.objects.create(
#             title="Equipment request"
#         )

#         self.url = reverse(
#             "case-comments",
#             kwargs={"case_id": self.case.id}
#         )

#         self.client.force_authenticate(user=self.user)

#     # 1. POST should create a comment.
#     def test_create_comment(self):
#         response = self.client.post(
#             self.url,
#             {"content": "Patient is ready"},
#             format="json"
#         )

#         self.assertEqual(
#             response.status_code,
#             status.HTTP_201_CREATED
#         )

#         self.assertEqual(Comment.objects.count(), 1)

#         comment = Comment.objects.first()
#         self.assertEqual(comment.content, "Patient is ready")
#         self.assertEqual(comment.author, self.user)
#         self.assertEqual(comment.case, self.case)
#         self.assertIsNotNone(comment.created_at)

#     # 2. GET should return saved comments.
#     def test_get_comments(self):
#         comment = Comment.objects.create(
#             author=self.user,
#             case=self.case,
#             content="Transport confirmed"
#         )

#         response = self.client.get(self.url)

#         self.assertEqual(
#             response.status_code,
#             status.HTTP_200_OK
#         )
#         self.assertEqual(len(response.data["comments"]), 1)
#         self.assertEqual(
#             response.data["comments"][0]["id"],
#             comment.id
#         )

#     # 3. GET should return comments only for the requested case.
#     def test_get_comments_filters_by_case(self):
#         Comment.objects.create(
#             author=self.user,
#             case=self.case,
#             content="Comment for first case"
#         )

#         Comment.objects.create(
#             author=self.user,
#             case=self.other_case,
#             content="Comment for second case"
#         )

#         response = self.client.get(self.url)

#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(len(response.data["comments"]), 1)
#         self.assertEqual(
#             response.data["comments"][0]["content"],
#             "Comment for first case"
#         )

#     # 4. Empty comments must be rejected.
#     def test_empty_comment(self):
#         response = self.client.post(
#             self.url,
#             {"content": ""},
#             format="json"
#         )

#         self.assertEqual(response.status_code, 400)
#         self.assertEqual(Comment.objects.count(), 0)

#     # 5. Comments containing only spaces must be rejected.
#     def test_whitespace_comment(self):
#         response = self.client.post(
#             self.url,
#             {"content": "     "},
#             format="json"
#         )

#         self.assertEqual(response.status_code, 400)
#         self.assertEqual(Comment.objects.count(), 0)

#     # 6. Comments longer than 200 characters must be rejected.
#     def test_comment_too_long(self):
#         response = self.client.post(
#             self.url,
#             {"content": "A" * 201},
#             format="json"
#         )

#         self.assertEqual(response.status_code, 400)
#         self.assertEqual(Comment.objects.count(), 0)

#     # 7. Short comments are allowed.
#     def test_short_comment(self):
#         response = self.client.post(
#             self.url,
#             {"content": "OK"},
#             format="json"
#         )

#         self.assertEqual(response.status_code, 201)

#     # 8. GET for a nonexistent case returns 404.
#     def test_get_nonexistent_case(self):
#         url = reverse(
#             "case-comments",
#             kwargs={"case_id": 999999}
#         )

#         response = self.client.get(url)

#         self.assertEqual(response.status_code, 404)

#     # 9. POST for a nonexistent case returns 404.
#     def test_post_nonexistent_case(self):
#         url = reverse(
#             "case-comments",
#             kwargs={"case_id": 999999}
#         )

#         response = self.client.post(
#             url,
#             {"content": "Testing missing case"},
#             format="json"
#         )

#         self.assertEqual(response.status_code, 404)
#         self.assertEqual(Comment.objects.count(), 0)

#     # 10. A visitor who is not logged in cannot GET comments.
#     def test_unauthenticated_get(self):
#         self.client.force_authenticate(user=None)

#         response = self.client.get(self.url)

#         self.assertIn(response.status_code, [401, 403])

#     # 11. A visitor who is not logged in cannot POST comments.
#     def test_unauthenticated_post(self):
#         self.client.force_authenticate(user=None)

#         response = self.client.post(
#             self.url,
#             {"content": "Unauthorized comment"},
#             format="json"
#         )

#         self.assertIn(response.status_code, [401, 403])
#         self.assertEqual(Comment.objects.count(), 0)

#     # 12. A user cannot pretend to be another comment author.
#     def test_cannot_fake_author(self):
#         response = self.client.post(
#             self.url,
#             {
#                 "author": self.other_user.id,
#                 "content": "Testing author protection"
#             },
#             format="json"
#         )

#         self.assertEqual(response.status_code, 201)

#         comment = Comment.objects.get()
#         self.assertEqual(comment.author, self.user)
#         self.assertNotEqual(comment.author, self.other_user)

#     # 13. A user cannot change the case using POST data.
#     def test_cannot_fake_case(self):
#         response = self.client.post(
#             self.url,
#             {
#                 "case": self.other_case.id,
#                 "content": "Testing case protection"
#             },
#             format="json"
#         )

#         self.assertEqual(response.status_code, 201)

#         comment = Comment.objects.get()
#         self.assertEqual(comment.case, self.case)
#         self.assertNotEqual(comment.case, self.other_case)

#     # 14. Deleting an author should preserve comment history.
#     def test_comment_remains_after_author_deleted(self):
#         comment = Comment.objects.create(
#             author=self.user,
#             case=self.case,
#             content="Important historical comment"
#         )

#         self.user.delete()
#         comment.refresh_from_db()

#         self.assertIsNone(comment.author)
#         self.assertEqual(
#             comment.content,
#             "Important historical comment"
#         )
        
    



# class NotificationAPITests(APITestCase):

#     def setUp(self):
#         User = get_user_model()

#         self.sara = User.objects.create_user(username="sara_notify")
#         self.hamza = User.objects.create_user(username="hamza_notify")

#         self.sara_notification = Notification.objects.create(
#             recipient=self.sara,
#             message="New task assigned"
#         )

#         self.hamza_notification = Notification.objects.create(
#             recipient=self.hamza,
#             message="Case completed"
#         )

#         self.list_url = reverse("notification_list")
#         self.client.force_authenticate(user=self.sara)

#     def test_new_notification_is_unread(self):
#         self.assertFalse(self.sara_notification.is_read)

#     def test_get_only_own_notifications(self):
#         response = self.client.get(self.list_url)

#         self.assertEqual(response.status_code, 200)

#         notifications = response.data["notifications"]
#         self.assertEqual(len(notifications), 1)
#         self.assertEqual(
#             notifications[0]["id"],
#             self.sara_notification.id
#         )

#     def test_mark_own_notification_as_read(self):
#         url = reverse(
#             "read_notification",
#             kwargs={"notification_id": self.sara_notification.id}
#         )

#         response = self.client.patch(url)

#         self.assertEqual(response.status_code, 200)

#         self.sara_notification.refresh_from_db()
#         self.assertTrue(self.sara_notification.is_read)

#     def test_cannot_mark_other_users_notification(self):
#         url = reverse(
#             "read_notification",
#             kwargs={"notification_id": self.hamza_notification.id}
#         )

#         response = self.client.patch(url)

#         self.assertEqual(response.status_code, 404)

#         self.hamza_notification.refresh_from_db()
#         self.assertFalse(self.hamza_notification.is_read)

#     def test_nonexistent_notification(self):
#         url = reverse(
#             "read_notification",
#             kwargs={"notification_id": 999999}
#         )

#         response = self.client.patch(url)

#         self.assertEqual(response.status_code, 404)

#     def test_unauthenticated_get(self):
#         self.client.force_authenticate(user=None)

#         response = self.client.get(self.list_url)

#         self.assertIn(response.status_code, [401, 403])

#     def test_unauthenticated_patch(self):
#         self.client.force_authenticate(user=None)

#         url = reverse(
#             "read_notification",
#             kwargs={"notification_id": self.sara_notification.id}
#         )

#         response = self.client.patch(url)

#         self.assertIn(response.status_code, [401, 403])

#         self.sara_notification.refresh_from_db()
#         self.assertFalse(self.sara_notification.is_read)

#     def test_hamza_sees_only_his_notifications(self):
#         self.client.force_authenticate(user=self.hamza)

#         response = self.client.get(self.list_url)

#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(
#             response.data["notifications"][0]["id"],
#             self.hamza_notification.id
#         )
#         self.assertEqual(len(response.data["notifications"]), 1)
   



# class NotificationServiceTests(TestCase):

#     def test_create_notification(self):
#         User = get_user_model()
#         self.user = User.objects.create_user(
#             username="salma",
#             password="test_password_123!"
#         )
#         notification = create_notification(recipient= self.user, message="task from case 2")
#         self.assertEqual(notification.recipient, self.user)
#         self.assertFalse(notification.is_read)

class EventHandlerTests(TestCase):
    def test_create_notification(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="salma",
            password="test_password_123!"
        )
        with self.assertRaises(ValueError):
            handle_event(event_type="gt", recipient=user, task_id=1)

        self.assertEqual(Notification.objects.count(), 0)
        notification = handle_event(event_type="case.completed", recipient= user, case_id=1)
        self.assertEqual(notification.recipient, user)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertIn("1", notification.message)
        # self.assertIsNone(notification)





class NotificationConsumerTests(TestCase):

    async def test_anonymous_connection_rejected(self):
        communicator = WebsocketCommunicator(NotificationConsumer.as_asgi(),"/ws/notifications/")

        communicator.scope["user"] = AnonymousUser()

        connected, _ = await communicator.connect()

        self.assertFalse(connected)

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="salma",
            password="test_password_123!"
        )
    async def test_anonymous_connection_accepted(self):
        com = WebsocketCommunicator(NotificationConsumer.as_asgi(), "/ws/notifications/")
        com.scope["user"] = self.user
        ced, _ = await com.connect()
        self.assertTrue(ced)
        await com.disconnect()














# APITestCase	A DRF class for testing APIs
# setUp()	Prepares fresh data before each test
# self.client	A fake HTTP client used for testing
# assertEqual(a, b)	Checks that two values are equal
# assertIn(a, b)	Checks whether a is inside b
# assertIsNone(a)	Checks whether a value is None
# reverse()	Finds a URL using its Django route name
# refresh_from_db()	Reloads an object from the database









