from django.contrib import admin

from .models import Product, Category, Condition, ProductImage


class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "owner",
        "category",
        "condition",
        "product_type",
        "status",
        "price",
        "is_active",
        "created_at",
    )
    search_fields = ("title", "owner__email", "category__name")
    list_filter = (
        "product_type",
        "status",
        "category",
        "condition",
        "is_active",
        "created_at",
    )
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        ("Basic Information", {"fields": ("id", "title", "description", "owner")}),
        (
            "Product Details",
            {
                "fields": (
                    "category",
                    "condition",
                    "product_type",
                    "status",
                    "price",
                    "location",
                )
            },
        ),
        ("Media", {"fields": ("image",)}),
        ("Status", {"fields": ("is_active",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active", "created_at")
    ordering = ("name",)
    readonly_fields = ("id", "created_at")


class ConditionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active", "created_at")
    ordering = ("name",)
    readonly_fields = ("id", "created_at")


admin.site.register(Product, ProductAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Condition, ConditionAdmin)

admin.site.register(ProductImage)
