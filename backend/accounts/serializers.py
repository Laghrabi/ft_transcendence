from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError



class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "email", "password"]
        extra_kwargs = {
            "password": {
                "write_only": True,
                "required": True,
            }
        }
    
    def create(self, validated_data):
        user = User.objects.create_user(
            **validated_data,
            is_active=False,
            approval_status="pending",
            is_staff=False,
            is_superuser=False,
        )
        return user
    
    def validate_password(self, value):
        user = User(
            name=self.initial_data.get("name", ""),
            email=self.initial_data.get("email", "")
        )

        try:
            validate_password(value, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        
        return value

class PendingRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "approval_status"]