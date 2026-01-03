from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from channels.db import database_sync_to_async
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@database_sync_to_async
def get_user(user_id):
    """
    Fetch a user by ID asynchronously.
    """
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware:
    """
    WebSocket middleware for authenticating users via JWT.
    """

    def __init__(self, app):
        """
        Initialize middleware with the next ASGI app.
        """
        self.app = app

    async def __call__(self, scope, receive, send):
        """
        ASGI entry point for the middleware.
        """
        try:
            scope["user"] = await self.get_user_from_scope(scope)
            return await self.app(scope, receive, send)
        except Exception:
            logger.exception("WS middleware fatal error")

    async def get_user_from_scope(self, scope):
        """
        Extract JWT from query string and authenticate the user.
        """
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token")

        if not token:
            return AnonymousUser()

        try:
            access = AccessToken(token[0])
            return await get_user(access["user_id"])
        except Exception:
            return AnonymousUser()



