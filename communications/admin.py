from django.contrib import admin

from .models import Thread, Message


class ThreadAdmin(admin.ModelAdmin):
    list_display = ["id", "user1", "user2", "product", "created_at", "updated_at"]
    list_filter = ["created_at", "updated_at", "product"]
    search_fields = ["user1__email", "user2__email", "product__title"]
    readonly_fields = ["id", "created_at", "updated_at"]


admin.site.register(Thread, ThreadAdmin)
admin.site.register(Message)
