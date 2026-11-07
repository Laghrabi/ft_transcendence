from rest_framework.permissions import BasePermission

class IsApprovedUser(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated is False:
            return False
        if request.user.is_active is False:
            return False
        if request.user.approval_status != "approved":
            return False

        return True
        