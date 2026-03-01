from rest_framework import serializers
from .models import (
    DonationCategory,
    DonationCondition,
    DonationRequest,
    DonationImage,
    NGOOffer,
)


class UserDetailsSerializer(serializers.Serializer):
    """Serializer for displaying user details"""

    id = serializers.UUIDField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    phone_number = serializers.CharField(read_only=True)


class DonationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationCategory
        fields = ["id", "name", "description"]


class DonationConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationCondition
        fields = ["id", "name", "description"]


class DonationImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationImage
        fields = ["id", "image", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class DonationRequestSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    request_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    category_details = DonationCategorySerializer(source="category", read_only=True)
    condition_details = DonationConditionSerializer(source="condition", read_only=True)

    # Multiple images support
    images = DonationImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = DonationRequest
        fields = [
            "id",
            "user",
            "category",
            "category_details",
            "condition",
            "condition_details",
            "quantity",
            "notes",
            "pickup_address",
            "latitude",
            "longitude",
            "request_date",
            "status",
            "images",
            "uploaded_images",
        ]

    def create(self, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])
        request = DonationRequest.objects.create(**validated_data)
        # Create DonationImage instances for each uploaded image
        for image in uploaded_images:
            DonationImage.objects.create(donation=request, image=image)

        return request


class NGODonationRequestSerializer(serializers.ModelSerializer):
    """Serializer for NGO to view donation requests with user details"""

    user_details = UserDetailsSerializer(source="user", read_only=True)
    request_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    category_details = DonationCategorySerializer(source="category", read_only=True)
    condition_details = DonationConditionSerializer(source="condition", read_only=True)
    images = DonationImageSerializer(many=True, read_only=True)

    class Meta:
        model = DonationRequest
        fields = [
            "id",
            "user_details",
            "category",
            "category_details",
            "condition",
            "condition_details",
            "quantity",
            "notes",
            "pickup_address",
            "latitude",
            "longitude",
            "request_date",
            "status",
            "images",
        ]


class NGOOfferSerializer(serializers.ModelSerializer):
    """Serializer for NGO to create offers for donation requests"""

    ngo = serializers.PrimaryKeyRelatedField(read_only=True)
    offer_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = NGOOffer
        fields = [
            "id",
            "donation_request",
            "ngo",
            "offer_date",
            "pickup_date",
            "notes",
            "status",
        ]
        read_only_fields = ["id", "ngo", "offer_date", "status"]


class NGOAcceptedDonationRequestSerializer(serializers.ModelSerializer):
    """Serializer for NGO to view accepted donation requests with user and offer details"""

    user_details = UserDetailsSerializer(source="user", read_only=True)
    request_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    category_details = DonationCategorySerializer(source="category", read_only=True)
    condition_details = DonationConditionSerializer(source="condition", read_only=True)
    images = DonationImageSerializer(many=True, read_only=True)
    ngo_offers = NGOOfferSerializer(many=True, read_only=True)

    class Meta:
        model = DonationRequest
        fields = [
            "id",
            "user_details",
            "category",
            "category_details",
            "condition",
            "condition_details",
            "quantity",
            "notes",
            "pickup_address",
            "latitude",
            "longitude",
            "request_date",
            "status",
            "images",
            "ngo_offers",
        ]
