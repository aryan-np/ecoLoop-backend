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
