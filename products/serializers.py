from rest_framework import serializers
from .models import Product, Category, Condition


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class ConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        fields = ["id", "name", "description"]


class ProductSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    owner_id = serializers.CharField(source="owner.id", read_only=True)

    is_owner = serializers.SerializerMethodField()

    # Display category and condition as nested objects
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        write_only=True,
        source="category",
    )

    condition = ConditionSerializer(read_only=True)
    condition_id = serializers.PrimaryKeyRelatedField(
        queryset=Condition.objects.filter(is_active=True),
        write_only=True,
        source="condition",
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "owner_email",
            "owner_name",
            "owner_id",
            "is_owner",
            "title",
            "image",
            "status",
            "description",
            "category",
            "category_id",
            "condition",
            "condition_id",
            "price",
            "product_type",
            "location",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner_id",
            "owner_email",
            "owner_name",
            "owner_address1",
            "owner_address2",
            "is_owner",
            "product_type",
            "created_at",
            "updated_at",
        ]

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.owner_id == request.user.id

    def update(self, instance, validated_data):
        if instance.status != "available":
            raise serializers.ValidationError("Only available products can be updated.")
        return super().update(instance, validated_data)
