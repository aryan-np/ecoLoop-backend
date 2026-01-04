from django.urls import path, include
from rest_framework.routers import DefaultRouter
from accounts.views import (
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    RefreshTokenView,
    UserProfileViewSet,
    OTPVerifyView,
)

router = DefaultRouter()
router.register(r"user-profile", UserProfileViewSet, basename="user-profile")

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    path("login/", UserLoginView.as_view(), name="user-login"),
    path("logout/", UserLogoutView.as_view(), name="user-logout"),
    # path('profile/', UserProfileView.as_view(), name='user-profile'),
    path("token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("verify-otp/", OTPVerifyView.as_view(), name="otp-verify"),
    path("", include(router.urls)),
]
