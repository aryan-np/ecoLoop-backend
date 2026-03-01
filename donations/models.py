from django.db import models


# Create your models here.
class DonationCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class DonationCondition(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class DonationRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("completed", "Completed"),
        ("canceled", "Canceled"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    category = models.ForeignKey(
        DonationCategory, on_delete=models.PROTECT, related_name="donation_requests"
    )
    condition = models.ForeignKey(
        DonationCondition, on_delete=models.PROTECT, related_name="donation_requests"
    )
    quantity = models.CharField(max_length=100)
    notes = models.TextField()
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending")
    pickup_address = models.TextField()
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True
    )

    def __str__(self):
        return f"Donation Request by {self.user.username} for {self.category.name} in {self.condition.name} condition"


class DonationImage(models.Model):
    donation = models.ForeignKey(
        DonationRequest,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="donations/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for donation {self.donation.id} uploaded at {self.uploaded_at}"


class NGOOffer(models.Model):
    """NGO offer for a donation request"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
    ]

    donation_request = models.ForeignKey(
        DonationRequest, on_delete=models.CASCADE, related_name="ngo_offers"
    )
    ngo = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    offer_date = models.DateTimeField(auto_now_add=True)
    pickup_date = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending")

    def __str__(self):
        return f"NGO Offer by {self.ngo.full_name} for Donation Request {self.donation_request.id}"
