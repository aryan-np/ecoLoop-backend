from rest_framework import serializers
from payments.models import Payment


class CustomerInfoSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False)


class InitiatePaymentSerializer(serializers.Serializer):
    amount = serializers.IntegerField(
        min_value=1000, help_text="Amount in paisa (min 1000 paisa = Rs. 10)"
    )
    purchase_order_name = serializers.CharField(max_length=255)
    return_url = serializers.URLField(
        help_text="Frontend URL Khalti redirects to after payment"
    )
    customer_info = CustomerInfoSerializer(required=False)
    thread_id = serializers.IntegerField(required=False, allow_null=True)


class VerifyPaymentSerializer(serializers.Serializer):
    pidx = serializers.CharField(max_length=100)


class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    amount_in_rupees = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "user_email",
            "purchase_order_id",
            "purchase_order_name",
            "amount",
            "amount_in_rupees",
            "pidx",
            "transaction_id",
            "status",
            "payment_url",
            "expires_at",
            "created_at",
            "updated_at",
        ]

    def get_amount_in_rupees(self, obj):
        return obj.amount / 100
