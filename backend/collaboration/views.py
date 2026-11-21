from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Case, Comment, Notification
from .serializers import CommentSerializer, NotificationSerializer
from rest_framework import status


class CaseCommentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, case_id):
        case = get_object_or_404(Case, id=case_id)
        comments = Comment.objects.filter(case=case)
        data = CommentSerializer(comments, many=True)
        return Response({"comments": data.data} )

    def post(self, request, case_id):
        case = get_object_or_404(Case, id=case_id)
        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(author=request.user, case=case)
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
    
class NotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        notification = Notification.objects.filter(recipient= request.user)
        data = NotificationSerializer(notification, many=True)
        return Response({"notifications" : data.data})


class NotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)