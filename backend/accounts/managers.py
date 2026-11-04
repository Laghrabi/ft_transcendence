from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not isinstance(email, str) or not email.strip():
            raise ValueError("An email address is required")
        
        name = extra_fields.get("name")
        if not isinstance(name, str) or not name.strip():
             raise ValueError("A name is required")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
                raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)