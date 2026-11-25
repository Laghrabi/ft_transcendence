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
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import User
from organizations.models import Department, DepartmentMembership
from .permissions import IsApprovedUser, can_manage_department
from .serializers import (
    RegisterSerializer,
    PendingRegistrationSerializer,
    UserProfileSerializer,
    UpdateProfileSerializer,
    StaffListSerializer,
    AdminStaffListSerializer,
)
from audit.services import record_audit_event
from workflow.models import Task

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

        pending_users = User.objects.filter(
            approval_status="pending"
        )

        if not request.user.is_superuser:

            admin_departments = DepartmentMembership.objects.filter(
                user=request.user,
                role__name="Administrator",
                department__is_active=True
            ).values_list(
                "department_id",
                flat=True
            )

            if not admin_departments.exists():
                return Response(
                    data={
                        "message": "Administrator access required."
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            pending_users = pending_users.filter(
                requested_department_id__in=admin_departments
            )

        pending_users = pending_users.select_related(
            "requested_department",
            "requested_role"
        )

        serializer = PendingRegistrationSerializer(
            pending_users,
            many=True
        )

        return Response(
            data=serializer.data,
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class ApproveRegistrationView(APIView):
    """
    Approve pending registrations and create department memberships.

    Department Administrators can approve registrations only
    for departments they manage.

    Superusers can approve registrations across departments.

    Registrations cannot be approved for inactive departments.

    Successful approvals are recorded in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, user_id):

        if not request.user.is_superuser:

            is_department_admin = DepartmentMembership.objects.filter(
                user=request.user,
                role__name="Administrator",
                department__is_active=True
            ).exists()

            if not is_department_admin:
                return Response(
                    data={
                        "message": "Administrator access required."
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        with transaction.atomic():

            user = get_object_or_404(
                User.objects.select_for_update(),
                id=user_id
            )

            if not request.user.is_superuser:

                if not can_manage_department(
                    request.user,
                    user.requested_department_id
                ):
                    return Response(
                        data={
                            "message": (
                                "You cannot approve registrations "
                                "for this department."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

            if user.approval_status != "pending":
                return Response(
                    data={
                        "message": (
                            "Only pending registrations can be approved."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            if (
                user.requested_department_id is None
                or user.requested_role_id is None
            ):
                return Response(
                    data={
                        "message": (
                            "Registration must have a requested "
                            "department and role before approval."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            department = get_object_or_404(
                Department.objects.select_for_update(),
                id=user.requested_department_id
            )

            if not department.is_active:
                return Response(
                    data={
                        "message": (
                            "Cannot approve registration "
                            "for an inactive department."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            if user.requested_role.name not in ("Nurse", "Doctor"):
                return Response(
                    data={
                        "message": (
                            "Only Nurse or Doctor registrations "
                            "can be approved."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            if DepartmentMembership.objects.filter(user=user).exists():
                return Response(
                    data={
                        "message": (
                            "This user already has a department membership."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            previous_approval_status = user.approval_status
            previous_is_active = user.is_active

            membership = DepartmentMembership.objects.create(
                user=user,
                department=department,
                role_id=user.requested_role_id
            )

            user.approval_status = "approved"
            user.is_active = True

            user.save(
                update_fields=["approval_status", "is_active"]
            )

            record_audit_event(
                actor=request.user,
                action="registration.approved",
                target=user,
                metadata={
                    "previous_approval_status": previous_approval_status,
                    "new_approval_status": "approved",
                    "previous_is_active": previous_is_active,
                    "new_is_active": True,
                    "department_id": department.id,
                    "role_id": user.requested_role_id,
                    "membership_id": membership.id,
                }
            )

        return Response(
            data={
                "message": "Registration approved successfully."
            },
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class RejectRegistrationView(APIView):
    """
    Reject pending registration requests.

    Superusers can reject registrations across departments.

    Department Administrators can reject registrations only
    for active departments they manage.

    Successful rejections are recorded in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, user_id):

        if not request.user.is_superuser:

            is_administrator = DepartmentMembership.objects.filter(
                user=request.user,
                role__name="Administrator",
                department__is_active=True
            ).exists()

            if not is_administrator:
                return Response(
                    data={
                        "message": "Administrator access required."
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        with transaction.atomic():

            user = get_object_or_404(
                User.objects.select_for_update(),
                id=user_id
            )

            if not request.user.is_superuser:

                if not can_manage_department(
                    request.user,
                    user.requested_department_id
                ):
                    return Response(
                        data={
                            "message": (
                                "You cannot reject registrations "
                                "for this department."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

            if user.approval_status != "pending":
                return Response(
                    data={
                        "message": (
                            "Only pending registrations can be rejected."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            previous_approval_status = user.approval_status
            previous_is_active = user.is_active

            user.approval_status = "rejected"
            user.is_active = False

            user.save(
                update_fields=["approval_status", "is_active"]
            )

            record_audit_event(
                actor=request.user,
                action="registration.rejected",
                target=user,
                metadata={
                    "previous_approval_status": previous_approval_status,
                    "new_approval_status": "rejected",
                    "previous_is_active": previous_is_active,
                    "new_is_active": False,
                    "requested_department_id": user.requested_department_id,
                    "requested_role_id": user.requested_role_id,
                }
            )

        return Response(
            data={
                "message": "Registration rejected successfully.",
                "id": user.id
            },
            status=status.HTTP_200_OK
        )

class StaffProfileView(APIView):
    """
    Retrieve the profile of an active, approved staff member.

    Access is restricted to approved users. Phone number
    visibility is controlled by UserProfileSerializer.
    """
    
    permission_classes = [IsApprovedUser]

    def get(self, request, user_id):
        """Return the profile of the staff member with the given ID."""

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

class StaffListView(APIView):
    """
    List approved staff members based on the requesting user's privileges.

    Regular approved users can view only active, approved staff members.
    Administrators can view all approved staff members, including
    deactivated accounts, with additional account status information.
    """

    permission_classes = [IsApprovedUser]

    def get(self, request):
        """Return the appropriate staff list based on the user's privileges."""
        
        if request.user.is_superuser is False:
            users = User.objects.filter(is_active=True, approval_status="approved")
            serializer = StaffListSerializer(users, many=True)
        else:
            users = User.objects.filter(approval_status="approved")
            serializer = AdminStaffListSerializer(users, many=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class DeactivateStaffView(APIView):
    """
    Deactivate an approved staff account.

    Superusers can deactivate staff across all departments.

    Department Administrators can deactivate staff belonging
    to at least one active department they administer.

    Prevents self-deactivation and deactivation of users
    who currently hold a Department Administrator role.

    Successful deactivations are recorded in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, user_id):

        if request.user.id == user_id:
            return Response(
                data={
                    "message": "You cannot deactivate your own account."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        if not request.user.is_superuser:

            managed_departments = DepartmentMembership.objects.filter(
                user=request.user,
                role__name="Administrator",
                department__is_active=True
            ).values_list("department_id", flat=True)

            can_deactivate = DepartmentMembership.objects.filter(
                user_id=user_id,
                department_id__in=managed_departments
            ).exists()

            if not can_deactivate:
                return Response(
                    data={
                        "message": (
                            "You can only deactivate staff belonging "
                            "to a department you administer."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        with transaction.atomic():

            user = get_object_or_404(
                User.objects.select_for_update(),
                id=user_id,
                approval_status="approved"
            )

            if not user.is_active:
                return Response(
                    data={
                        "message": "This account is already deactivated."
                    },
                    status=status.HTTP_409_CONFLICT
                )

            is_department_administrator = (
                DepartmentMembership.objects.filter(
                    user=user,
                    role__name="Administrator"
                ).exists()
            )

            if is_department_administrator:
                return Response(
                    data={
                        "message": (
                            "Cannot deactivate a Department Administrator. "
                            "Transfer administration first."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            user.is_active = False

            user.save(
                update_fields=["is_active"]
            )

            record_audit_event(
                actor=request.user,
                action="staff.deactivated",
                target=user,
                metadata={
                    "previous_is_active": True,
                    "new_is_active": False,
                }
            )

        return Response(
            data={
                "message": "Staff account deactivated successfully."
            },
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class ActivateStaffView(APIView):
    """
    Reactivate an approved staff account.

    Superusers can reactivate staff across all departments.

    Any approved, active Department Administrator belonging
    to at least one active department can reactivate staff,
    regardless of the target staff member's department.

    Prevents activating accounts that are already active.

    Successful activations are recorded in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, user_id):

        if not request.user.is_superuser:

            is_administrator = DepartmentMembership.objects.filter(
                user=request.user,
                role__name="Administrator",
                department__is_active=True
            ).exists()

            if not is_administrator:
                return Response(
                    data={
                        "message": "Administrator access required."
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        with transaction.atomic():

            user = get_object_or_404(
                User.objects.select_for_update(),
                id=user_id,
                approval_status="approved"
            )

            if user.is_active:
                return Response(
                    data={
                        "message": "This account is already activated."
                    },
                    status=status.HTTP_409_CONFLICT
                )

            user.is_active = True

            user.save(
                update_fields=["is_active"]
            )

            record_audit_event(
                actor=request.user,
                action="staff.activated",
                target=user,
                metadata={
                    "previous_is_active": False,
                    "new_is_active": True,
                }
            )

        return Response(
            data={
                "message": "Staff account activated successfully."
            },
            status=status.HTTP_200_OK
        )

@require_GET
def generate_token(request):
    csrf_token = get_token(request)

    return JsonResponse({"csrf_token": csrf_token})