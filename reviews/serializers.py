from rest_framework import serializers

from accounts.models import User
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    reviewee_id = serializers.PrimaryKeyRelatedField(
        source="reviewee",
        queryset=User.objects.all(),
        write_only=True,
        required=False,
    )
    reviewer_name = serializers.CharField(source="reviewer.full_name", read_only=True)
    reviewer_profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "reviewer",
            "reviewee",
            "reviewee_id",
            "rating",
            "comment",
            "created_at",
            "reviewer_name",
            "reviewer_profile_picture",
        ]
        read_only_fields = [
            "id",
            "reviewer",
            "reviewee",
            "created_at",
            "reviewer_name",
            "reviewer_profile_picture",
        ]

    def get_reviewer_profile_picture(self, obj):
        profile = getattr(obj.reviewer, "profile", None)
        if not profile or not profile.profile_picture:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(profile.profile_picture.url)
        return profile.profile_picture.url

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.method == "POST":
            reviewee = attrs.get("reviewee")
            if not reviewee:
                raise serializers.ValidationError(
                    {"reviewee_id": ["This field is required."]}
                )

            if request.user == reviewee:
                raise serializers.ValidationError(
                    {"reviewee_id": ["You cannot review yourself."]}
                )

            already_exists = Review.objects.filter(
                reviewer=request.user,
                reviewee=reviewee,
            ).exists()
            if already_exists:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "You have already reviewed this user. Use PATCH to edit it."
                        ]
                    }
                )

        return attrs
