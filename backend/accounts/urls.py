from django.urls import path
from .views import LoginView, generate_token, MeView, LogoutView, RegisterView
from .views import PendingRegistrationsView, ApproveRegistrationView, RejectRegistrationView

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
]
