from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InitiatePaymentView, VerifyPaymentView, PaymentViewSet

router = DefaultRouter()
router.register(r"", PaymentViewSet, basename="payments")

urlpatterns = [
    path("initiate/", InitiatePaymentView.as_view(), name="payment-initiate"),
    path("verify/", VerifyPaymentView.as_view(), name="payment-verify"),
    path("", include(router.urls)),
]
