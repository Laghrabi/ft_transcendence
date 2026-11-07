from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import UserManager

class User(AbstractUser):
    APPROVAL_CHOICES = [
        ("approved", "Approved"),
        ("pending", "Pending"),
        ("rejected", "Rejected"),
    ]

    username = None

    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    avatar = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=20, default="offline")
    approval_status = models.CharField(max_length=10, choices=APPROVAL_CHOICES, default="pending")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self):
        return self.email