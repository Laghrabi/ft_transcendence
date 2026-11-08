from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout, get_user_model
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import RegisterSerializer, PendingRegistrationSerializer, UserProfileSerializer, UpdateProfileSerializer
from .models import User
from django.shortcuts import get_object_or_404
from .permissions import IsApprovedUser

@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not isinstance(email, str) or not isinstance(password, str):
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        authenticated_user = authenticate(
            request,
            email=email,
            password=password
        )

        user = authenticated_user

        if user is None:
            User = get_user_model()
            user = User.objects.filter(email=email).first()

            if user is None or not user.check_password(password):
                return Response(
                    {"error": "Invalid email or password."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        if user.approval_status == "pending":
            return Response(
                {"error": "Your account is awaiting administrator approval."},
                status=status.HTTP_403_FORBIDDEN
            )

        if user.approval_status == "rejected":
            return Response(
                {"error": "Your registration request was rejected."},
                status=status.HTTP_403_FORBIDDEN
            )

        if user.approval_status != "approved":
            return Response(
                {"error": "Your account is not approved."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not user.is_active:
            return Response(
                {"error": "Your account is disabled."},
                status=status.HTTP_403_FORBIDDEN
            )

        if authenticated_user is None:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        login(request, authenticated_user)

        return Response(
            {"message": "Login successful."},
            status=status.HTTP_200_OK
        )

# class LoginView(APIView):
#     def post(self, request):
#         email = request.data.get("email")
#         password = request.data.get("password")

#         user = authenticate(request, email=email, password=password)

#         if user is None or user.approval_status != "approved":
#             return Response(
#                 data={"message": "Invalid email or password"},
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
#         login(request, user)
#         return Response(
#             data={"message": "Login successful"},
#             status=status.HTTP_200_OK
#         )

@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)

        return Response(
            data={"message": "Logout successful"},
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class MeView(APIView):
    permission_classes = [IsApprovedUser]

    def get(self, request):
        serializer = UserProfileSerializer(
            request.user,
            context={"request": request}
        )

        return Response(serializer.data)

    def patch(self, request):
        serializer = UpdateProfileSerializer(
            request.user,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        profile_serializer = UserProfileSerializer(
            request.user,
            context={"request": request}
        )

        return Response(profile_serializer.data)


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            data={
                "message": "Registration successful. Awaiting administrator approval.",
                "id": user.id
            },
            status=status.HTTP_201_CREATED
        )

class PendingRegistrationsView(APIView):
    permission_classes = [IsApprovedUser]

    def get(self, request):
        if request.user.is_superuser is False:
            return Response(
                data={
                    "message": "Administrator access required."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        pending_users = User.objects.filter(approval_status="pending")
        serializer = PendingRegistrationSerializer(pending_users, many=True)

        return Response(
            data=serializer.data,
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class ApproveRegistrationView(APIView):
    permission_classes = [IsApprovedUser]

    def post(self, request, user_id):
        if request.user.is_superuser is False:
            return Response(
                data={
                    "message": "Administrator access required."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = get_object_or_404(User, id=user_id)

        if user.approval_status != "pending":
            return Response(
                data={
                    "message": "Only pending registrations can be approved."
                },
                status=status.HTTP_409_CONFLICT
            )
        
        user.approval_status = "approved"
        user.is_active = True
        user.save(update_fields=["approval_status", "is_active"])

        return Response(
            data={
                "message": "Registration approved successfully."
            },
            status=status.HTTP_200_OK
        )


@method_decorator(csrf_protect, name="dispatch")
class RejectRegistrationView(APIView):
    permission_classes = [IsApprovedUser]

    def post(self, request, user_id):
        if request.user.is_superuser is False:
            return Response(
                data={
                    "message": "Administrator access required."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        user = get_object_or_404(User, id=user_id)

        if user.approval_status != "pending":
            return Response(
                data={
                    "message": "Only pending registrations can be rejected."
                },
                status=status.HTTP_409_CONFLICT
            )

        user.approval_status = "rejected"
        user.is_active = False
        user.save(update_fields=["approval_status", "is_active"])

        return Response(
            data={
                "message": "Registration rejected successfully.",
                "id": user.id
            },
            status=status.HTTP_200_OK
        )


class StaffProfileView(APIView):
    permission_classes = [IsApprovedUser]

    def get(self, request, user_id):
        user = get_object_or_404(
            User,
            id=user_id,
            is_active=True,
            approval_status="approved"
        )

        serializer = UserProfileSerializer(
            user,
            context={"request": request}
        )

        return Response(serializer.data)


@require_GET
def generate_token(request):
    csrf_token = get_token(request)

    return JsonResponse({"csrf_token": csrf_token})