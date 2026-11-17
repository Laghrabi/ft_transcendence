from rest_framework import serializers
from .models import User, Department, DepartmentMembership, Role
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import RolePermission
from .permissions_catalog import ALLOWED_PERMISSIONS
from django.db import transaction


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
    
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "avatar",
            "status",
            "is_active",
        ]
        read_only_fields = fields

class DepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department

        fields = [
            "id",
            "name",
            "description",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "is_active",
        ]

class DepartmentCreateSerializer(serializers.ModelSerializer):

    administrator = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True,
        required=True,
    )

    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "administrator",
        ]
        read_only_fields = ["id", "is_active",]

    def validate_administrator(self, value):

        if not value.is_active or value.approval_status != "approved":
            raise serializers.ValidationError(
                "The administrator must be an active, approved user."
            )

        return value

    def create(self, validated_data):

        administrator = validated_data.pop("administrator")

        with transaction.atomic():

            administrator = (
                User.objects.select_for_update().filter(
                    id=administrator.id
                ).first()
            )

            if (
                administrator is None
                or not administrator.is_active
                or administrator.approval_status != "approved"
            ):
                raise serializers.ValidationError({
                    "administrator": [
                        "The administrator must be an active, approved user."
                    ]
                })

            administrator_role = Role.objects.get(
                name="Administrator"
            )

            department = Department.objects.create(
                **validated_data
            )

            DepartmentMembership.objects.create(
                user=administrator,
                department=department,
                role=administrator_role
            )

        return department

class DepartmentMembershipSerializer(serializers.ModelSerializer):
    """
    Serialize and validate staff department memberships.

    Manages the relationship between users, departments, and roles.
    Supports creating and updating memberships, while keeping
    the membership ID read-only.
    """

    class Meta:
        model = DepartmentMembership
        fields = [
            "id",
            "user",
            "department",
            "role",
        ]
        read_only_fields = ["id"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
        ]
        read_only_fields = ["id"]


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = [
            "id",
            "role",
            "codename",
        ]
        read_only_fields = ["id"]

    def validate_codename(self, value):
        if value not in ALLOWED_PERMISSIONS:
            raise serializers.ValidationError(
                "Unsupported permission codename."
            )

        return value

class TransferDepartmentAdministratorSerializer(serializers.Serializer):

    new_administrator = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=True
    )
    