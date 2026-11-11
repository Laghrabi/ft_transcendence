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
from .models import User, Department, DepartmentMembership
from django.shortcuts import get_object_or_404
from .permissions import IsApprovedUser
from .serializers import StaffListSerializer, AdminStaffUpdateSerializer, AdminStaffListSerializer, DepartmentSerializer
from django.db.models.deletion import ProtectedError
from .serializers import DepartmentMembershipSerializer

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
class AdminStaffUpdateView(APIView):
    """
    Allow administrators to update approved staff members' information.

    Access is restricted to authenticated, approved users with
    superuser privileges. Supports partial updates using PATCH.
    """

    permission_classes = [IsApprovedUser]

    def patch(self, request, user_id):
        """Validate and update the name or email of an approved staff member."""

        if request.user.is_superuser is False:
            return Response(
                data={
                    "message": "Administrator access required."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        user = get_object_or_404(User, id=user_id, approval_status="approved")
        serializer = AdminStaffUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

@method_decorator(csrf_protect, name="dispatch")
class DeactivateStaffView(APIView):
    """
    Allow administrators to deactivate approved staff accounts.

    Access is restricted to authenticated, approved users with
    superuser privileges. Prevents self-deactivation and returns
    an error if the target account is already inactive.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, user_id):
        """Deactivate an approved staff account by setting is_active to False."""

        if request.user.is_superuser is False:
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
        user = get_object_or_404(User, id=user_id, approval_status="approved")
        if user.is_active is False:
            return Response(
                data= {"message": "This account is already deactivated."},
                status=status.HTTP_409_CONFLICT
            )
        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response(
            data={"message": "Staff account deactivated successfully."}, status=status.HTTP_200_OK)

@method_decorator(csrf_protect, name="dispatch")
class ActivateStaffView(APIView):
    """
    Allow administrators to activate approved staff accounts.

    Access is restricted to authenticated, approved users with
    superuser privileges. Returns an error if the target account
    is already active.
    """

    permission_classes = [IsApprovedUser]

    def post(self, request, user_id):
        """Activate an approved staff account by setting is_active to True."""

        if request.user.is_superuser is False:
            return Response(
                data={
                        "message": "Administrator access required."
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        user = get_object_or_404(User, id=user_id, approval_status="approved")
        if user.is_active is True:
            return Response(
                data= {"message": "This account is already activated."},
                status=status.HTTP_409_CONFLICT
            )
        user.is_active = True
        user.save(update_fields=["is_active"])

        return Response(
            data={"message": "Staff account activated successfully."}, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name="dispatch")
class DepartmentListCreateView(APIView):
    """
    Manage department listing and creation.

    Approved users can retrieve all departments ordered by ID.
    Only administrators can create new departments.
    """

    permission_classes = [IsApprovedUser]

    def get(self, request):
        """Return a list of all departments ordered by ID."""

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
        """Validate and create a new department with administrator privileges."""

        if not request.user.is_superuser:
            return Response(
                data={"message": "Administrator access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

@method_decorator(csrf_protect, name="dispatch")
class DepartmentDetailView(APIView):
    """
    Manage updates and deletion of existing departments.

    Access is restricted to approved administrators.
    Supports partial updates and prevents deletion of departments
    that have assigned staff members.
    """

    permission_classes = [IsApprovedUser]

    def patch(self, request, department_id):
        """Validate and partially update a department by its ID."""

        if not request.user.is_superuser:
            return Response(
                data={"message": "Administrator access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        department = get_object_or_404(
            Department,
            id=department_id
        )

        serializer = DepartmentSerializer(
            department,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    
    def delete(self, request, department_id):
        """Delete a department unless existing staff memberships protect it."""

        if not request.user.is_superuser:
            return Response(
                data={"message": "Administrator access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        department = get_object_or_404(
            Department,
            id=department_id
        )

        try:
            department.delete()
        except ProtectedError:
            return Response(
                data={
                    "message": "Cannot delete a department with assigned staff members."
                },
                status=status.HTTP_409_CONFLICT
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name="dispatch")
class DepartmentMembershipListCreateView(APIView):
    """
    Manage department membership listing and creation.

    Approved users can view memberships, optionally filtered by
    department. Administrators can view all memberships, including
    those of inactive or unapproved users, and assign active,
    approved staff members to departments.
    """

    permission_classes = [IsApprovedUser]

    def get(self, request):
        """
        Return memberships ordered by ID with optional department filtering.

        Non-administrators can only view memberships belonging to
        active, approved staff members.
        """

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
                    data={"department_id": ["A positive integer is required."]},
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
        """
        Create a department membership with administrator privileges.

        Only active, approved staff members can be assigned
        to departments.
        """

        if not request.user.is_superuser:
            return Response(
                data={"message": "Administrator access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DepartmentMembershipSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        if not user.is_active or user.approval_status != "approved":
            return Response(
                data={
                    "user": [
                        "Only active, approved staff can be assigned to departments."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


@method_decorator(csrf_protect, name="dispatch")
class DepartmentMembershipDetailView(APIView):
    """
    Manage updates and deletion of department memberships.

    Access is restricted to approved administrators.
    Supports updating only the role assigned to a membership
    and removing staff members from departments.
    """

    permission_classes = [IsApprovedUser]

    def patch(self, request, membership_id):
        """Update only the role of an existing department membership."""

        if not request.user.is_superuser:
            return Response(
                data={"message": "Administrator access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        membership = get_object_or_404(
            DepartmentMembership,
            id=membership_id
        )

        if set(request.data.keys()) != {"role"}:
            return Response(
                data={"message": "Only the role field can be updated."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DepartmentMembershipSerializer(
            membership,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def delete(self, request, membership_id):
        """Remove an existing department membership by its ID."""
        
        if not request.user.is_superuser:
            return Response(
                data={"message": "Administrator access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        membership = get_object_or_404(
            DepartmentMembership,
            id=membership_id
        )

        membership.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )

@require_GET
def generate_token(request):
    csrf_token = get_token(request)

    return JsonResponse({"csrf_token": csrf_token})