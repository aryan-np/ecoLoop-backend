from rest_framework import serializers
from .models import DonationCategory, DonationCondition, DonationRequest, DonationImage


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
