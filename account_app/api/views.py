from account_app.api import serializers
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import generics, permissions, status
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from account_app.tasks import send_email_task
from django.db import transaction
import logging


logger = logging.getLogger(__name__)

class StudentRegisterView(generics.CreateAPIView):
    """
    Register a new student user.

    Creates a student account and sends a welcome email
    after the transaction is successfully committed.
    """
    serializer_class = serializers.StudentRegisterSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Student registration",
        request_body=serializers.StudentRegisterSerializer,
        responses={
            201: openapi.Response(
                description="Student registered successfully"
            ),
            400: "Validation error"
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        try:
            transaction.on_commit(
                lambda: send_email_task.apply_async(
                    args=[user.email, "EduShopX", user.username]
                )
            )
        except Exception as e:
            logger.error(f"Failed to enqueue welcome email for user {user.id}: {e}")

        return Response(
            {"message": "User registered successfully"},
            status=status.HTTP_201_CREATED
        )


class TeacherRegisterView(generics.CreateAPIView):
    """
    Register a new teacher user.

    Creates a teacher account and sends a welcome email
    asynchronously after successful commit.
    """
    serializer_class = serializers.TeacherRegisterSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Teacher registration",
        request_body=serializers.TeacherRegisterSerializer,
        responses={
            201: openapi.Response(
                description="Teacher registered successfully"
            ),
            400: "Validation error"
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        try:
            transaction.on_commit(
                lambda: send_email_task.apply_async(
                    args=[user.email, "Welcome", user.username]
                )
            )
        except Exception as e:
            logger.error(f"Failed to enqueue welcome email for user {user.id}: {e}")

        return Response(
            {"message": "User registered successfully"},
            status=status.HTTP_201_CREATED
        )


@swagger_auto_schema(
    method="post",
    operation_summary="Logout user",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["refresh"],
        properties={
            "refresh": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Refresh token"
            )
        },
    ),
    responses={
        200: "Logout successful",
        400: "Invalid token"
    },
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """
    Logout the authenticated user by blacklisting the refresh token.
    """
    try:
        refresh_token = request.data.get("refresh")
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(
            {"detail": "Logout successful"},
            status=status.HTTP_200_OK
        )
    except Exception as error:
        return Response(
            {"error": str(error)},
            status=status.HTTP_400_BAD_REQUEST
        )


class MyTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view.
    """
    serializer_class = serializers.MyTokenObtainPairSerializer

