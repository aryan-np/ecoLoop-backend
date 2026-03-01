from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ScrapCategoryViewSet,
    ScrapRequestViewSet,
    RecyclerScrapRequestViewSet,
    RecyclerAcceptedScrapRequestViewSet,
)

router = DefaultRouter()
router.register(r"categories", ScrapCategoryViewSet, basename="scrap-categories")
router.register(r"scrap-requests", ScrapRequestViewSet, basename="scrap-requests")
router.register(
    r"recycler/pending-requests",
    RecyclerScrapRequestViewSet,
    basename="recycler-pending-requests",
)
router.register(
    r"recycler/accepted-requests",
    RecyclerAcceptedScrapRequestViewSet,
    basename="recycler-accepted-requests",
)

urlpatterns = [
    path("", include(router.urls)),
]
