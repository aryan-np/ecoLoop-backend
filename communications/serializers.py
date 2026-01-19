from rest_framework import serializers
from communications.models import Thread, Message
from accounts.serializers import UserSerializer
from products.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "thread",
            "sender",
            "content",
            "created_at",
            "is_read",
        ]
        read_only_fields = ["id", "sender", "created_at"]

    def validate(self, data):
        request = self.context.get("request")
        thread = data.get("thread")

        # Check if thread exists
        if not thread:
            raise serializers.ValidationError("thread is required")

        # Check if user is part of the thread
        if thread.user1 != request.user and thread.user2 != request.user:
            raise serializers.ValidationError(
                "Not allowed to send message in this thread"
            )

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["sender"] = request.user
        message = super().create(validated_data)
        # Update thread's updated_at
        message.thread.save()
        return message


class ThreadSerializer(serializers.ModelSerializer):
    user2 = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), write_only=True
    )
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), required=False, allow_null=True
    )

    # Self (current user in the thread)
    self_id = serializers.SerializerMethodField()
    self_email = serializers.SerializerMethodField()
    self_name = serializers.SerializerMethodField()
    self_profile_picture = serializers.SerializerMethodField()

    # Participant (other user in the thread)
    participant_id = serializers.SerializerMethodField()
    participant_email = serializers.SerializerMethodField()
    participant_name = serializers.SerializerMethodField()
    participant_profile_picture = serializers.SerializerMethodField()

    # Product details (read-only)
    product_id = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()

    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Thread
        fields = [
            "id",
            "user2",
            "product",
            "product_id",
            "product_name",
            "self_id",
            "self_email",
            "self_name",
            "self_profile_picture",
            "participant_id",
            "participant_email",
            "participant_name",
            "participant_profile_picture",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "self_id",
            "self_email",
            "self_name",
            "self_profile_picture",
            "user2",
            "product_id",
            "product_name",
            "participant_id",
            "participant_email",
            "participant_name",
            "participant_profile_picture",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        request = self.context.get("request")
        user2 = data.get("user2")

        if not user2:
            raise serializers.ValidationError("user2 is required")

        if user2.id == request.user.id:
            raise serializers.ValidationError("Cannot create thread with yourself")

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        user2 = validated_data.get("user2")
        product = validated_data.get("product")

        # Sort UUIDs to handle both directions - ensure no duplicates
        user_ids = sorted([str(request.user.id), str(user2.id)])
        thread, created = Thread.objects.get_or_create(
            user1_id=user_ids[0],
            user2_id=user_ids[1],
        )

        # Update product if provided
        if product:
            thread.product = product
            thread.save()

        return thread

    def get_self_user(self, obj):
        """Get the current user from context"""
        request = self.context.get("request")
        if request and request.user:
            if obj.user1_id == request.user.id:
                return obj.user1
            else:
                return obj.user2
        return None

    def get_participant_user(self, obj):
        """Get the other user in the thread"""
        request = self.context.get("request")
        if request and request.user:
            if obj.user1_id == request.user.id:
                return obj.user2
            else:
                return obj.user1
        return None

    def get_self_id(self, obj):
        user = self.get_self_user(obj)
        return str(user.id) if user else None

    def get_self_email(self, obj):
        user = self.get_self_user(obj)
        return user.email if user else None

    def get_self_name(self, obj):
        user = self.get_self_user(obj)
        return user.full_name if user else None

    def get_self_profile_picture(self, obj):
        user = self.get_self_user(obj)
        if user and hasattr(user, "profile") and user.profile.profile_picture:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(user.profile.profile_picture.url)
            return user.profile.profile_picture.url
        return None

    def get_participant_id(self, obj):
        user = self.get_participant_user(obj)
        return str(user.id) if user else None

    def get_participant_email(self, obj):
        user = self.get_participant_user(obj)
        return user.email if user else None

    def get_participant_name(self, obj):
        user = self.get_participant_user(obj)
        return user.full_name if user else None

    def get_participant_profile_picture(self, obj):
        user = self.get_participant_user(obj)
        if user and hasattr(user, "profile") and user.profile.profile_picture:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(user.profile.profile_picture.url)
            return user.profile.profile_picture.url
        return None

    def get_product_id(self, obj):
        if obj.product:
            return obj.product.id
        return None

    def get_product_name(self, obj):
        if obj.product:
            return obj.product.title
        return None

    def get_product_id(self, obj):
        if obj.product:
            return obj.product.id
        return None

    def get_product_name(self, obj):
        if obj.product:
            return obj.product.title
        return None

    def get_last_message(self, obj):
        last_msg = obj.messages.first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if request and request.user:
            return (
                obj.messages.filter(is_read=False).exclude(sender=request.user).count()
            )
        return 0


class ThreadDetailSerializer(serializers.ModelSerializer):
    # Self (current user in the thread)
    self_id = serializers.SerializerMethodField()
    self_email = serializers.SerializerMethodField()
    self_name = serializers.SerializerMethodField()
    self_profile_picture = serializers.SerializerMethodField()

    # Participant (other user in the thread)
    participant_id = serializers.SerializerMethodField()
    participant_email = serializers.SerializerMethodField()
    participant_name = serializers.SerializerMethodField()
    participant_profile_picture = serializers.SerializerMethodField()

    # Product details
    product_id = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()

    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Thread
        fields = [
            "id",
            "product_id",
            "product_name",
            "self_id",
            "self_email",
            "self_name",
            "self_profile_picture",
            "participant_id",
            "participant_email",
            "participant_name",
            "participant_profile_picture",
            "messages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_self_user(self, obj):
        """Get the current user from context"""
        request = self.context.get("request")
        if request and request.user:
            if obj.user1_id == request.user.id:
                return obj.user1
            else:
                return obj.user2
        return None

    def get_participant_user(self, obj):
        """Get the other user in the thread"""
        request = self.context.get("request")
        if request and request.user:
            if obj.user1_id == request.user.id:
                return obj.user2
            else:
                return obj.user1
        return None

    def get_self_name(self, obj):
        user = self.get_self_user(obj)
        return user.full_name if user else None

    def get_self_profile_picture(self, obj):
        user = self.get_self_user(obj)
        if user and hasattr(user, "profile") and user.profile.profile_picture:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(user.profile.profile_picture.url)
            return user.profile.profile_picture.url
        return None

    def get_participant_id(self, obj):
        user = self.get_participant_user(obj)
        return str(user.id) if user else None

    def get_participant_email(self, obj):
        user = self.get_participant_user(obj)
        return user.email if user else None

    def get_participant_name(self, obj):
        user = self.get_participant_user(obj)
        return user.full_name if user else None

    def get_participant_profile_picture(self, obj):
        user = self.get_participant_user(obj)
        if user and hasattr(user, "profile") and user.profile.profile_picture:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(user.profile.profile_picture.url)
            return user.profile.profile_picture.url
        return None
