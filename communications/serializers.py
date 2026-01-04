from rest_framework import serializers
from communications.models import Thread, Message
from accounts.serializers import UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "thread", "sender", "content", "created_at", "is_read"]
        read_only_fields = ["id", "sender", "created_at"]

    def validate(self, data):
        request = self.context.get("request")
        thread = data.get("thread")

        print("Validating message data:", data)

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
    user1_email = serializers.EmailField(source="user1.email", read_only=True)
    user1_name = serializers.CharField(source="user1.full_name", read_only=True)
    user2_email = serializers.EmailField(source="user2.email", read_only=True)
    user2_name = serializers.CharField(source="user2.full_name", read_only=True)
    user2 = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), write_only=True
    )

    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Thread
        fields = [
            "id",
            "user1",
            "user1_email",
            "user1_name",
            "user2",
            "user2_email",
            "user2_name",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user1",
            "user1_email",
            "user1_name",
            "user2_email",
            "user2_name",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]

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

        # Sort UUIDs to handle both directions
        user_ids = sorted([str(request.user.id), str(user2.id)])
        thread, created = Thread.objects.get_or_create(
            user1_id=user_ids[0],
            user2_id=user_ids[1],
        )
        return thread

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
    user1_email = serializers.EmailField(source="user1.email", read_only=True)
    user1_name = serializers.CharField(source="user1.full_name", read_only=True)
    user2_email = serializers.EmailField(source="user2.email", read_only=True)
    user2_name = serializers.CharField(source="user2.full_name", read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Thread
        fields = [
            "id",
            "user1",
            "user1_email",
            "user1_name",
            "user2",
            "user2_email",
            "user2_name",
            "messages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
