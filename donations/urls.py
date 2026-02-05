from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DonationCategoryViewSet,
    DonationConditionViewSet,
    DonationRequestViewSet,
)

router = DefaultRouter()
router.register(r"categories", DonationCategoryViewSet, basename="donation-categories")
router.register(r"conditions", DonationConditionViewSet, basename="donation-conditions")
router.register(r"requests", DonationRequestViewSet, basename="donation-requests")

urlpatterns = [
    path("", include(router.urls)),
]
