from django.urls import path

from .views import ImpactAnalyticsView

urlpatterns = [
    path("impact/", ImpactAnalyticsView.as_view(), name="impact-analytics"),
]
