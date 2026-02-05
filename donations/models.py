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
    status = models.CharField(max_length=50, default="Pending")
    pickup_address = models.TextField()

    def __str__(self):
        return f"Donation Request by {self.user.username} for {self.category.name} in {self.condition.name} condition"