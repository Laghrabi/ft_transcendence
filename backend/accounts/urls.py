from django.urls import path
from .views import LoginView, generate_token

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("csrf/", generate_token, name="csrf"),
]

