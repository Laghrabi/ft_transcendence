from django.urls import path

from .views import (
    DepartmentListCreateView,
    DepartmentDetailView,
    DepartmentMembershipListCreateView,
    DepartmentMembershipDetailView,
    RoleListCreateView,
    TransferDepartmentAdministratorView,
    DeactivateDepartmentView,
    ActivateDepartmentView,
    UpdateDepartmentTaskAcceptanceView,
)

urlpatterns = [
    path(
        "departments/",
        DepartmentListCreateView.as_view(),
        name="department-list-create"
    ),

    path(
        "departments/<int:department_id>/",
        DepartmentDetailView.as_view(),
        name="department-detail"
    ),

    path(
        "memberships/",
        DepartmentMembershipListCreateView.as_view(),
        name="membership-list-create"
    ),

    path(
        "memberships/<int:membership_id>/",
        DepartmentMembershipDetailView.as_view(),
        name="membership-detail"
    ),

    path(
        "roles/",
        RoleListCreateView.as_view(),
        name="role-list-create"
    ),

    path(
        "departments/<int:department_id>/transfer-administrator/",
        TransferDepartmentAdministratorView.as_view(),
        name="transfer-department-administrator"
    ),

    path(
        "departments/<int:department_id>/deactivate/",
        DeactivateDepartmentView.as_view(),
        name="department-deactivate"
    ),

    path(
        "departments/<int:department_id>/activate/",
        ActivateDepartmentView.as_view(),
        name="department-activate"
    ),

    path(
        "departments/<int:department_id>/task-acceptance/",
        UpdateDepartmentTaskAcceptanceView.as_view(),
        name="department-task-acceptance"
    ),
]
