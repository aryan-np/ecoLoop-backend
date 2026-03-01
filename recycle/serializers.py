from rest_framework import serializers
from recycle.models import ScrapCategory, ScrapRequest, ScrapImage, ScrapOffer


class UserDetailsSerializer(serializers.Serializer):
    """Serializer for displaying user details"""

    id = serializers.UUIDField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    phone_number = serializers.CharField(read_only=True)


class ScrapCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapCategory
        fields = ["id", "material_type", "rate_per_kg", "description"]


class ScrapImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapImage
        fields = ["id", "image", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class ScrapRequestSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    request_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    category_details = ScrapCategorySerializer(source="category", read_only=True)

    # Multiple images support
    images = ScrapImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = ScrapRequest
        fields = [
            "id",
            "user",
            "category",
            "category_details",
            "weight_kg",
            "pickup_address",
            "latitude",
            "longitude",
            "preferred_time_slot",
            "condition",
            "request_date",
            "status",
            "images",
            "uploaded_images",
        ]

    def create(self, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])
        request = ScrapRequest.objects.create(**validated_data)

        # Create ScrapImage instances for each uploaded image
        for image in uploaded_images:
            ScrapImage.objects.create(scrap=request, image=image)

        return request


class RecyclerScrapRequestSerializer(serializers.ModelSerializer):
    """Serializer for Recycler to view scrap requests with user details"""

    user_details = UserDetailsSerializer(source="user", read_only=True)
    request_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    category_details = ScrapCategorySerializer(source="category", read_only=True)
    images = ScrapImageSerializer(many=True, read_only=True)

    class Meta:
        model = ScrapRequest
        fields = [
            "id",
            "user_details",
            "category",
            "category_details",
            "weight_kg",
            "pickup_address",
            "latitude",
            "longitude",
            "preferred_time_slot",
            "condition",
            "request_date",
            "status",
            "images",
        ]


class ScrapOfferSerializer(serializers.ModelSerializer):
    """Serializer for Recycler to create offers for scrap requests"""

    recycler = serializers.PrimaryKeyRelatedField(read_only=True)
    offer_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ScrapOffer
        fields = [
            "id",
            "scrap_request",
            "recycler",
            "offer_date",
            "offered_price",
            "pickup_date",
            "notes",
            "status",
        ]
        read_only_fields = ["id", "recycler", "offer_date", "status"]


class RecyclerAcceptedScrapRequestSerializer(serializers.ModelSerializer):
    """Serializer for Recycler to view accepted scrap requests with user and offer details"""

    user_details = UserDetailsSerializer(source="user", read_only=True)
    request_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    category_details = ScrapCategorySerializer(source="category", read_only=True)
    images = ScrapImageSerializer(many=True, read_only=True)
    recycler_offers = ScrapOfferSerializer(many=True, read_only=True)

    class Meta:
        model = ScrapRequest
        fields = [
            "id",
            "user_details",
            "category",
            "category_details",
            "weight_kg",
            "pickup_address",
            "latitude",
            "longitude",
            "preferred_time_slot",
            "condition",
            "request_date",
            "status",
            "images",
            "recycler_offers",
        ]
