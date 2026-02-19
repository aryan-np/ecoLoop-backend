from django.contrib import admin
from . import models

# Register your models here.
admin.register(models.User)


class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "full_name", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "full_name")
    list_filter = ("is_active", "is_staff", "is_superuser")
    ordering = ("email",)


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "city", "area", "created_at")
    search_fields = ("user__email", "city", "area")
    list_filter = ("city", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")


admin.site.register(models.User, UserAdmin)

admin.site.register(models.UserProfile, UserProfileAdmin)
admin.site.register(models.PendingRegistration)
admin.site.register(models.Role)
admin.site.register(models.OTPVerification)


class RoleApplicationDocumentInline(admin.TabularInline):
    model = models.RoleApplicationDocument
    extra = 1
    fields = ("document", "uploaded_at")
    readonly_fields = ("uploaded_at",)


class RoleApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "role_type",
        "organization_name",
        "status",
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


admin.site.register(models.RoleApplication, RoleApplicationAdmin)
admin.site.register(models.RoleApplicationDocument)


class AdminActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
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


admin.site.register(models.AdminActivityLog, AdminActivityLogAdmin)
