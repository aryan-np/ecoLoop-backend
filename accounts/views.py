from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication

from loguru import logger

from ecoLoop.utils import api_response

from accounts.serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    LogoutSerializer,
    UserSerializer,
)
from .models import UserProfile
from .serializers import UserProfileSerializer
from .permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
)


# =========================================================
# Auth: Registration
# =========================================================
class UserRegistrationView(APIView):
    """
    API view for user registration.
    Accepts email, full_name, phone_number, password, confirm_password, and roles.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Register user",
        description="Create a new user account using email, full_name, phone_number, password, confirm_password, and optional roles.",
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(description="User registered successfully."),
            400: OpenApiResponse(description="Validation error."),
            500: OpenApiResponse(description="Server error."),
        },
        examples=[
            OpenApiExample(
                "Register example",
                value={
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "phone_number": "9800000000",
                    "password": "StrongPass@123",
                    "confirm_password": "StrongPass@123",
                    "roles": ["USER"],
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        try:
            if serializer.is_valid():
                user = serializer.save()
                return api_response(
                    is_success=True,
                    result={
                        "message": "User registered successfully.",
                        "user": UserSerializer(user).data,
                    },
                    status_code=status.HTTP_201_CREATED,
                )
            return api_response(
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.critical(f"Error during user registration: {str(e)}")
            return api_response(
                is_success=False,
                error_message=["Something went wrong. Please try again."],
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# =========================================================
# Auth: Login
# =========================================================
class UserLoginView(APIView):
    """
    API view for user login with JWT token generation.
    Accepts email and password, returns user data and JWT tokens.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Login user",
        description="Login using email and password. Returns user data and JWT access/refresh tokens.",
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful."),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Invalid credentials."),
            500: OpenApiResponse(description="Server error."),
        },
        examples=[
            OpenApiExample(
                "Login example",
                value={"email": "user@example.com", "password": "StrongPass@123"},
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data)

        try:
            if serializer.is_valid():
                user = serializer.user
                refresh_token = RefreshToken.for_user(user)
                access_token = str(refresh_token.access_token)

                return api_response(
                    is_success=True,
                    result={
                        "message": "User logged in successfully.",
                        "user_data": UserSerializer(user).data,
                        "tokens": {
                            "access": access_token,
                            "refresh": str(refresh_token),
                        },
                    },
                    status_code=status.HTTP_200_OK,
                )

            if "message" in serializer.errors and "Invalid credentials." in str(
                serializer.errors.get("message", "")
            ):
                return api_response(
                    is_success=False,
                    error_message=serializer.errors,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            return api_response(
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.critical(f"Error during user login: {str(e)}")
            return api_response(
                is_success=False,
                error_message=["Something went wrong. Please try again."],
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# =========================================================
# Auth: Logout (Blacklist refresh token)
# =========================================================
class UserLogoutView(APIView):
    """
    API view for user logout with JWT token blacklisting.
    Requires authentication and accepts refresh token to blacklist.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        tags=["Auth"],
        summary="Logout user",
        description="Blacklist the refresh token (requires authentication).",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description="Logout successful."),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
            500: OpenApiResponse(description="Server error."),
        },
        examples=[
            OpenApiExample(
                "Logout example",
                value={"refresh": "your_refresh_token_here"},
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = LogoutSerializer(data=request.data)
        try:
            if serializer.is_valid():
                serializer.save()
                return api_response(
                    is_success=True,
                    result={"message": "User logged out successfully."},
                    status_code=status.HTTP_200_OK,
                )
            return api_response(
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.critical(f"Error during user logout: {str(e)}")
            return api_response(
                is_success=False,
                error_message=["Something went wrong. Please try again."],
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# =========================================================
# Auth: Refresh access token
# =========================================================
class RefreshTokenView(APIView):
    """
    API view to refresh access token using refresh token.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Refresh access token",
        description="Generate a new access token using a valid refresh token.",
        request={
            "application/json": {
                "type": "object",
                "properties": {"refresh": {"type": "string"}},
                "required": ["refresh"],
            }
        },
        responses={
            200: OpenApiResponse(description="Token refreshed successfully."),
            400: OpenApiResponse(description="Missing refresh field."),
            401: OpenApiResponse(description="Invalid/expired refresh token."),
        },
        examples=[
            OpenApiExample(
                "Refresh example",
                value={"refresh": "your_refresh_token_here"},
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return api_response(
                is_success=False,
                error_message={"refresh": ["This field is required."]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)

            return api_response(
                is_success=True,
                result={
                    "message": "Token refreshed successfully.",
                    "access": access_token,
                },
                status_code=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error during token refresh: {str(e)}")
            return api_response(
                is_success=False,
                error_message=["Invalid or expired refresh token."],
                status_code=status.HTTP_401_UNAUTHORIZED,
            )


# =========================================================
# User Profile ViewSet (CRUD + Docs)
# =========================================================
@extend_schema(tags=["User Profile"])
class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.select_related("user").all()
    serializer_class = UserProfileSerializer
    # permission_classes = [IsOwnerOrReadOnly]
    # authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="List profiles",
        description="Normal users see only their own profile; admins can see all.",
        responses={200: UserProfileSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Get profile detail",
        responses={200: UserProfileSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create profile",
        description="Create a profile for the authenticated user (only if your system allows POST).",
        request=UserProfileSerializer,
        responses={
            201: UserProfileSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update profile (full)",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            403: OpenApiResponse(description="Not allowed (not owner)"),
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Update profile (partial)",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            403: OpenApiResponse(description="Not allowed (not owner)"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete profile",
        responses={
            204: OpenApiResponse(description="Deleted."),
            403: OpenApiResponse(description="Not allowed (not owner)"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        qs = UserProfile.objects.select_related("user")
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            return qs.all()
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
