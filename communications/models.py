from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from products.models import Product

User = get_user_model()


class Thread(models.Model):

    user1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user1_threads"
    )
    user2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user2_threads"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="threads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user1", "user2")
        indexes = [
            models.Index(fields=["user1", "user2"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"Thread between {self.user1.email} and {self.user2.email}"


class Message(models.Model):

    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
            models.Index(fields=["is_read"]),
        ]

    def __str__(self):
        return f"Message from {self.sender.email} in thread {self.thread.id}"
