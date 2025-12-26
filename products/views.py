from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)

from .models import Product
from .serializers import ProductSerializer
from accounts.permissions import IsOwnerOrReadOnly


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
    # permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    # authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        # public view of active products (change if you want owner-only listing)
        return Product.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
