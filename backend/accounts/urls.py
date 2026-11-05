from django.urls import path
from .views import LoginView, generate_token, MeView, LogoutView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("csrf/", generate_token, name="csrf"),
    path("me/", MeView.as_view(), name="me"),
    path("logout/", LogoutView.as_view(), name="logout"),
]

