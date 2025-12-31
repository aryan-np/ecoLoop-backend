import os
import django

# Set up Django settings BEFORE any Django imports
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "ecoLoop.settings"
)  # Replace 'ecoLoop.settings' with your actual settings module path
django.setup()

# Now you can import your email functions
from ecoLoop.mail import send_email, send_login_otp

# Test the email
send_email("nparyan7@gmail.com", "Test Subject", "This is a test message.")
print("Email sent successfully!")
