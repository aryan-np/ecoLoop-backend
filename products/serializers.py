from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "owner_email",
            "owner_name",
            "title",
            "description",
            "category",
            "condition",
            "price",
            "is_free",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner_email",
            "owner_name",
            "created_at",
            "updated_at",
        ]
