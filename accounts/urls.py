from django.urls import path
from accounts.views import (
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    RefreshTokenView,
)

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    path("login/", UserLoginView.as_view(), name="user-login"),
    path("logout/", UserLogoutView.as_view(), name="user-logout"),
    # path('profile/', UserProfileView.as_view(), name='user-profile'),
    path("token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
]
