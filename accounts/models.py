from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    single_assignment = models.BooleanField(
        default=False,
        help_text="If True, only one user can hold this role (e.g., NGO, Admin).",
    )

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(
        self, email, full_name, phone_number, password=None, **extra_fields
    ):
        if not email:
            raise ValueError("The email field is required.")
        if not full_name:
            raise ValueError("The full name field is required.")
        if not phone_number:
            raise ValueError("The phone number field is required.")

        email = self.normalize_email(email)
        user = self.model(
            email=email, full_name=full_name, phone_number=phone_number, **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)

        # Assign default USER role
        default_role, _ = Role.objects.get_or_create(
            name="USER", single_assignment=False
        )
        user.roles.add(default_role)

        return user

    def create_superuser(
        self, email, full_name, phone_number, password=None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_admin", True)

        user = self.create_user(
            email=email,
            full_name=full_name,
            phone_number=phone_number,
            password=password,
            **extra_fields,
        )

        # Assign ADMIN role to superuser
        admin_role, _ = Role.objects.get_or_create(name="ADMIN", single_assignment=True)
        user.roles.add(admin_role)
        return user


class User(AbstractUser):
    username = None
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)

    roles = models.ManyToManyField(Role, related_name="users")

    # Verification & status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "phone_number"]

    objects = UserManager()

    def __str__(self):
        roles_list = ", ".join([r.name for r in self.roles.all()])
        return f"{self.email} ({roles_list})"

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def get_full_name(self):
        return self.full_name


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # Basic profile fields (you can extend later)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=80, blank=True, null=True)
    area = models.CharField(max_length=80, blank=True, null=True)  # e.g., locality
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    # Optional geo fields
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    bio = models.TextField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile: {self.user.email}"