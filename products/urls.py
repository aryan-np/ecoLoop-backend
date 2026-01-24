from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    CategoryViewSet,
    ConditionViewSet,
    GetOwnerProductsViewSet,
    GetUserProductsView,
)
from django.urls import path, include

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="products")
router.register(r"categories", CategoryViewSet, basename="categories")
router.register(r"conditions", ConditionViewSet, basename="conditions")
router.register(r"listing", GetOwnerProductsViewSet, basename="user-products")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<uuid:user_id>/products/",
        GetUserProductsView.as_view(),
        name="user-products-list",
    ),
]
