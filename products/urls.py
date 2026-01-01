from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    CategoryViewSet,
    ConditionViewSet,
    GetUserProductsViewSet,
)
from django.urls import path, include

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="products")
router.register(r"categories", CategoryViewSet, basename="categories")
router.register(r"conditions", ConditionViewSet, basename="conditions")
router.register(r"listing", GetUserProductsViewSet, basename="user-products")

urlpatterns = [
    path("", include(router.urls)),
]
