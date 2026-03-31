from django.urls import path

from .views import (
    AdminImpactView,
    CommunityHighlightsView,
    NGOImpactView,
    RecyclerImpactView,
    UserImpactView,
)

urlpatterns = [
    path("user/", UserImpactView.as_view(), name="impact-user"),
    path("recycler/", RecyclerImpactView.as_view(), name="impact-recycler"),
    path("ngo/", NGOImpactView.as_view(), name="impact-ngo"),
    path("admin/", AdminImpactView.as_view(), name="impact-admin"),
    path("community/", CommunityHighlightsView.as_view(), name="impact-community"),
]
