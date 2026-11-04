# from django.test import TestCase

# from rest_framework.test import APITestCase


# from django.contrib.auth import get_user_model
# from django.urls import reverse
# from rest_framework import status

# from .models import Case, Comment


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
# APITestCase	A DRF class for testing APIs
# setUp()	Prepares fresh data before each test
# self.client	A fake HTTP client used for testing
# assertEqual(a, b)	Checks that two values are equal
# assertIn(a, b)	Checks whether a is inside b
# assertIsNone(a)	Checks whether a value is None
# reverse()	Finds a URL using its Django route name
# refresh_from_db()	Reloads an object from the database