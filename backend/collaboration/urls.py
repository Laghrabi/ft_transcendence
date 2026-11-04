# path("example/<int:item_id>/", SomeView.as_view(), name="example")

from django.urls import path
from .views import CaseCommentsAPIView

urlpatterns = [
    path("cases/<int:case_id>/comments/", CaseCommentsAPIView.as_view(), name="case-comments"),
]