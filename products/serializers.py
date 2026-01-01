from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)

    owner_address1 = serializers.SerializerMethodField()
    owner_address2 = serializers.SerializerMethodField()

    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "owner_email",
            "owner_name",
            "owner_address1",
            "owner_address2",
            "is_owner",
            "title",
            "image",
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
            "owner_address1",
            "owner_address2",
            "is_owner",
            "created_at",
            "updated_at",
        ]

    def get_owner_address1(self, obj):
        profile = getattr(obj.owner, "profile", None)
        return getattr(profile, "address_line1", None)

    def get_owner_address2(self, obj):
        profile = getattr(obj.owner, "profile", None)
        return getattr(profile, "address_line2", None)

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.owner_id == request.user.id
