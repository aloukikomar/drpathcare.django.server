from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps  

# -----------------------------
# Custom User Manager
# -----------------------------
class UserManager(BaseUserManager):
    def create_user(self, email, mobile, role=None, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not mobile:
            raise ValueError("Mobile is required")

        email = self.normalize_email(email)
        user = self.model(email=email, mobile=mobile, role=role, **extra_fields)
        if password:
            user.set_password(password)  # Optional, can be None for OTP login
        user.save(using=self._db)
        return user

    def create_superuser(self, email, mobile, role=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, mobile, role, password, **extra_fields)


# -----------------------------
# Role Model
# -----------------------------
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.SET_NULL
    )

    def __str__(self):
        return self.name

# -----------------------------
# User Model
# -----------------------------
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=True, blank=True)
    mobile = models.CharField(max_length=15, unique=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="users",blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    first_name = models.CharField(max_length=50,blank=True, null=True)
    last_name = models.CharField(max_length=50,blank=True, null=True)
    gender = models.CharField(max_length=10,default='Male')
    date_of_birth = models.DateField(blank=True, null=True)
    age = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["mobile"]

    def __str__(self):
        role_name = self.role.name if self.role else "No Role"
        return f"{self.email} ({role_name})"
    

@receiver(post_save, sender=User)
def create_patient_for_user(sender, instance, created, **kwargs):
    if created:
        Patient = apps.get_model('users', 'Patient')  # app_label='patients', model_name='Patient'
        Patient.objects.create(
            user=instance,
            first_name=instance.first_name or "",
            last_name=instance.last_name or "",
            gender=instance.gender or "Male",
            date_of_birth=instance.date_of_birth or "2000-01-01",
            age=instance.age or 18,
        )