from django.db import transaction
from rest_framework import serializers
from accounts.models import User
from .models import (
    Department,
    DepartmentMembership,
    Role,
    RolePermission,
)
from accounts.permissions_catalog import ALLOWED_PERMISSIONS



class PublicDepartmentSerializer(serializers.ModelSerializer):
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


class DepartmentSerializer(PublicDepartmentSerializer):
    administrator = serializers.SerializerMethodField()

    class Meta(PublicDepartmentSerializer.Meta):
        fields = PublicDepartmentSerializer.Meta.fields + [
            "created_at",
            "updated_at",
            "administrator",
        ]

        read_only_fields = (
            PublicDepartmentSerializer.Meta.read_only_fields + [
                "created_at",
                "updated_at",
                "administrator",
            ]
        )

    def get_administrator(self, obj):
        memberships = getattr(
            obj,
            "administrator_memberships",
            None,
        )

        if memberships is None:
            membership = DepartmentMembership.objects.filter(
                department=obj,
                role__name="Administrator",
            ).select_related("user").order_by("id").first()
        elif not memberships:
            return None
        else:
            membership = memberships[0]

        if membership is None:
            return None

        return {
            "id": membership.user_id,
            "name": membership.user.name,
            "avatar": membership.user.avatar,
        }

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

        if (
            not value.is_superuser
            and (
                value.requested_role_id is None
                or value.requested_role.name not in ("Nurse", "Doctor")
            )
        ):
            raise serializers.ValidationError(
                "A staff Administrator must be a registered Nurse or Doctor."
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

            if (
                not administrator.is_superuser
                and (
                    administrator.requested_role_id is None
                    or administrator.requested_role.name not in ("Nurse", "Doctor")
                )
            ):
                raise serializers.ValidationError({
                    "administrator": [
                        "A staff Administrator must be a registered Nurse or Doctor."
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
    Serialize department memberships with staff identity,
    registered profession, department role and account activity.

    Clinical roles are assigned automatically from the user's
    registered profession.
    """

    user_name = serializers.CharField(
        source="user.name",
        read_only=True,
    )

    user_avatar = serializers.CharField(
        source="user.avatar",
        read_only=True,
        allow_null=True,
    )

    profession = serializers.CharField(
        source="user.requested_role.name",
        read_only=True,
        allow_null=True,
    )

    role_name = serializers.CharField(
        source="role.name",
        read_only=True,
    )

    is_active = serializers.BooleanField(
        source="user.is_active",
        read_only=True,
    )

    class Meta:
        model = DepartmentMembership

        fields = [
            "id",
            "user",
            "department",
            "role",
            "user_name",
            "user_avatar",
            "profession",
            "role_name",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "role",
            "user_name",
            "user_avatar",
            "profession",
            "role_name",
            "is_active",
        ]

    def validate(self, attrs):

        if "role" in self.initial_data:
            raise serializers.ValidationError({
                "role": [
                    "The membership role is assigned automatically."
                ]
            })

        return attrs

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