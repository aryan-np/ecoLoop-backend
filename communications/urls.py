from django.urls import path, include
from rest_framework.routers import DefaultRouter
from communications.views import ThreadViewSet, MessageViewSet

router = DefaultRouter()
router.register(r"threads", ThreadViewSet, basename="thread")
router.register(r"messages", MessageViewSet, basename="message")

urlpatterns = [
    path("", include(router.urls)),
]
