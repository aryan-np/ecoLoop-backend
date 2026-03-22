from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from donations.models import DonationRequest, NGOOffer
from drf_spectacular.utils import OpenApiResponse, extend_schema
from ecoLoop.utils import api_response
from recycle.models import ScrapOffer, ScrapRequest

from .serializers import ImpactAnalyticsSerializer


def _to_float(value):
    return float(value or 0)


class ImpactAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Analytics"],
        summary="Get impact analytics",
        description=(
            "Return impact analytics for the authenticated user, including user-level "
            "metrics and role-based NGO/Recycler metrics."
        ),
        responses={
            200: ImpactAnalyticsSerializer,
            401: OpenApiResponse(description="Unauthorized"),
        },
    )
    def get(self, request, *args, **kwargs):
        role_names = set(request.user.roles.values_list("name", flat=True))

        result = {
            "generated_at": timezone.now(),
            "role_flags": {
                "is_user": "USER" in role_names,
                "is_ngo": "NGO" in role_names,
                "is_recycler": "RECYCLER" in role_names,
            },
            "user_impact": self._build_user_impact(request.user),
            "ngo_impact": (
                self._build_ngo_impact(request.user) if "NGO" in role_names else None
            ),
            "recycler_impact": (
                self._build_recycler_impact(request.user)
                if "RECYCLER" in role_names
                else None
            ),
        }

        serializer = ImpactAnalyticsSerializer(result)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )

    def _build_user_impact(self, user):
        donation_qs = DonationRequest.objects.filter(user=user)
        scrap_qs = ScrapRequest.objects.filter(user=user)

        total_donations = donation_qs.count()
        total_scraps = scrap_qs.count()
        total_requests = total_donations + total_scraps

        completed_donations = donation_qs.filter(status="completed").count()
        completed_scraps = scrap_qs.filter(status="completed").count()

        completed_scrap_weight = (
            scrap_qs.filter(status="completed").aggregate(total=Sum("weight_kg"))[
                "total"
            ]
            or 0
        )

        completion_rate = (
            round(((completed_donations + completed_scraps) / total_requests) * 100, 2)
            if total_requests
            else 0.0
        )

        connected_ngos = (
            donation_qs.exclude(accepted_by__isnull=True)
            .values("accepted_by")
            .distinct()
            .count()
        )
        connected_recyclers = (
            scrap_qs.exclude(accepted_by__isnull=True)
            .values("accepted_by")
            .distinct()
            .count()
        )

        return {
            "total_requests": total_requests,
            "total_donation_requests": total_donations,
            "total_scrap_requests": total_scraps,
            "completed_donations": completed_donations,
            "completed_scrap_requests": completed_scraps,
            "completed_scrap_weight_kg": _to_float(completed_scrap_weight),
            "connected_ngos": connected_ngos,
            "connected_recyclers": connected_recyclers,
            "completion_rate_percent": completion_rate,
        }

    def _build_ngo_impact(self, user):
        accepted_requests_qs = DonationRequest.objects.filter(accepted_by=user)
        offers_qs = NGOOffer.objects.filter(ngo=user)

        requests_accepted = accepted_requests_qs.count()
        completed_pickups = accepted_requests_qs.filter(status="completed").count()
        pending_pickups = accepted_requests_qs.filter(status="accepted").count()

        completion_rate = (
            round((completed_pickups / requests_accepted) * 100, 2)
            if requests_accepted
            else 0.0
        )

        donors_supported = (
            accepted_requests_qs.filter(status="completed")
            .values("user")
            .distinct()
            .count()
        )

        return {
            "offers_made": offers_qs.count(),
            "offers_completed": offers_qs.filter(status="completed").count(),
            "requests_accepted": requests_accepted,
            "pending_pickups": pending_pickups,
            "completed_pickups": completed_pickups,
            "donors_supported": donors_supported,
            "completion_rate_percent": completion_rate,
        }

    def _build_recycler_impact(self, user):
        accepted_requests_qs = ScrapRequest.objects.filter(accepted_by=user)
        offers_qs = ScrapOffer.objects.filter(recycler=user)

        requests_accepted = accepted_requests_qs.count()
        completed_pickups = accepted_requests_qs.filter(status="completed").count()
        pending_pickups = accepted_requests_qs.filter(status="accepted").count()

        completed_requests = accepted_requests_qs.filter(status="completed")

        total_weight_recycled = (
            completed_requests.aggregate(total=Sum("weight_kg"))["total"] or 0
        )

        earnings_expression = ExpressionWrapper(
            F("weight_kg") * F("category__rate_per_kg"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
        estimated_earnings = (
            completed_requests.aggregate(total=Sum(earnings_expression))["total"] or 0
        )

        completion_rate = (
            round((completed_pickups / requests_accepted) * 100, 2)
            if requests_accepted
            else 0.0
        )

        households_served = completed_requests.values("user").distinct().count()

        return {
            "offers_made": offers_qs.count(),
            "offers_completed": offers_qs.filter(status="completed").count(),
            "requests_accepted": requests_accepted,
            "pending_pickups": pending_pickups,
            "completed_pickups": completed_pickups,
            "households_served": households_served,
            "total_weight_recycled_kg": _to_float(total_weight_recycled),
            "estimated_earnings": _to_float(estimated_earnings),
            "completion_rate_percent": completion_rate,
        }
