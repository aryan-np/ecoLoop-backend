from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError
from rest_framework_simplejwt.authentication import JWTAuthentication


def get_user_from_authorization(authorization):
    if not authorization:
        raise CommandError(
            "The --authorization parameter is required. Pass a JWT access token or 'Bearer <token>'."
        )

    parts = authorization.strip().split()
    token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization.strip()

    jwt_auth = JWTAuthentication()
    try:
        validated_token = jwt_auth.get_validated_token(token)
        return jwt_auth.get_user(validated_token)
    except Exception as exc:
        raise CommandError(f"Invalid authorization token: {exc}") from exc


def get_seed_image_path():
    image_path = Path(settings.BASE_DIR) / "image.png"
    return image_path if image_path.exists() else None
