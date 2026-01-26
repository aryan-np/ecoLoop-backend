from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from loguru import logger

from ecoLoop.utils import api_response

from accounts.serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    LogoutSerializer,
    UserSerializer,
    OTPVerifySerializer,
)
from .models import UserProfile
from .serializers import UserProfileSerializer
from .permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
)


class UserRegistrationView(APIView):
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
                        "user": user,
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


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Login user",
        description="Login using PASSWORD or OTP method. OTP method sends OTP first; tokens are returned after OTP verify.",
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(description="OTP sent or login successful."),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Invalid credentials."),
            500: OpenApiResponse(description="Server error."),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data)

        try:
            if serializer.is_valid():
                result = serializer.save()  # <-- IMPORTANT
                return api_response(
                    is_success=True,
                    result=result,
                    status_code=status.HTTP_200_OK,
                )

            # invalid credentials handling (optional)
            if "message" in serializer.errors and "Invalid credentials." in str(
                serializer.errors.get("message", "")
            ):
                logger.warning(
                    f"Invalid login attempt for email: {request.data.get('email')}"
                )
                return api_response(
                    is_success=False,
                    error_message=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
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


class UserLogoutView(APIView):

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


class RefreshTokenView(APIView):
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


@extend_schema(tags=["User Profile"])
class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.select_related("user").all().order_by("-created_at")
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    authentication_classes = [JWTAuthentication]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_object(self):

        queryset = self.get_queryset()
        lookup_value = self.kwargs.get("pk")

        if not lookup_value:
            raise UserProfile.DoesNotExist("Profile not found")

        # For retrieve action, lookup by user_id
        if self.action == "retrieve":
            try:
                obj = queryset.get(user=lookup_value)
                self.check_object_permissions(self.request, obj)
                return obj
            except UserProfile.DoesNotExist as e:
                logger.error(f"UserProfile with user_id={lookup_value} does not exist")
                raise

        # For other actions (update, partial_update, destroy), lookup by profile id
        try:
            obj = queryset.get(id=lookup_value)
            self.check_object_permissions(self.request, obj)
            return obj
        except UserProfile.DoesNotExist as e:
            logger.error(f"UserProfile with id={lookup_value} does not exist")
            raise

    @extend_schema(
        summary="List profiles",
        description="Normal users see only their own profile; admins can see all profiles.",
        responses={
            200: UserProfileSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden."),
        },
        tags=["User Profile"],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Get profile detail by user ID",
        description="Retrieve a user profile by providing the user UUID. Requires authentication.",
        responses={
            200: UserProfileSerializer,
            401: OpenApiResponse(description="Unauthorized."),
            404: OpenApiResponse(description="Profile not found."),
        },
        tags=["User Profile"],
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = UserProfile.objects.get(user=kwargs.get("pk"))
            serializer = self.get_serializer(instance)
            return api_response(
                is_success=True,
                result=serializer.data,
                status_code=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return api_response(
                is_success=False,
                error_message=["User profile not found."],
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @extend_schema(
        summary="Create profile",
        description="Create a new user profile for the authenticated user. User profile is auto-created, but this endpoint allows manual creation if needed.",
        request=UserProfileSerializer,
        responses={
            201: UserProfileSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
        },
        tags=["User Profile"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_create(serializer)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Update profile (full)",
        description="Fully update a user profile by profile ID. All fields must be provided. Only the owner or admins can update.",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Not allowed (not owner)."),
            404: OpenApiResponse(description="Profile not found."),
        },
        tags=["User Profile"],
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_update(serializer)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Update profile (partial)",
        description="Partially update a user profile by profile ID. Only provided fields will be updated. Only the owner or admins can update.",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Not allowed (not owner)."),
            404: OpenApiResponse(description="Profile not found."),
        },
        tags=["User Profile"],
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_update(serializer)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Delete profile",
        description="Delete a user profile by profile ID. Only the owner or admins can delete. This will not delete the associated user account.",
        responses={
            204: OpenApiResponse(description="Profile deleted successfully."),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Not allowed (not owner)."),
            404: OpenApiResponse(description="Profile not found."),
        },
        tags=["User Profile"],
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return api_response(
            result={"message": "Deleted successfully."},
            is_success=True,
            status_code=status.HTTP_204_NO_CONTENT,
        )

    def get_queryset(self):
        user = self.request.user
        qs = UserProfile.objects.select_related("user").order_by("-created_at")
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            return qs.all()
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["OTP"],
        summary="Verify OTP",
        description="Verify OTP for REGISTER / LOGIN / RESET_PASSWORD. OTP must be unused, unexpired, and within attempt limit.",
        request=OTPVerifySerializer,
        responses={
            200: OpenApiResponse(description="OTP verified successfully."),
            400: OpenApiResponse(description="Invalid/expired OTP."),
            500: OpenApiResponse(description="Server error."),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = OTPVerifySerializer(data=request.data)
        try:
            if serializer.is_valid():
                result = serializer.save()
                return api_response(
                    is_success=True,
                    result=result,
                    status_code=status.HTTP_200_OK,
                )

            return api_response(
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.critical(f"Error during OTP verify: {str(e)}")
            return api_response(
                is_success=False,
                error_message=["Something went wrong. Please try again."],
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
