from django.urls import path
from .views import AnalyticsSummaryAPIView

urlpatterns = [
    path("summary/", AnalyticsSummaryAPIView.as_view(), name="analytics-summary"),
]