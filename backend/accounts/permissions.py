from rest_framework.permissions import BasePermission
from .models import DepartmentMembership

class IsApprovedUser(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated is False:
            return False
        if request.user.is_active is False:
            return False
        if request.user.approval_status != "approved":
            return False

        return True

def can_manage_department(user, department_id):

    if not user or not user.is_authenticated:
        return False

    if not user.is_active:
        return False

    if user.approval_status != "approved":
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department_id=department_id,
        role__name="Administrator"
    ).exists()