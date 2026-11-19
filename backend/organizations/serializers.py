from django.db import transaction
from rest_framework import serializers

from accounts.models import (
    User,
    Department,
    DepartmentMembership,
    Role,
    RolePermission,
)
from accounts.permissions_catalog import ALLOWED_PERMISSIONS


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "accepts_new_tasks",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "accepts_new_tasks",
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
            "accepts_new_tasks",
            "administrator",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "accepts_new_tasks",
        ]

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
                User.objects.select_for_update()
                .filter(id=administrator.id)
                .first()
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
                role=administrator_role,
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
        required=True,
    )