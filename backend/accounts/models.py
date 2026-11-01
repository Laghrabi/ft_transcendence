from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    username = None
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    avatar = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=20, default="offline")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email