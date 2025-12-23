from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
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


class UserRegistrationView(APIView):
    """
    API view for user registration.
    Accepts email, full_name, phone_number, password, confirm_password, and roles.
    """

    permission_classes = [AllowAny]

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


class UserLoginView(APIView):
    """
    API view for user login with JWT token generation.
    Accepts email and password, returns user data and JWT tokens.
    """

    permission_classes = [AllowAny]

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

            # For invalid credentials, use 401 Unauthorized
            if "message" in serializer.errors and "Invalid credentials." in str(
                serializer.errors.get("message", "")
            ):
                return api_response(
                    is_success=False,
                    error_message=serializer.errors,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # For other validation errors, use 400 Bad Request
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
    """
    API view for user logout with JWT token blacklisting.
    Requires authentication and accepts refresh token to blacklist.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

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


# class UserProfileView(APIView):
#     """
#     API view to retrieve authenticated user's profile.
#     """
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [JWTAuthentication]

#     def get(self, request, *args, **kwargs):
#         try:
#             serializer = UserSerializer(request.user)
#             return api_response(
#                 is_success=True,
#                 result=serializer.data,
#                 status_code=status.HTTP_200_OK,
#             )
#         except Exception as e:
#             logger.critical(f"Error during user profile retrieval: {str(e)}")
#             return api_response(
#                 is_success=False,
#                 error_message=["Something went wrong. Please try again."],
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


class RefreshTokenView(APIView):
    """
    API view to refresh access token using refresh token.
    """

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
