from django.urls import path
from .views import AnalyticsSummaryAPIView, AnalyticsExportAPIView

urlpatterns = [
    path("summary/", AnalyticsSummaryAPIView.as_view(), name="analytics-summary"),
    path("export/", AnalyticsExportAPIView.as_view(), name="analytics-export"),
    
]