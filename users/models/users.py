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
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.SET_NULL,
    )
    permissions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of permission keys"
    )
    # ✅ NEW: access control flag
    view_all = models.BooleanField(
        default=False,
        help_text="If true, users with this role can view all records"
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
    # 🔑 NEW: User Code (Agent / Employee Code)
    user_code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="External / third-party user ID (agents only)"
    )
    # 🔑 Role
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        blank=True,
        null=True
    )

    # 🔑 NEW: Parent → Child hierarchy
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.SET_NULL,
        help_text="Manager / parent user"
    )

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
        role_name = self.role.name if self.role else "Customer"
        code = f"[{self.user_code}]" if self.user_code else ""
        return f"{self.full_name} {code} ({role_name})"

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    @property
    def get_assigned_users(self):
        """
        Returns:
        - None → unrestricted access (view_all roles)
        - List[int] → user IDs this user can see
        """

        # 🧑 Customer (role is null)
        if not self.role:
            return [self.id]

        # 🔓 View-all roles (Admin, Super Admin, etc.)
        if self.role.view_all:
            return None

        # 👥 Hierarchical users (self + children)
        ids = set()

        def collect(user):
            if user.id in ids:
                return
            ids.add(user.id)

            for child in user.children.filter(role__isnull=False):
                collect(child)

        collect(self)
        return list(ids)
    

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