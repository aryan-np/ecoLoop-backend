from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def get_user_for_token(token: str):
    try:
        jwt_auth = JWTAuthentication()
        validated = jwt_auth.get_validated_token(token)
        return jwt_auth.get_user(validated)
    except Exception:
        return AnonymousUser()


class JwtAuthMiddleware:
    """
    Accept token from:
    - Authorization header: Bearer <token>
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        token = None

        auth = headers.get(b"authorization")
        if auth:
            try:
                parts = auth.decode().split()
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    token = parts[1]
            except Exception:
                token = None

        if not token:
            qs = parse_qs(scope.get("query_string", b"").decode())
            token = (qs.get("token") or [None])[0]

        scope["user"] = AnonymousUser()

        if token:
            try:
                scope["user"] = await get_user_for_token(token)
            except Exception:
                scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)
