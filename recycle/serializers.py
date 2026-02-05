from rest_framework import serializers
from recycle.models import ScrapCategory, ScrapRequest


class ScrapCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapCategory
        fields = ["id", "material_type", "rate_per_kg", "description"]


class ScrapRequestSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    request_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    category_details = ScrapCategorySerializer(source="category", read_only=True)

    class Meta:
        model = ScrapRequest
        fields = [
            "id",
            "user",
            "category",
            "category_details",
            "weight_kg",
            "pickup_address",
            "preferred_time_slot",
            "condition",
            "request_date",
            "status",
        ]

    def create(self, validated_data):
        request = ScrapRequest.objects.create(**validated_data)
        return request
