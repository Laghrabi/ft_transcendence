from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User
from organizations.models import (
    Department,
    Role,
    DepartmentMembership,
)
from organizations.serializers import (
    DepartmentSerializer,
    DepartmentCreateSerializer,
    DepartmentMembershipSerializer,
    RoleSerializer,
    RolePermissionSerializer,
    TransferDepartmentAdministratorSerializer,
)
from .permissions import can_be_department_admin


def _has_active_admin_role(user):
    """
    Check whether the staff member holds an Administrator
    role in at least one active department.
    """

    memberships = list(user.departmentmembership_set.all())
    index = 0

    while index < len(memberships):
        membership = memberships[index]

        if (
            membership.role.name == "Administrator"
            and membership.department.is_active
        ):
            return True

        index += 1

    return False

class RegisterSerializer(serializers.ModelSerializer):
    requested_department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        required=True,
        allow_null=False,
    )

    requested_role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        required=True,
        allow_null=False,
    )

    class Meta:
        model = User
        fields = [
            "name",
            "email",
            "password",
            "requested_department",
            "requested_role",
        ]

        extra_kwargs = {
            "password": {
                "write_only": True,
                "required": True,
            }
        }

    def create(self, validated_data):
        """
        Create an inactive user awaiting administrator approval.
        """

        user = User.objects.create_user(
            **validated_data,
            is_active=False,
            approval_status="pending",
            is_staff=False,
            is_superuser=False,
        )

        return user

    def validate_password(self, value):
        """
        Validate the password using Django's password validators.
        """

        user = User(
            name=self.initial_data.get("name", ""),
            email=self.initial_data.get("email", ""),
        )

        try:
            validate_password(value, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)

        return value

    def validate_requested_role(self, value):
        if value.name not in ("Nurse", "Doctor"):
            raise serializers.ValidationError(
                "This role is not available for public registration."
            )

        return value


class PendingRegistrationSerializer(serializers.ModelSerializer):
    requested_department_name = serializers.CharField(
        source="requested_department.name",
        read_only=True,
        allow_null=True
    )

    requested_role_name = serializers.CharField(
        source="requested_role.name",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "avatar",
            "date_joined",
            "approval_status",
            "requested_department",
            "requested_department_name",
            "requested_role",
            "requested_role_name",
        ]
        read_only_fields = fields

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "avatar",
            "status",
            "date_joined",
            "phone_number",
            "show_phone_number",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)

        request = self.context.get("request")
        viewer = request.user if request is not None else None

        is_owner = (
            viewer is not None
            and viewer.is_authenticated
            and viewer.pk == instance.pk
        )

        is_approved_staff = (
            viewer is not None
            and viewer.is_authenticated
            and viewer.is_active
            and viewer.approval_status == "approved"
        )

        if not is_owner:
            data.pop("show_phone_number", None)

        if not is_owner and not (
            is_approved_staff and instance.show_phone_number
        ):
            data.pop("phone_number", None)

        return data

class DepartmentMembershipSummarySerializer(
    serializers.ModelSerializer
):
    department_id = serializers.IntegerField(read_only=True)

    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )

    department_is_active = serializers.BooleanField(
        source="department.is_active",
        read_only=True,
    )

    role_id = serializers.IntegerField(read_only=True)

    role_name = serializers.CharField(
        source="role.name",
        read_only=True,
    )

    class Meta:
        model = DepartmentMembership
        fields = [
            "department_id",
            "department_name",
            "department_is_active",
            "role_id",
            "role_name",
        ]
        read_only_fields = fields

class StaffDetailsSerializer(UserProfileSerializer):
    profession = serializers.CharField(
        source="requested_role.name",
        read_only=True,
        allow_null=True,
    )

    is_department_admin = serializers.SerializerMethodField()

    department_memberships = DepartmentMembershipSummarySerializer(
        source="departmentmembership_set",
        many=True,
        read_only=True,
    )

    class Meta(UserProfileSerializer.Meta):
        fields = UserProfileSerializer.Meta.fields + [
            "is_active",
            "profession",
            "is_department_admin",
            "department_memberships",
        ]
        read_only_fields = fields

    def get_is_department_admin(self, obj):
        return _has_active_admin_role(obj)

class CurrentUserSerializer(StaffDetailsSerializer):
    class Meta(StaffDetailsSerializer.Meta):
        fields = StaffDetailsSerializer.Meta.fields + [
            "is_superuser",
        ]
        read_only_fields = fields

class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "name",
            "email",
            "avatar",
            "phone_number",
            "show_phone_number",
        ]

class StaffListSerializer(serializers.ModelSerializer):
    """
    Serialize basic information of staff members for the staff directory.

    Includes identification, contact, avatar, and status information.
    All fields are read-only.
    """
    
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "avatar",
            "status",
        ]
        read_only_fields = fields

class AdminStaffListSerializer(serializers.ModelSerializer):
    """
    Serialize staff information for the administrative Users directory.

    Include the staff member's registered profession, department
    administrator status, and available activation or deactivation
    actions based on the requesting administrator's permissions.
    
    All fields are read-only.
    """

    profession = serializers.CharField(
        source="requested_role.name",
        read_only=True,
        allow_null=True,
    )

    is_department_admin = serializers.SerializerMethodField()
    can_activate = serializers.SerializerMethodField()
    can_deactivate = serializers.SerializerMethodField()
    can_be_department_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "avatar",
            "status",
            "is_active",
            "profession",
            "is_department_admin",
            "can_activate",
            "can_deactivate",
            "can_be_department_admin",
        ]
        read_only_fields = fields

    def get_is_department_admin(self, obj):
        return _has_active_admin_role(obj)

    def get_can_be_department_admin(self, obj):
        return can_be_department_admin(obj)

    def get_can_activate(self, obj):
        return (
            self.context.get("admin_directory_access", False)
            and obj.approval_status == "approved"
            and not obj.is_active
        )

    def get_can_deactivate(self, obj):
        request = self.context.get("request")

        if (
            request is None
            or not self.context.get("admin_directory_access", False)
            or not obj.is_active
            or obj.approval_status != "approved"
            or request.user.pk == obj.pk
        ):
            return False

        managed_departments = self.context.get(
            "managed_department_ids",
            set()
        )

        allowed = request.user.is_superuser
        memberships = list(obj.departmentmembership_set.all())
        index = 0

        while index < len(memberships):
            membership = memberships[index]

            if membership.role.name == "Administrator":
                return False

            if membership.department_id in managed_departments:
                allowed = True

            index += 1

        return allowed
