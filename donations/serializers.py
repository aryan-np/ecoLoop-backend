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
            "request_date",
            "status",
        ]

    def create(self, validated_data):
        request = DonationRequest.objects.create(**validated_data)
        return request
