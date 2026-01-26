from rest_framework import serializers
from .models import Product, Category, Condition, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class ConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        fields = ["id", "name", "description"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product list - returns first image only"""

    category = CategorySerializer(read_only=True)
    condition = ConditionSerializer(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "category",
            "condition",
            "price",
            "image",
        ]

    def get_image(self, obj):
        """Return first image URL or None"""
        first_image = obj.images.first()
        if first_image and first_image.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None


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

    # Multiple images support
    images = ProductImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
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
            "images",
            "uploaded_images",
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

    def create(self, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])
        print("Uploaded images:", uploaded_images)
        product = Product.objects.create(**validated_data)

        # Create ProductImage instances for each uploaded image
        for image in uploaded_images:
            ProductImage.objects.create(product=product, image=image)

        return product

    def update(self, instance, validated_data):
        if instance.status != "available":
            raise serializers.ValidationError("Only available products can be updated.")

        uploaded_images = validated_data.pop("uploaded_images", [])

        # Update product fields
        instance = super().update(instance, validated_data)

        # Add new images if provided
        for image in uploaded_images:
            ProductImage.objects.create(product=instance, image=image)

        return instance
