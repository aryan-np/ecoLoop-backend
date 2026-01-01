from django.conf import settings
from twilio.rest import Client


def send_sms(phone_number: str, message: str):
    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN,
    )

    msg = client.messages.create(
        body=message,
        from_=settings.TWILIO_FROM_NUMBER,
        to=phone_number,
    )

    return msg.sid
