from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScrapCategoryViewSet, ScrapRequestViewSet

router = DefaultRouter()
router.register(r"categories", ScrapCategoryViewSet, basename="scrap-categories")
router.register(r"scrap-requests", ScrapRequestViewSet, basename="scrap-requests")

urlpatterns = [
    path("", include(router.urls)),
]
