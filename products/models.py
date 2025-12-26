from django.db import models
from django.conf import settings


class Product(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
    )

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)

    category = models.CharField(max_length=100)
    condition = models.CharField(
        max_length=50,
        choices=[
            ("new", "New"),
            ("used", "Used"),
            ("damaged", "Damaged"),
        ],
    )

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_free = models.BooleanField(default=False)

    # image = models.ImageField(upload_to="products/", blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.owner.email}"
