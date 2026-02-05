from django.db import models


class ScrapCategory(models.Model):
    material_type = models.CharField(max_length=100, unique=True)
    rate_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Scrap Categories"

    def __str__(self):
        return f"{self.material_type}: {self.rate_per_kg} per kg"


class ScrapRequest(models.Model):
    CONDITION_CHOICES = [
        ("clean", "Clean"),
        ("mixed", "Mixed"),
    ]

    TIME_SLOT_CHOICES = [
        ("morning", "Morning"),
        ("afternoon", "Afternoon"),
        ("evening", "Evening"),
    ]

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    category = models.ForeignKey(
        ScrapCategory, on_delete=models.PROTECT, related_name="requests"
    )
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default="Pending")
    pickup_address = models.TextField()
    preferred_time_slot = models.CharField(max_length=20, choices=TIME_SLOT_CHOICES)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)

    def __str__(self):
        return f"Scrap Request by {self.user.username} for {self.category.material_type} ({self.weight_kg} kg)"
