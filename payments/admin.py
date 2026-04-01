from django.contrib import admin
from payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["purchase_order_name", "user", "amount", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["purchase_order_id", "pidx", "transaction_id"]
    readonly_fields = ["id", "pidx", "transaction_id", "payment_url", "expires_at", "created_at", "updated_at"]
