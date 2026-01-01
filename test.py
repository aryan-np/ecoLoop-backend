import os
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecoLoop.settings")
django.setup()

# Import SMS function
from ecoLoop.sms import send_sms

# Test SMS
send_sms(
    "+9779843530143", "EcoLoop Test SMS: SMS service is working correctly. lastttt"
)

print("SMS sent successfully!")
