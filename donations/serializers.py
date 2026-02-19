from rest_framework import serializers
from .models import DonationCategory, DonationCondition, DonationRequest


class DonationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationCategory
        fields = ["id", "name", "description"]


class DonationConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationCondition
        fields = ["id", "name", "description"]


class DonationRequestSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    request_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    category_details = DonationCategorySerializer(source="category", read_only=True)
    condition_details = DonationConditionSerializer(source="condition", read_only=True)

    # Map-related fields
    map_preview_url = serializers.SerializerMethodField()
    google_maps_url = serializers.SerializerMethodField()
    has_location = serializers.SerializerMethodField()

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
            "has_location",
            "map_preview_url",
            "google_maps_url",
            "request_date",
            "status",
        ]

    def get_has_location(self, obj):
        """Check if request has valid location coordinates"""
        return obj.latitude is not None and obj.longitude is not None

    def get_map_preview_url(self, obj):
        """Generate Google Maps Static API URL for map preview"""
        if obj.latitude and obj.longitude:
            base_url = "https://maps.googleapis.com/maps/api/staticmap"
            params = f"?center={obj.latitude},{obj.longitude}&zoom=15&size=600x300&markers=color:red%7C{obj.latitude},{obj.longitude}"
            return base_url + params
        return None

    def get_google_maps_url(self, obj):
        """Generate Google Maps URL for 'Open in Maps' functionality"""
        if obj.latitude and obj.longitude:
            return f"https://www.google.com/maps/dir/?api=1&destination={obj.latitude},{obj.longitude}"
        return None

    def create(self, validated_data):
        request = DonationRequest.objects.create(**validated_data)
        return request
