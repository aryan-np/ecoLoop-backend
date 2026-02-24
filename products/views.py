from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)

from .models import Product, Category, Condition, ProductImage
from .serializers import (
    ProductSerializer,
    ProductListSerializer,
    CategorySerializer,
    ConditionSerializer,
)
from .filters import ProductStatusFilter
from accounts.permissions import IsOwnerOrReadOnlyProduct
from ecoLoop.utils import api_response
from recycle.models import ScrapRequest
from recycle.serializers import ScrapRequestSerializer
from donations.models import DonationRequest
from donations.serializers import DonationRequestSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List categories",
        description="Retrieve all active product categories. No authentication required.",
        responses={200: CategorySerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Get category detail",
        description="Retrieve a specific category by ID. No authentication required.",
        responses={200: CategorySerializer},
    ),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by("name")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


@extend_schema_view(
    list=extend_schema(
        summary="List conditions",
        description="Retrieve all active product conditions. No authentication required.",
        responses={200: ConditionSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Get condition detail",
        description="Retrieve a specific condition by ID. No authentication required.",
        responses={200: ConditionSerializer},
    ),
)
class ConditionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConditionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Condition.objects.filter(is_active=True).order_by("name")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


@extend_schema(tags=["Product"])
@extend_schema_view(
    list=extend_schema(
        summary="List products",
        description="List all active products.",
        responses={200: ProductSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Get product detail",
        responses={200: ProductSerializer},
    ),
    create=extend_schema(
        summary="Create product",
        description="Create a product listing (authenticated users only).",
        request=ProductSerializer,
        responses={201: ProductSerializer},
    ),
    update=extend_schema(
        summary="Update product (full)",
        request=ProductSerializer,
        responses={200: ProductSerializer},
    ),
    partial_update=extend_schema(
        summary="Update product (partial)",
        request=ProductSerializer,
        responses={200: ProductSerializer},
    ),
    destroy=extend_schema(
        summary="Delete product",
        responses={
            204: OpenApiResponse(description="Deleted successfully"),
            403: OpenApiResponse(description="Not allowed (not owner)"),
        },
    ),
)
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnlyProduct]
    authentication_classes = [JWTAuthentication]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    lookup_field = "id"
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductStatusFilter

    def get_permissions(self):
        """
        Allow list and retrieve for anyone.
        Require authentication for create, update, partial_update, and destroy.
        """
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsOwnerOrReadOnlyProduct()]

    def get_serializer_class(self):
        """Use ProductListSerializer for list, ProductSerializer for everything else"""
        if self.action == "list":
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        # Return all products that are active and available

        return (
            Product.objects.filter(
                is_active=True, status="available"
            )
            .select_related("owner", "category", "condition")
            .prefetch_related("images")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        # Save product with authenticated user as owner
        serializer.save(owner=self.request.user)

    @extend_schema(
        summary="List sell products",
        description="List all active sell products. No authentication required. Pagination supported.",
        responses={200: ProductSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

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
        summary="Get sell product detail",
        description="Retrieve a specific product by ID. No authentication required.",
        responses={
            200: ProductSerializer,
            404: OpenApiResponse(description="Product not found."),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = self.get_serializer(instance).data
        return api_response(
            result=data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Create sell product",
        description="Create a new product listing (product_type is forced to 'sell'). Requires authentication.",
        request=ProductSerializer,
        responses={
            201: ProductSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized. Authentication required."),
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
        summary="Update sell product (full)",
        description="Fully update a product (all fields required). Only the owner or admins can update.",
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized. Authentication required."),
            403: OpenApiResponse(description="Not allowed (not owner)."),
            404: OpenApiResponse(description="Product not found."),
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
        summary="Update sell product (partial)",
        description="Partially update a product (only provided fields updated). Only the owner or admins can update.",
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Unauthorized. Authentication required."),
            403: OpenApiResponse(description="Not allowed (not owner)."),
            404: OpenApiResponse(description="Product not found."),
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
        summary="Delete sell product",
        description="Delete a product. Only the owner or admins can delete.",
        responses={
            204: OpenApiResponse(description="Product deleted successfully."),
            401: OpenApiResponse(description="Unauthorized. Authentication required."),
            403: OpenApiResponse(description="Not allowed (not owner)."),
            404: OpenApiResponse(description="Product not found."),
        },
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)

        # Keeping your unified response format even on 204
        return api_response(
            result={"message": "Deleted."},
            is_success=True,
            status_code=status.HTTP_204_NO_CONTENT,
        )


@extend_schema(tags=["Product"])
@extend_schema_view(
    list=extend_schema(
        summary="List owner's all items",
        description="Retrieve all items owned by the authenticated user (products, scrap requests, and donation requests). Requires authentication.",
        responses={200: OpenApiResponse(description="Combined list of products, scrap requests, and donation requests")},
    ),
)
class GetOwnerProductsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ['get']  # Only allow GET requests

    def list(self, request, *args, **kwargs):
        # Get all products
        products = Product.objects.filter(owner=request.user).select_related("owner", "category", "condition").prefetch_related("images").order_by("-created_at")
        product_data = ProductSerializer(products, many=True, context={'request': request}).data
        
        # Get all scrap requests
        scrap_requests = ScrapRequest.objects.filter(user=request.user).select_related("user", "category").prefetch_related("images").order_by("-request_date")
        scrap_data = ScrapRequestSerializer(scrap_requests, many=True, context={'request': request}).data
        
        # Get all donation requests
        donation_requests = DonationRequest.objects.filter(user=request.user).select_related("user", "category", "condition").prefetch_related("images").order_by("-request_date")
        donation_data = DonationRequestSerializer(donation_requests, many=True, context={'request': request}).data
        
        # Add type identifier to each item
        for item in product_data:
            item['item_type'] = 'product'
        for item in scrap_data:
            item['item_type'] = 'scrap'
        for item in donation_data:
            item['item_type'] = 'donation'
        
        # Combine all items
        result = {
            "products": product_data,
            "scrap_requests": scrap_data,
            "donation_requests": donation_data,
            "total_count": len(product_data) + len(scrap_data) + len(donation_data)
        }
        
        return api_response(
            result=result,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


@extend_schema(tags=["Product"])
class GetUserProductsView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    lookup_field = "user"

    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        return (
            Product.objects.filter(
                owner=user_id,

                is_active=True,
                status="available",
            )
            .select_related("owner", "category", "condition")
            .order_by("-created_at")
        )

    @extend_schema(
        summary="List user's sell products",
        description="Retrieve all active sell products for a specific user. No authentication required. Pass user UUID in the URL.",
        responses={
            200: ProductSerializer(many=True),
            404: OpenApiResponse(description="User not found."),
        },
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )
