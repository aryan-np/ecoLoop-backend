from rest_framework import viewsets, status
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

from .models import Product, Category, Condition
from .serializers import ProductSerializer, CategorySerializer, ConditionSerializer
from .filters import ProductStatusFilter
from accounts.permissions import IsOwnerOrReadOnlyProduct
from ecoLoop.utils import api_response


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for listing categories.
    GET /api/products/categories/ - List all active categories
    """

    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by("name")


class ConditionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for listing conditions.
    GET /api/products/conditions/ - List all active conditions
    """

    serializer_class = ConditionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Condition.objects.filter(is_active=True).order_by("name")


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

    def get_queryset(self):
        # Only return products with type "sell" (status filter applied separately)

        return (
            Product.objects.filter(
                is_active=True, product_type="sell", status="available"
            )
            .select_related("owner", "category", "condition")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        # Always set product_type to "sell" when creating
        serializer.save(owner=self.request.user, product_type="sell")

    @extend_schema(
        summary="List sell products",
        description="List all active products where product_type='sell'.",
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
        responses={
            200: ProductSerializer,
            404: OpenApiResponse(description="Not found."),
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
        description="Create a product listing (product_type is forced to 'sell').",
        request=ProductSerializer,
        responses={
            201: ProductSerializer,
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

        self.perform_create(serializer)

        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Update sell product (full)",
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Not allowed (not owner)."),
            404: OpenApiResponse(description="Not found."),
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
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Not allowed (not owner)."),
            404: OpenApiResponse(description="Not found."),
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
        responses={
            204: OpenApiResponse(description="Deleted."),
            403: OpenApiResponse(description="Not allowed (not owner)."),
            404: OpenApiResponse(description="Not found."),
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
class GetUserProductsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to get products of the authenticated user.
    GET /api/products/my-products/ - List products owned by the authenticated user
    """

    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    lookup_field = "id"
    filterset_class = ProductStatusFilter
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        return (
            Product.objects.filter(owner=self.request.user)
            .select_related("owner", "category", "condition")
            .order_by("-created_at")
        )
