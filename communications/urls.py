from django.urls import path, include
from rest_framework.routers import DefaultRouter
from communications.views import ThreadViewSet, MessageViewSet, OfferViewSet

router = DefaultRouter()
router.register(r"threads", ThreadViewSet, basename="thread")
router.register(r"messages", MessageViewSet, basename="message")
router.register(r"offers", OfferViewSet, basename="offer")

urlpatterns = [
    path("", include(router.urls)),
]
