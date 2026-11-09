from django.urls import path
from .views import LoginView, generate_token, MeView, LogoutView, RegisterView
from .views import PendingRegistrationsView, ApproveRegistrationView, RejectRegistrationView, StaffProfileView
from .views import StaffListView, AdminStaffUpdateView, DeactivateStaffView, ActivateStaffView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("csrf/", generate_token, name="csrf"),
    path("me/", MeView.as_view(), name="me"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path(
        "registrations/pending/",
        PendingRegistrationsView.as_view(),
        name="pending-registrations"
        ),
    path(
        "registrations/<int:user_id>/approve/",
        ApproveRegistrationView.as_view(), 
        name="approve-registration"
        ),
    path(
        "registrations/<int:user_id>/reject/",
        RejectRegistrationView.as_view(),
        name="reject-registration"
    ),
    path("users/<int:user_id>/", StaffProfileView.as_view(), name="staff-profile"),
    path("users/", StaffListView.as_view(), name="staff-list"),
    path("admin/users/<int:user_id>/", AdminStaffUpdateView.as_view(), name="admin-staff-update"),
    path("admin/users/<int:user_id>/deactivate/", DeactivateStaffView.as_view(), name="admin-staff-deactivate"),
    path("admin/users/<int:user_id>/activate/", ActivateStaffView.as_view(), name="admin-staff-activate"),
]
