from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework import status
from .serializers import AnalyticsDateRangeSerializer
from .services import get_analytics_summary



class AnalyticsSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        serializer = AnalyticsDateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        dates = serializer.validated_data
        return Response(get_analytics_summary(), status=200)
    # def post(self, request):

class AnalyticsExportAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        serializer = AnalyticsDateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        dates = serializer.validated_data
        return Response({"detail": "Analytics export is not implemented yet."}, status=501)