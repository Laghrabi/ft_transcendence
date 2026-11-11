from rest_framework import serializers
from .models import User, Department, DepartmentMembership
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "email", "password"]
        extra_kwargs = {
            "password": {
                "write_only": True,
                "required": True,
            }
        }
    
    def create(self, validated_data):
        user = User.objects.create_user(
            **validated_data,
            is_active=False,
            approval_status="pending",
            is_staff=False,
            is_superuser=False,
        )
        return user
    
    def validate_password(self, value):
        user = User(
            name=self.initial_data.get("name", ""),
            email=self.initial_data.get("email", "")
        )

        try:
            validate_password(value, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        
        return value

class PendingRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "approval_status"]


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

class AdminStaffUpdateSerializer(serializers.ModelSerializer):
    """
    Serialize and validate staff information updates.

    Allows updating a staff member's name and email address.
    """
    
    class Meta:
        model = User
        fields = [
			"name",
			"email",
		]

class DepartmentSerializer(serializers.ModelSerializer):
    """
    Serialize and validate department information.

    Supports creating, retrieving, and updating departments.
    The department ID is read-only.
    """

    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "description",
        ]
        read_only_fields = ["id"]


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
