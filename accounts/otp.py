import secrets
from django.contrib.auth.hashers import make_password, check_password


def generate_otp(length=6):
    # numeric OTP
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def hash_otp(otp: str) -> str:
    return make_password(otp)


def verify_otp(otp: str, otp_hash: str) -> bool:
    return check_password(otp, otp_hash)