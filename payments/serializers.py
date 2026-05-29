from rest_framework import serializers

from communications.models import Thread
from payments.models import Payment
from products.models import Product


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
    product_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        thread_id = attrs.get("thread_id")
        product_id = attrs.get("product_id")
        request = self.context.get("request")

        if not thread_id and not product_id:
            raise serializers.ValidationError(
                {"detail": "Either thread_id or product_id is required."}
            )

        thread = None
        product = None

        if thread_id:
            try:
                thread = Thread.objects.select_related("product", "user1", "user2").get(
                    id=thread_id
                )
            except Thread.DoesNotExist:
                raise serializers.ValidationError({"thread_id": "Thread not found."})

            if request and request.user not in [thread.user1, thread.user2]:
                raise serializers.ValidationError(
                    {"thread_id": "You are not a participant of this thread."}
                )

            product = thread.product

        if product_id:
            try:
                product = Product.objects.select_related("owner").get(id=product_id)
            except Product.DoesNotExist:
                raise serializers.ValidationError({"product_id": "Product not found."})

        if not product:
            raise serializers.ValidationError(
                {"product_id": "A valid product could not be resolved for this payment."}
            )

        if request and product.owner_id == request.user.id:
            raise serializers.ValidationError(
                {"product_id": "You cannot purchase your own product."}
            )

        if not product.is_active or product.status == "sold":
            raise serializers.ValidationError(
                {"product_id": "This product is no longer available for purchase."}
            )

        attrs["resolved_thread"] = thread
        attrs["resolved_product"] = product
        return attrs


class VerifyPaymentSerializer(serializers.Serializer):
    pidx = serializers.CharField(max_length=100)


class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    amount_in_rupees = serializers.SerializerMethodField()
    thread_id = serializers.IntegerField(source="thread.id", read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "user_email",
            "thread_id",
            "product_id",
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
