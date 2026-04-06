from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_reviews",
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_reviews",
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["reviewer", "reviewee"],
                name="unique_reviewer_reviewee",
            )
        ]

    def __str__(self):
        return f"{self.reviewer_id} -> {self.reviewee_id} ({self.rating})"
