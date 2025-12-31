from django.core.mail import send_mail
from django.conf import settings


def send_email(email: str, subject: str, message: str):

    send_mail(
        subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False
    )


def send_login_otp(email: str, otp: str):
    subject = "Your Login OTP"
    message = f"""Hello,

Your OTP for login is: {otp}

This OTP will expire in 5 minutes. Please do not share this code with anyone.

If you didn't request this, please ignore this email.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)


def send_registration_otp(email: str, otp: str):
    """Send OTP for user registration."""
    subject = "Verify Your Email Address"
    message = f"""Welcome!

Thank you for registering. Your verification OTP is: {otp}

This OTP will expire in 5 minutes. Please enter this code to complete your registration.

If you didn't create an account, please ignore this email.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)


def send_password_reset_otp(email: str, otp: str):
    """Send OTP for password reset."""
    subject = "Password Reset Request"
    message = f"""Hello,

We received a request to reset your password. Your OTP is: {otp}

This OTP will expire in 5 minutes. If you didn't request a password reset, please ignore this email.

Your password will remain unchanged until you create a new one using this OTP.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)
