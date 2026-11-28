from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .serializers import AnalyticsDateRangeSerializer
from .services import get_analytics_summary, get_staff_summary, get_departments_summary, get_department_metrics, get_dashboard_summary
from accounts.permissions import can_view_hospital_analytics, can_view_department_analytics
from organizations.models import Department
from .csv_utils import summary_to_csv


def _can_view_requested_analytics(user, department_id):

    if department_id is None:
        return can_view_hospital_analytics(user)

    department = get_object_or_404(
        Department,
        id=department_id
    )

    return can_view_department_analytics(user, department)

class AnalyticsSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        serializer = AnalyticsDateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        if not _can_view_requested_analytics(request.user, filters.get("department_id")):
            return Response({"detail": "Permission denied."},status=403)
        return Response(get_analytics_summary(**filters), status=200)

class AnalyticsExportAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        serializer = AnalyticsDateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        if not _can_view_requested_analytics(request.user, filters.get("department_id")):
            return Response({"detail": "Permission denied."},status=403)
        summary = get_analytics_summary(**filters)
        return summary_to_csv(summary=summary)


class AnalyticsStaffAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not can_view_hospital_analytics(request.user):
            return Response({"detail": "Permission denied."},status=403)
        return Response(get_staff_summary())


class AnalyticsDepartmentsAPIView(APIView): 
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not can_view_hospital_analytics(request.user):
            return Response({"detail": "Permission denied."},status=403)
        return Response(get_departments_summary())


class AnalyticsDepartmentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, department_id):
        department = get_object_or_404(Department, id=department_id)

        if not can_view_department_analytics(request.user, department):
            return Response({"detail": "Permission denied."}, status=403)

        return Response(get_department_metrics(department_id))


class AnalyticsDashboardAPIView(APIView): 
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not can_view_hospital_analytics(request.user):
            return Response({"detail": "Permission denied."},status=403)
        return Response(get_dashboard_summary())