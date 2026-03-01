from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DonationCategoryViewSet,
    DonationConditionViewSet,
    DonationRequestViewSet,
    NGODonationRequestViewSet,
    NGOAcceptedDonationRequestViewSet,
)

router = DefaultRouter()
router.register(r"categories", DonationCategoryViewSet, basename="donation-categories")
router.register(r"conditions", DonationConditionViewSet, basename="donation-conditions")
router.register(r"requests", DonationRequestViewSet, basename="donation-requests")
router.register(
    r"ngo/pending-requests", NGODonationRequestViewSet, basename="ngo-pending-requests"
)
router.register(
    r"ngo/accepted-requests",
    NGOAcceptedDonationRequestViewSet,
    basename="ngo-accepted-requests",
)

urlpatterns = [
    path("", include(router.urls)),
]
