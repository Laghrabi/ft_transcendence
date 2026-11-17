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
from .models import User, Department, DepartmentMembership, Role
from django.shortcuts import get_object_or_404
from .permissions import IsApprovedUser, can_manage_department
from .serializers import StaffListSerializer, AdminStaffListSerializer, DepartmentSerializer, DepartmentCreateSerializer
from .serializers import DepartmentMembershipSerializer, RoleSerializer, TransferDepartmentAdministratorSerializer
from django.db import transaction
from audit.services import record_audit_event

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

            if user.requested_role.name == "Administrator":
                return Response(
                    data={
                        "message": (
                            "Administrator roles cannot be assigned "
                            "through registration approval."
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
    Allow superusers to deactivate approved staff accounts.

    Prevents self-deactivation and deactivation of users
    who are currently Department Administrators.

    Records successful deactivations in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, user_id):

        if not request.user.is_superuser:
            return Response(
                data={
                    "message": "Administrator access required."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.id == user_id:
            return Response(
                data={
                    "message": "You cannot deactivate your own account."
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
    Allow superusers to activate approved staff accounts.

    Prevents activating accounts that are already active.

    Records successful activations in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, user_id):

        if not request.user.is_superuser:
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

@method_decorator(csrf_protect, name="dispatch")
class DepartmentListCreateView(APIView):
    """
    List and create departments.

    Anyone can list departments.

    Superusers and approved department administrators
    can create departments and appoint their Administrator.
    """

    permission_classes = [IsApprovedUser]

    def get_permissions(self):

        if self.request.method == "GET":
            return [AllowAny()]

        return super().get_permissions()

    def get(self, request):

        departments = Department.objects.all().order_by("id")

        serializer = DepartmentSerializer(
            departments,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def post(self, request):

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

        serializer = DepartmentCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        administrator = serializer.validated_data["administrator"]

        with transaction.atomic():

            department = serializer.save()

            administrator_membership = DepartmentMembership.objects.get(
                user=administrator,
                department=department,
                role__name="Administrator"
            )

            record_audit_event(
                actor=request.user,
                action="department.created",
                target=department,
                metadata={
                    "administrator_id": administrator.id,
                    "administrator_membership_id": (
                        administrator_membership.id
                    ),
                    "is_active": department.is_active,
                    "accepts_new_tasks": department.accepts_new_tasks,
                }
            )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

@method_decorator(csrf_protect, name="dispatch")
class DepartmentDetailView(APIView):
    """
    Manage updates to existing departments.

    Only system superusers can update department information.

    Inactive departments cannot be modified.

    Successful changes are recorded in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def patch(self, request, department_id):
        """
        Update an active department's name or description.
        """

        if not request.user.is_superuser:
            return Response(
                data={
                    "message": "Administrator access required."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():

            department = get_object_or_404(
                Department.objects.select_for_update(),
                id=department_id
            )

            if not department.is_active:
                return Response(
                    data={
                        "message": "Cannot edit an inactive department."
                    },
                    status=status.HTTP_409_CONFLICT
                )

            serializer = DepartmentSerializer(
                department,
                data=request.data,
                partial=True
            )

            serializer.is_valid(raise_exception=True)

            changes = {}

            new_name = serializer.validated_data.get(
                "name",
                department.name
            )

            if new_name != department.name:
                changes["name"] = {
                    "old": department.name,
                    "new": new_name,
                }

            new_description = serializer.validated_data.get(
                "description",
                department.description
            )

            if new_description != department.description:
                changes["description"] = {
                    "old": department.description,
                    "new": new_description,
                }

            if changes:

                serializer.save()

                record_audit_event(
                    actor=request.user,
                    action="department.updated",
                    target=department,
                    metadata={
                        "changes": changes,
                    }
                )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class DepartmentMembershipListCreateView(APIView):
    """
    List and create department memberships.

    Approved users can view memberships.

    Superusers can create memberships, but each department
    can have only one Administrator.
    """

    permission_classes = [IsApprovedUser]

    def get(self, request):

        memberships = DepartmentMembership.objects.all().order_by("id")

        if not request.user.is_superuser:
            memberships = memberships.filter(
                user__is_active=True,
                user__approval_status="approved"
            )

        department_id = request.query_params.get("department_id")

        if department_id is not None:

            if not department_id.isdecimal() or int(department_id) < 1:
                return Response(
                    data={
                        "department_id": [
                            "A positive integer is required."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            memberships = memberships.filter(
                department_id=int(department_id)
            )

        serializer = DepartmentMembershipSerializer(
            memberships,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def post(self, request):

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

        serializer = DepartmentMembershipSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        department = serializer.validated_data["department"]
        role = serializer.validated_data["role"]

        with transaction.atomic():

            department = get_object_or_404(
                Department.objects.select_for_update(),
                id=department.id
            )

            if not department.is_active:
                return Response(
                    data={
                        "message": (
                            "Cannot modify memberships "
                            "of an inactive department."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            if not request.user.is_superuser:

                if not can_manage_department(
                    request.user,
                    department.id
                ):
                    return Response(
                        data={
                            "message": (
                                "You cannot add staff "
                                "to this department."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

            user = get_object_or_404(
                User.objects.select_for_update(),
                id=user.id
            )

            if not user.is_active or user.approval_status != "approved":
                return Response(
                    data={
                        "user": [
                            "Only active, approved staff can be "
                            "assigned to departments."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if DepartmentMembership.objects.filter(
                user=user,
                department=department
            ).exists():
                return Response(
                    data={
                        "message": (
                            "This user already belongs "
                            "to this department."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            if role.name == "Administrator":

                administrator_exists = DepartmentMembership.objects.filter(
                    department=department,
                    role__name="Administrator"
                ).exists()

                if administrator_exists:
                    return Response(
                        data={
                            "message": (
                                "This department already has "
                                "an Administrator."
                            )
                        },
                        status=status.HTTP_409_CONFLICT
                    )

            serializer.validated_data["user"] = user
            serializer.validated_data["department"] = department

            membership = serializer.save()

            record_audit_event(
                actor=request.user,
                action="department.membership.created",
                target=membership,
                metadata={
                    "user_id": membership.user_id,
                    "department_id": membership.department_id,
                    "role_id": membership.role_id,
                }
            )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

@method_decorator(csrf_protect, name="dispatch")
class DepartmentMembershipDetailView(APIView):
    """
    Manage department membership role updates and deletion.

    Superusers can change roles across all departments.

    Department administrators can change roles only within
    departments they manage.

    Each department must have exactly one Administrator.
    """

    permission_classes = [IsApprovedUser]

    def patch(self, request, membership_id):

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

        if (
            not isinstance(request.data, dict)
            or set(request.data.keys()) != {"role"}
        ):
            return Response(
                data={
                    "message": "Only the role field can be updated."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            membership = get_object_or_404(
                DepartmentMembership,
                id=membership_id
            )

            department = get_object_or_404(
                Department.objects.select_for_update(),
                id=membership.department_id
            )

            if not department.is_active:
                return Response(
                    data={
                        "message": (
                            "Cannot modify memberships "
                            "of an inactive department."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            membership = get_object_or_404(
                DepartmentMembership.objects.select_for_update(),
                id=membership_id,
                department=department
            )

            if not request.user.is_superuser:

                if not can_manage_department(
                    request.user,
                    membership.department_id
                ):
                    return Response(
                        data={
                            "message": (
                                "You cannot modify memberships "
                                "in this department."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

            serializer = DepartmentMembershipSerializer(
                membership,
                data=request.data,
                partial=True
            )

            serializer.is_valid(raise_exception=True)

            new_role = serializer.validated_data["role"]
            current_role = membership.role

            if (
                current_role.name == "Administrator"
                and new_role.name != "Administrator"
            ):

                another_administrator_exists = (
                    DepartmentMembership.objects.filter(
                        department=department,
                        role__name="Administrator"
                    ).exclude(
                        id=membership.id
                    ).exists()
                )

                if not another_administrator_exists:
                    return Response(
                        data={
                            "message": (
                                "Cannot remove the department's "
                                "only Administrator."
                            )
                        },
                        status=status.HTTP_409_CONFLICT
                    )

            if (
                current_role.name != "Administrator"
                and new_role.name == "Administrator"
            ):

                administrator_exists = (
                    DepartmentMembership.objects.filter(
                        department=department,
                        role__name="Administrator"
                    ).exists()
                )

                if administrator_exists:
                    return Response(
                        data={
                            "message": (
                                "This department already has "
                                "an Administrator."
                            )
                        },
                        status=status.HTTP_409_CONFLICT
                    )

            if current_role.id != new_role.id:

                serializer.save()

                record_audit_event(
                    actor=request.user,
                    action="department.membership.role_updated",
                    target=membership,
                    metadata={
                        "user_id": membership.user_id,
                        "department_id": membership.department_id,
                        "previous_role_id": current_role.id,
                        "previous_role_name": current_role.name,
                        "new_role_id": new_role.id,
                        "new_role_name": new_role.name,
                    }
                )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def delete(self, request, membership_id):

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

            membership = get_object_or_404(
                DepartmentMembership,
                id=membership_id
            )

            department = get_object_or_404(
                Department.objects.select_for_update(),
                id=membership.department_id
            )

            if not department.is_active:
                return Response(
                    data={
                        "message": (
                            "Cannot modify memberships "
                            "of an inactive department."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            membership = get_object_or_404(
                DepartmentMembership.objects.select_for_update(),
                id=membership_id,
                department=department
            )

            if not request.user.is_superuser:

                if not can_manage_department(
                    request.user,
                    membership.department_id
                ):
                    return Response(
                        data={
                            "message": (
                                "You cannot remove staff "
                                "from this department."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

            if membership.role.name == "Administrator":

                another_administrator_exists = (
                    DepartmentMembership.objects.filter(
                        department=department,
                        role__name="Administrator"
                    ).exclude(
                        id=membership.id
                    ).exists()
                )

                if not another_administrator_exists:
                    return Response(
                        data={
                            "message": (
                                "Cannot delete the department's "
                                "only Administrator."
                            )
                        },
                        status=status.HTTP_409_CONFLICT
                    )

            record_audit_event(
                actor=request.user,
                action="department.membership.deleted",
                target=membership,
                metadata={
                    "user_id": membership.user_id,
                    "department_id": membership.department_id,
                    "role_id": membership.role_id,
                    "role_name": membership.role.name,
                }
            )

            membership.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )

@method_decorator(csrf_protect, name="dispatch")
class RoleListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        roles = Role.objects.filter(
            name__in=["Nurse", "Doctor"]
        ).order_by("id")

        serializer = RoleSerializer(roles, many=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class TransferDepartmentAdministratorView(APIView):
    """
    Transfer department administration to another staff member.

    Only the superuser or the current Department Administrator
    can perform this operation.

    The previous Administrator's membership is deleted,
    but their user account is preserved.

    Successful transfers are recorded in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, department_id):

        with transaction.atomic():

            department = get_object_or_404(
                Department.objects.select_for_update(),
                id=department_id
            )

            if not department.is_active:
                return Response(
                    data={
                        "message": (
                            "Cannot transfer administration "
                            "of an inactive department."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            if not request.user.is_superuser:

                if not can_manage_department(
                    request.user,
                    department.id
                ):
                    return Response(
                        data={
                            "message": (
                                "You cannot transfer administration "
                                "of this department."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

            serializer = TransferDepartmentAdministratorSerializer(
                data=request.data
            )

            serializer.is_valid(raise_exception=True)

            new_administrator = serializer.validated_data[
                "new_administrator"
            ]

            new_administrator = get_object_or_404(
                User.objects.select_for_update(),
                id=new_administrator.id
            )

            if (
                not new_administrator.is_active
                or new_administrator.approval_status != "approved"
            ):
                return Response(
                    data={
                        "message": (
                            "The new Administrator must be "
                            "an active, approved user."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            administrator_role = Role.objects.get(
                name="Administrator"
            )

            current_administrators = (
                DepartmentMembership.objects.select_for_update().filter(
                    department=department,
                    role=administrator_role
                )
            )

            if current_administrators.count() != 1:
                return Response(
                    data={
                        "message": (
                            "This department must have exactly one "
                            "current Administrator before transferring."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            current_membership = current_administrators.first()

            if current_membership.user_id == new_administrator.id:
                return Response(
                    data={
                        "message": (
                            "The selected user is already "
                            "this department's Administrator."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            new_membership = (
                DepartmentMembership.objects.select_for_update().filter(
                    user=new_administrator,
                    department=department
                ).first()
            )

            previous_administrator_id = current_membership.user_id
            previous_membership_id = current_membership.id

            new_administrator_was_member = (
                new_membership is not None
            )

            current_membership.delete()

            if new_membership is None:

                new_membership = DepartmentMembership.objects.create(
                    user=new_administrator,
                    department=department,
                    role=administrator_role
                )

            else:

                new_membership.role = administrator_role

                new_membership.save(
                    update_fields=["role"]
                )

            record_audit_event(
                actor=request.user,
                action="department.administrator.transferred",
                target=department,
                metadata={
                    "previous_administrator_id": previous_administrator_id,
                    "new_administrator_id": new_administrator.id,
                    "previous_membership_id": previous_membership_id,
                    "new_membership_id": new_membership.id,
                    "new_administrator_was_member": (
                        new_administrator_was_member
                    ),
                }
            )

        return Response(
            data={
                "message": (
                    "Department administration transferred successfully."
                ),
                "department_id": department.id,
                "previous_administrator_id": previous_administrator_id,
                "new_administrator_id": new_administrator.id
            },
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class DeactivateDepartmentView(APIView):
    """
    Allow superusers to deactivate departments.

    Records successful department deactivations
    in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, department_id):

        if not request.user.is_superuser:
            return Response(
                data={
                    "message": "Superuser access required."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():

            department = get_object_or_404(
                Department.objects.select_for_update(),
                id=department_id
            )

            if not department.is_active:
                return Response(
                    data={
                        "message": "This department is already inactive."
                    },
                    status=status.HTTP_409_CONFLICT
                )

            department.is_active = False

            department.save(
                update_fields=["is_active"]
            )

            record_audit_event(
                actor=request.user,
                action="department.deactivated",
                target=department,
                metadata={
                    "previous_is_active": True,
                    "new_is_active": False,
                }
            )

        return Response(
            data={
                "message": "Department deactivated successfully."
            },
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class ActivateDepartmentView(APIView):
    """
    Allow superusers to reactivate departments.

    Records successful department reactivations
    in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, department_id):

        if not request.user.is_superuser:
            return Response(
                data={
                    "message": "Superuser access required."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():

            department = get_object_or_404(
                Department.objects.select_for_update(),
                id=department_id
            )

            if department.is_active:
                return Response(
                    data={
                        "message": "This department is already active."
                    },
                    status=status.HTTP_409_CONFLICT
                )

            department.is_active = True

            department.save(
                update_fields=["is_active"]
            )

            record_audit_event(
                actor=request.user,
                action="department.activated",
                target=department,
                metadata={
                    "previous_is_active": False,
                    "new_is_active": True,
                }
            )

        return Response(
            data={
                "message": "Department activated successfully."
            },
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_protect, name="dispatch")
class UpdateDepartmentTaskAcceptanceView(APIView):
    """
    Pause or resume new task assignments for a department.

    Superusers can manage any department.

    Department Administrators can manage only their own department.

    Inactive departments cannot accept new task assignments.

    Successful changes are recorded in the audit trail.
    """

    permission_classes = [IsApprovedUser]

    def patch(self, request, department_id):

        if (
            not isinstance(request.data, dict)
            or set(request.data.keys()) != {"accepts_new_tasks"}
        ):
            return Response(
                data={
                    "message": (
                        "Only the accepts_new_tasks field can be updated."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        accepts_new_tasks = request.data["accepts_new_tasks"]

        if not isinstance(accepts_new_tasks, bool):
            return Response(
                data={
                    "accepts_new_tasks": [
                        "A boolean value is required."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            department = get_object_or_404(
                Department.objects.select_for_update(),
                id=department_id
            )

            if not request.user.is_superuser:

                is_administrator = DepartmentMembership.objects.filter(
                    user=request.user,
                    department=department,
                    role__name="Administrator"
                ).exists()

                if not is_administrator:
                    return Response(
                        data={
                            "message": (
                                "You cannot manage task assignments "
                                "for this department."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )

            if not department.is_active:
                return Response(
                    data={
                        "message": (
                            "Cannot modify task assignment acceptance "
                            "of an inactive department."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            previous_accepts_new_tasks = department.accepts_new_tasks

            if previous_accepts_new_tasks != accepts_new_tasks:

                department.accepts_new_tasks = accepts_new_tasks

                department.save(
                    update_fields=["accepts_new_tasks"]
                )

                record_audit_event(
                    actor=request.user,
                    action="department.task_acceptance.updated",
                    target=department,
                    metadata={
                        "previous_accepts_new_tasks": (
                            previous_accepts_new_tasks
                        ),
                        "new_accepts_new_tasks": accepts_new_tasks,
                    }
                )

        serializer = DepartmentSerializer(department)

        return Response(
            data=serializer.data,
            status=status.HTTP_200_OK
        )

@require_GET
def generate_token(request):
    csrf_token = get_token(request)

    return JsonResponse({"csrf_token": csrf_token})