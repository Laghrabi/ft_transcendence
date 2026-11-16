from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework import status
from .serializers import AnalyticsDateRangeSerializer




class AnalyticsSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        serializer = AnalyticsDateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        dates = serializer.validated_data
        return Response({"detail": "Analytics calculations are not implemented yet."}, status=501)
    # def post(self, request):
