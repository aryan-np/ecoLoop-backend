from django.contrib import admin
from .models import DonationCategory, DonationCondition, DonationRequest

# Register your models here.
admin.site.register(DonationCategory)
admin.site.register(DonationCondition)
admin.site.register(DonationRequest)
