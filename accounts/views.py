from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from django.db.models import Exists, OuterRef, Q, Case, When, Value, BooleanField

from loguru import logger

from ecoLoop.utils import api_response

from accounts.serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    LogoutSerializer,
    UserSerializer,
    OTPVerifySerializer,
    RoleApplicationSerializer,
    RoleApplicationReviewSerializer,
    ReportSerializer,
    ReportAdminSerializer,
    ReportReviewSerializer,
)
from .models import UserProfile, User, RoleApplication, Report
from .serializers import UserProfileSerializer
from .permissions import IsOwnerOrReadOnly, IsSuperUser, IsOwnerOrAdmin

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
    authentication_classes = []

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
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    authentication_classes = [JWTAuthentication]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

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

    def get_queryset(self):
        user = self.request.user

        # Subquery to check if user has pending NGO application
        has_pending_ngo = RoleApplication.objects.filter(
            user=OuterRef("user"), role_type="NGO", status="pending"
        )

        # Subquery to check if user has pending RECYCLER application
        has_pending_recycler = RoleApplication.objects.filter(
            user=OuterRef("user"), role_type="RECYCLER", status="pending"
        )

        # Subquery to check if user has any NGO application (any status)
        has_applied_ngo = RoleApplication.objects.filter(
            user=OuterRef("user"), role_type="NGO"
        )

        # Subquery to check if user has any RECYCLER application (any status)
        has_applied_recycler = RoleApplication.objects.filter(
            user=OuterRef("user"), role_type="RECYCLER"
        )

        # Subquery to check if user has approved RECYCLER role
        has_recycler_role = User.objects.filter(
            id=OuterRef("user"), roles__name="RECYCLER"
        )

        # Subquery to check if user has approved NGO role
        has_ngo_role = User.objects.filter(id=OuterRef("user"), roles__name="NGO")

        qs = (
            UserProfile.objects.select_related("user")
            .filter(user=user)
            .annotate(
                can_apply_ngo=Case(
                    # Can't apply for NGO if: any pending application OR already has RECYCLER role OR already has NGO role
                    When(
                        Q(Exists(has_pending_ngo))
                        | Q(Exists(has_pending_recycler))
                        | Q(Exists(has_recycler_role))
                        | Q(Exists(has_ngo_role)),
                        then=Value(False),
                    ),
                    default=Value(True),
                    output_field=BooleanField(),
                ),
                can_apply_recycler=Case(
                    # Can't apply for RECYCLER if: any pending application OR already has NGO role OR already has RECYCLER role
                    When(
                        Q(Exists(has_pending_ngo))
                        | Q(Exists(has_pending_recycler))
                        | Q(Exists(has_ngo_role))
                        | Q(Exists(has_recycler_role)),
                        then=Value(False),
                    ),
                    default=Value(True),
                    output_field=BooleanField(),
                ),
                has_applied_ngo=Case(
                    When(Exists(has_applied_ngo), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                has_applied_recycler=Case(
                    When(Exists(has_applied_recycler), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
            .order_by("-created_at")
        )

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


@extend_schema(tags=["Admin - User Management"])
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users. Only accessible to superusers.
    Provides full CRUD operations on user accounts.
    """

    serializer_class = UserSerializer
    permission_classes = [IsSuperUser]
    authentication_classes = [JWTAuthentication]
    queryset = User.objects.all().order_by("-date_joined")
    lookup_field = "id"

    @extend_schema(
        summary="List all users",
        description="Retrieve a list of all users with pagination and counts. Only accessible to superusers.",
        responses={
            200: UserSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
        },
    )
    def list(self, request, *args, **kwargs):
        from products.models import Product
        from donations.models import DonationRequest
        from recycle.models import ScrapRequest

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data

            # Add counts to each user
            for user_data in data:
                user_id = user_data["id"]
                user_data["listing"] = {
                    "products_count": Product.objects.filter(owner_id=user_id).count(),
                    "donations_count": DonationRequest.objects.filter(
                        user_id=user_id
                    ).count(),
                    "recycles_count": ScrapRequest.objects.filter(
                        user_id=user_id
                    ).count(),
                }

            result = {
                "count": getattr(self.paginator.page.paginator, "count", len(data)),
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "results": data,
            }
            return api_response(
                result=result,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        data = self.get_serializer(queryset, many=True).data

        # Add counts to each user
        for user_data in data:
            user_id = user_data["id"]
            user_data["listing"] = {
                "products_count": Product.objects.filter(owner_id=user_id).count(),
                "donations_count": DonationRequest.objects.filter(
                    user_id=user_id
                ).count(),
                "recycles_count": ScrapRequest.objects.filter(user_id=user_id).count(),
            }

        return api_response(
            result=data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Get user details with counts",
        description="Retrieve details of a specific user by ID including counts of products, donations, and recycle requests. Only accessible to superusers.",
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
            404: OpenApiResponse(description="User not found."),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        from products.models import Product
        from donations.models import DonationRequest
        from recycle.models import ScrapRequest

        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Get counts
        user_data = serializer.data
        user_data["products_count"] = Product.objects.filter(owner=instance).count()
        user_data["donations_count"] = DonationRequest.objects.filter(
            user=instance
        ).count()
        user_data["recycles_count"] = ScrapRequest.objects.filter(user=instance).count()

        return api_response(
            result=user_data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Create a new user",
        description="Create a new user account. Only accessible to superusers.",
        request=UserSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
        },
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
        summary="Update user (full)",
        description="Fully update a user account. Only accessible to superusers.",
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
            404: OpenApiResponse(description="User not found."),
        },
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
        summary="Update user (partial)",
        description="Partially update a user account. Only accessible to superusers.",
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
            404: OpenApiResponse(description="User not found."),
        },
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
        summary="Delete user",
        description="Delete a user account. Only accessible to superusers.",
        responses={
            204: OpenApiResponse(description="User deleted successfully."),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
            404: OpenApiResponse(description="User not found."),
        },
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)

        return api_response(
            result={"message": "User deleted successfully."},
            is_success=True,
            status_code=status.HTTP_204_NO_CONTENT,
        )


@extend_schema(tags=["Role Applications"])
class RoleApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for users to submit and view role applications (Recycler/NGO).
    Users can create and view their own applications.
    """

    serializer_class = RoleApplicationSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        return RoleApplication.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    @extend_schema(
        summary="List my role applications",
        description="Get all role applications submitted by the authenticated user.",
        responses={
            200: RoleApplicationSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized."),
        },
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
        summary="Submit a role application",
        description="Submit an application to become a Recycler or NGO.",
        request=RoleApplicationSerializer,
        responses={
            201: RoleApplicationSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
        },
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

        serializer.save()

        return api_response(
            result={"message": "Role application submitted successfully."},
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Admin - Role Applications"])
class AdminRoleApplicationViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = RoleApplicationSerializer
    permission_classes = [IsSuperUser]
    authentication_classes = [JWTAuthentication]
    queryset = (
        RoleApplication.objects.all()
        .order_by("-created_at")
        .select_related("user", "reviewed_by")
    )

    @extend_schema(
        summary="List all role applications",
        description="Get all role applications with pagination. Filter by status using ?status=pending",
        responses={
            200: RoleApplicationSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
        },
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Filter by status if provided
        status_filter = request.query_params.get("status", None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by role_type if provided
        role_type_filter = request.query_params.get("role_type", None)
        if role_type_filter:
            queryset = queryset.filter(role_type=role_type_filter)

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data
            result = {
                "count": getattr(self.paginator.page.paginator, "count", len(data)),
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "results": data,
            }
            return api_response(
                result=result,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        data = self.get_serializer(queryset, many=True).data
        return api_response(
            result=data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Get role application details",
        description="Retrieve details of a specific role application.",
        responses={
            200: RoleApplicationSerializer,
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
            404: OpenApiResponse(description="Application not found."),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Review role application (Approve/Reject)",
        description="Approve or reject a role application. Approving will assign the role to the user.",
        request=RoleApplicationReviewSerializer,
        responses={
            200: RoleApplicationSerializer,
            400: OpenApiResponse(
                description="Validation error or application already reviewed."
            ),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
            404: OpenApiResponse(description="Application not found."),
        },
    )
    @action(
        detail=True, methods=["patch"], serializer_class=RoleApplicationReviewSerializer
    )
    def review(self, request, pk=None):
        """Review (approve/reject) a role application"""
        instance = self.get_object()
        serializer = RoleApplicationReviewSerializer(
            instance, data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return api_response(
                result=None,
                is_success=False,
                error_message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated_application = serializer.save()
            result_serializer = RoleApplicationSerializer(updated_application)
            return api_response(
                result=result_serializer.data,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )
        except serializers.ValidationError as e:
            return api_response(
                result=None,
                is_success=False,
                error_message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=["Reports"])
class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for users to create and view their own reports.
    Users can create reports and view their submitted reports.
    """

    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        """Users can only see their own reports"""
        return Report.objects.filter(user=self.request.user, is_active=True).order_by(
            "-created_at"
        )

    @extend_schema(
        summary="List my reports",
        description="Get all reports submitted by the authenticated user.",
        responses={
            200: ReportSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized."),
        },
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
        summary="Get report details",
        description="Retrieve details of a specific report.",
        responses={
            200: ReportSerializer,
            401: OpenApiResponse(description="Unauthorized."),
            404: OpenApiResponse(description="Report not found."),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Create a report",
        description="Submit a new report to the admin.",
        request=ReportSerializer,
        responses={
            201: ReportSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
        },
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

        serializer.save()

        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Delete report",
        description="Delete a pending report.",
        responses={
            200: OpenApiResponse(description="Report deleted successfully."),
            400: OpenApiResponse(description="Cannot delete non-pending report."),
            401: OpenApiResponse(description="Unauthorized."),
            404: OpenApiResponse(description="Report not found."),
        },
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.status != "pending":
            return api_response(
                result=None,
                is_success=False,
                error_message={"detail": "Only pending reports can be deleted."},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        instance.is_active = False  # Soft delete
        instance.save()

        return api_response(
            result={"message": "Report deleted successfully."},
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


@extend_schema(tags=["Admin - Reports"])
class AdminReportViewSet(viewsets.ModelViewSet):

    serializer_class = ReportAdminSerializer
    permission_classes = [IsSuperUser]
    authentication_classes = [JWTAuthentication]
    queryset = Report.objects.filter(is_active=True).order_by("-created_at")
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Optional filtering by status
        status_filter = request.query_params.get("status", None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Optional filtering by category
        category_filter = request.query_params.get("category", None)
        if category_filter:
            queryset = queryset.filter(category=category_filter)

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.get_serializer(page, many=True).data

            result = {
                "count": getattr(self.paginator.page.paginator, "count", len(data)),
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "results": data,
            }
            return api_response(
                result=result,
                is_success=True,
                status_code=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Get report details",
        description="Retrieve details of a specific report.",
        responses={
            200: ReportAdminSerializer,
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
            404: OpenApiResponse(description="Report not found."),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Update report",
        description="Update a report's status or admin notes.",
        request=ReportAdminSerializer,
        responses={
            200: ReportAdminSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
            404: OpenApiResponse(description="Report not found."),
        },
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
        summary="Partial update report",
        description="Partially update a report's status or admin notes.",
        request=ReportAdminSerializer,
        responses={
            200: ReportAdminSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized."),
            403: OpenApiResponse(description="Forbidden. Superuser access required."),
            404: OpenApiResponse(description="Report not found."),
        },
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
