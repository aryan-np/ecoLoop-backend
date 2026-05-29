from django import forms
from django.contrib import admin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.db import transaction

from . import models


def _sync_user_organization_for_roles(user):
    """
    Keep organization data aligned with admin-managed roles.
    If NGO/RECYCLER role is removed, the linked organization and matching
    role applications are deleted.
    """
    current_roles = set(user.roles.values_list("name", flat=True))
    managed_roles = {"NGO", "RECYCLER"}

    models.RoleApplication.objects.filter(
        user=user,
        role_type__in=managed_roles - current_roles,
    ).delete()

    organization = getattr(user, "organization", None)
    if organization and organization.org_type not in current_roles:
        organization.delete()


class UserAdminForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text="Raw passwords are not stored, so there is no way to see this user's password here.",
    )

    class Meta:
        model = models.User
        fields = "__all__"

    def clean_roles(self):
        roles = self.cleaned_data.get("roles")

        if not roles:
            user_role, _ = models.Role.objects.get_or_create(
                name="USER",
                defaults={
                    "description": "Default platform user role",
                    "single_assignment": False,
                },
            )
            return [user_role]

        return roles


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    filter_horizontal = ("roles",)
    list_per_page = 25
    ordering = ("-date_joined",)

    list_display = (
        "email",
        "full_name",
        "display_roles",
        "display_organization",
        "is_active",
        "is_staff",
        "is_superuser",
        "is_email_verified",
        "date_joined",
    )
    search_fields = (
        "email",
        "full_name",
        "phone_number",
        "organization__name",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "is_email_verified",
        "is_phone_verified",
        "roles",
        "date_joined",
    )
    readonly_fields = ("id", "date_joined", "last_login", "password")

    fieldsets = (
        (
            "User Details",
            {
                "fields": (
                    "id",
                    "email",
                    "full_name",
                    "phone_number",
                    "password",
                )
            },
        ),
        (
            "Roles And Access",
            {
                "fields": (
                    "roles",
                    "is_active",
                    "is_staff",
                    "is_admin",
                    "is_superuser",
                )
            },
        ),
        (
            "Verification",
            {"fields": ("is_email_verified", "is_phone_verified")},
        ),
        (
            "Important Dates",
            {"fields": ("last_login", "date_joined")},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("roles")
            .select_related("organization")
        )

    @admin.display(description="Roles")
    def display_roles(self, obj):
        roles = sorted(obj.roles.values_list("name", flat=True))
        return ", ".join(roles) if roles else "-"

    @admin.display(description="Organization")
    def display_organization(self, obj):
        organization = getattr(obj, "organization", None)
        if not organization:
            return "-"
        return f"{organization.name} ({organization.org_type})"

    def save_related(self, request, form, formsets, change):
        with transaction.atomic():
            super().save_related(request, form, formsets, change)
            _sync_user_organization_for_roles(form.instance)


@admin.register(models.UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "area", "postal_code", "created_at")
    search_fields = ("user__email", "user__full_name", "city", "area")
    list_filter = ("city", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(models.PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "phone_number", "is_used", "created_at")
    search_fields = ("email", "full_name", "phone_number")
    list_filter = ("is_used", "created_at")
    readonly_fields = ("id", "created_at")


@admin.register(models.Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "single_assignment", "description")
    search_fields = ("name", "description")
    list_filter = ("single_assignment",)


@admin.register(models.OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "purpose", "is_used", "attempts", "expires_at")
    search_fields = ("email", "phone")
    list_filter = ("purpose", "is_used", "created_at")
    readonly_fields = ("id", "created_at")


class RoleApplicationDocumentInline(admin.TabularInline):
    model = models.RoleApplicationDocument
    extra = 1
    fields = ("document", "uploaded_at")
    readonly_fields = ("uploaded_at",)


@admin.register(models.RoleApplication)
class RoleApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role_type",
        "organization_name",
        "status",
        "reviewed_by",
        "created_at",
        "reviewed_at",
    )
    search_fields = ("user__email", "organization_name", "registration_number")
    list_filter = ("status", "role_type", "created_at", "reviewed_at")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "reviewed_at", "reviewed_by")
    inlines = [RoleApplicationDocumentInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "reviewed_by")


@admin.register(models.RoleApplicationDocument)
class RoleApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = ("application", "uploaded_at")
    search_fields = ("application__user__email",)
    readonly_fields = ("uploaded_at",)


@admin.register(models.AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "admin",
        "action",
        "target_type",
        "target_name",
        "result",
        "timestamp",
    )
    search_fields = ("admin__email", "admin__full_name", "target_name", "action")
    list_filter = ("action", "result", "target_type", "timestamp")
    ordering = ("-timestamp",)
    readonly_fields = ("id", "timestamp")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("admin")


@admin.register(models.Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "user", "is_verified", "created_at")
    search_fields = ("name", "user__email", "registration_number")
    list_filter = ("org_type", "is_verified", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "role_application")
