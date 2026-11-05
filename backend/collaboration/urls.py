# path("example/<int:item_id>/", SomeView.as_view(), name="example")

from django.urls import path
from .views import CaseCommentsAPIView, NotificationListAPIView, NotificationReadAPIView

urlpatterns = [
    path("cases/<int:case_id>/comments/", CaseCommentsAPIView.as_view(), name="case-comments"),
    path("notifications/", NotificationListAPIView.as_view(), name="notification_list"),
    path("notifications/<int:notification_id>/read/", NotificationReadAPIView.as_view(), name="read_notification"),
    

]