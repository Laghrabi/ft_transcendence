from django.urls import path
from .views import AnalyticsSummaryAPIView, AnalyticsExportAPIView, AnalyticsStaffAPIView, AnalyticsDepartmentsAPIView
from .views import AnalyticsDepartmentDetailAPIView, AnalyticsDashboardAPIView

urlpatterns = [
    path("summary/", AnalyticsSummaryAPIView.as_view(), name="analytics-summary"),
    path("export/", AnalyticsExportAPIView.as_view(), name="analytics-export"),
    path("staff/", AnalyticsStaffAPIView.as_view(), name="analytics-staff"),
    path("departments/", AnalyticsDepartmentsAPIView.as_view(), name="analytics-departments"),
    path("departments/<int:department_id>/",AnalyticsDepartmentDetailAPIView.as_view(),name="analytics-department-detail"),
    path("dashboard/",AnalyticsDashboardAPIView.as_view(),name="analytics-dashboard"),

]