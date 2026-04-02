import uuid
from django.db import models


class Payment(models.Model):
    STATUS_CHOICES = [
        ("Initiated", "Initiated"),
        ("Completed", "Completed"),
        ("Pending", "Pending"),
        ("Expired", "Expired"),
        ("User canceled", "User canceled"),
        ("Refunded", "Refunded"),
        ("Partially Refunded", "Partially Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="payments"
    )
    purchase_order_id = models.CharField(max_length=100, unique=True)
    purchase_order_name = models.CharField(max_length=255)
    amount = models.PositiveIntegerField(help_text="Amount in paisa")
    pidx = models.CharField(max_length=100, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Initiated"
    )
    thread = models.ForeignKey(
        "communications.Thread",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    payment_url = models.URLField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.purchase_order_name} - {self.status} ({self.user})"
