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


def send_role_application_approved(email: str, full_name: str, role_type: str):
    """Send notification when role application is approved."""
    subject = f"Your {role_type} Application Has Been Approved!"
    message = f"""Hello {full_name},

Congratulations! Your application for the {role_type} role has been approved.

To access your new dashboard and features, please:
1. Logout from your current session
2. Sign in again

This will refresh your permissions and give you access to all {role_type} features.

Thank you for joining Eco Loop!

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)


def send_product_sold(email: str, full_name: str, product_title: str):
    subject = "Your product has been sold"
    message = f"""Hello {full_name},

Your product "{product_title}" has been marked as sold.

Thank you for using Eco Loop.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)


def send_donation_status_update(email: str, full_name: str, status: str):
    status_labels = {
        "accepted": "accepted",
        "pickup_started": "pickup started",
        "completed": "completed",
    }
    status_text = status_labels.get(status, status)
    subject = f"Your donation request is {status_text}"
    message = f"""Hello {full_name},

Your donation request is now {status_text}.

Thank you for supporting Eco Loop.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)


def send_scrap_status_update(email: str, full_name: str, status: str):
    status_labels = {
        "accepted": "accepted",
        "pickup_started": "pickup started",
        "completed": "completed",
    }
    status_text = status_labels.get(status, status)
    subject = f"Your scrap pickup is {status_text}"
    message = f"""Hello {full_name},

Your scrap request is now {status_text}.

Thank you for recycling with Eco Loop.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)


def send_report_reviewed(email: str, full_name: str, subject_line: str):
    subject = "Your report has been reviewed"
    message = f"""Hello {full_name},

Your report ("{subject_line}") has been reviewed by the admin team.

Thank you for helping keep Eco Loop safe.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)


def send_product_deleted_notice(email: str, full_name: str, product_title: str):
    subject = "Your product has been removed"
    message = f"""Hello {full_name},

Your product "{product_title}" has been removed by the admin team.

If you believe this is a mistake, please contact support.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)


def send_product_restored_notice(email: str, full_name: str, product_title: str):
    subject = "Your product has been restored"
    message = f"""Hello {full_name},

Your product "{product_title}" has been restored by the admin team.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)


def send_chat_cleared_notice(email: str, full_name: str, thread_id: str):
    subject = "A conversation was cleared by admin"
    message = f"""Hello {full_name},

A conversation (ID: {thread_id}) has been cleared by the admin team.

If you believe this is a mistake, please contact support.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)


def send_chat_restored_notice(email: str, full_name: str, thread_id: str):
    subject = "A conversation was restored by admin"
    message = f"""Hello {full_name},

A conversation (ID: {thread_id}) has been restored by the admin team.

Best regards,
Eco Loop Team"""

    send_email(email, subject, message)
