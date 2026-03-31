from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from accounts.models import Organization, Report, Role, User
from accounts.permissions import IsNGO, IsRecycler, IsSuperUser
from donations.models import DonationRequest
from drf_spectacular.utils import OpenApiResponse, extend_schema
from ecoLoop.utils import api_response
from products.models import Product
from recycle.models import ScrapRequest

from .serializers import (
    AdminImpactSerializer,
    CommunityHighlightsSerializer,
    NGOImpactSerializer,
    RecyclerImpactSerializer,
    UserImpactSerializer,
)
from .utils import (
    calculate_co2_saved,
    get_donation_items_by_category,
    get_donor_leaderboard_for_ngo,
    get_monthly_chart_data,
    get_partner_organizations,
    get_photo_proof_completion_rate,
    get_scrap_weight_by_category,
    get_top_donors,
    get_top_recyclers,
)


class UserImpactView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Impact"],
        summary="Get user impact summary",
        description=(
            "Returns logged-in user impact summary with marketplace, donation, "
            "recycling, community highlights, and partner organizations."
        ),
        responses={
            200: UserImpactSerializer,
            401: OpenApiResponse(description="Unauthorized"),
        },
    )
    def get(self, request):
        user = request.user

        items_sold = Product.objects.filter(owner=user, status="sold").count()
        items_donated = DonationRequest.objects.filter(
            user=user, status="completed"
        ).count()

        completed_scraps = ScrapRequest.objects.filter(user=user, status="completed")
        scrap_recycled_kg = float(
            completed_scraps.aggregate(total=Sum("weight_kg"))["total"] or 0
        )
        co2_saved_kg = calculate_co2_saved(completed_scraps)

        result = {
            "items_sold": items_sold,
            "items_donated": items_donated,
            "scrap_recycled_kg": scrap_recycled_kg,
            "co2_saved_kg": co2_saved_kg,
            "community_highlights": {
                "top_donors": get_top_donors(limit=10),
                "top_recyclers": get_top_recyclers(limit=10),
            },
            "partner_organizations": get_partner_organizations(user),
        }

        serializer = UserImpactSerializer(result)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


class RecyclerImpactView(APIView):
    permission_classes = [IsAuthenticated, IsRecycler]

    @extend_schema(
        tags=["Impact"],
        summary="Get recycler impact dashboard",
        description="Returns recycler impact metrics, category breakdowns, and monthly chart.",
        responses={
            200: RecyclerImpactSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        },
    )
    def get(self, request):
        recycler = request.user

        accepted_requests = ScrapRequest.objects.filter(accepted_by=recycler)
        completed_requests = accepted_requests.filter(status="completed")

        total_pickups_completed = completed_requests.count()
        total_weight_collected_kg = float(
            completed_requests.aggregate(total=Sum("weight_kg"))["total"] or 0
        )

        weight_by_category = get_scrap_weight_by_category(completed_requests)
        top_category = weight_by_category[0] if weight_by_category else None

        earnings_expression = ExpressionWrapper(
            F("weight_kg") * F("category__rate_per_kg"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
        estimated_earnings = float(
            completed_requests.aggregate(total=Sum(earnings_expression))["total"] or 0
        )

        result = {
            "total_pickups_completed": total_pickups_completed,
            "total_weight_collected_kg": total_weight_collected_kg,
            "weight_by_category": weight_by_category,
            "total_co2_saved_kg": calculate_co2_saved(completed_requests),
            "total_unique_users_served": completed_requests.values("user")
            .distinct()
            .count(),
            "monthly_pickups_chart": get_monthly_chart_data(
                completed_requests, date_field="request_date", months=12
            ),
            "top_scrap_category": top_category["category"] if top_category else None,
            "top_scrap_category_percentage": (
                top_category["percentage"] if top_category else 0.0
            ),
            "estimated_earnings": estimated_earnings,
        }

        serializer = RecyclerImpactSerializer(result)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


class NGOImpactView(APIView):
    permission_classes = [IsAuthenticated, IsNGO]

    @extend_schema(
        tags=["Impact"],
        summary="Get NGO impact dashboard",
        description="Returns NGO impact metrics, donor leaderboard, and monthly chart.",
        responses={
            200: NGOImpactSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        },
    )
    def get(self, request):
        ngo = request.user

        accepted_requests = DonationRequest.objects.filter(accepted_by=ngo)
        completed_requests = accepted_requests.filter(status="completed")

        result = {
            "total_donation_requests_fulfilled": completed_requests.count(),
            "items_by_category": get_donation_items_by_category(completed_requests),
            # Estimated beneficiaries, because there is no explicit beneficiaries field.
            "total_beneficiaries_served": completed_requests.count(),
            "donor_leaderboard": get_donor_leaderboard_for_ngo(ngo, limit=10),
            "monthly_donations_chart": get_monthly_chart_data(
                completed_requests, date_field="request_date", months=12
            ),
            "photo_proof_completion_rate": get_photo_proof_completion_rate(
                accepted_requests
            ),
        }

        serializer = NGOImpactSerializer(result)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


class AdminImpactView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]

    @extend_schema(
        tags=["Impact"],
        summary="Get admin impact dashboard",
        description="Returns platform-wide impact metrics. Admin only.",
        responses={
            200: AdminImpactSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
        },
    )
    def get(self, request):
        completed_scraps = ScrapRequest.objects.filter(status="completed")

        platform_totals = {
            "items_sold": Product.objects.filter(status="sold").count(),
            "items_donated": DonationRequest.objects.filter(status="completed").count(),
            "items_recycled_kg": float(
                completed_scraps.aggregate(total=Sum("weight_kg"))["total"] or 0
            ),
            "co2_saved_kg": calculate_co2_saved(completed_scraps),
        }

        recycler_role = Role.objects.filter(name="RECYCLER").first()
        ngo_role = Role.objects.filter(name="NGO").first()

        active_users = {
            "total_users": User.objects.filter(is_active=True).count(),
            "total_recyclers": (
                recycler_role.users.filter(is_active=True).count()
                if recycler_role
                else 0
            ),
            "total_ngos": (
                ngo_role.users.filter(is_active=True).count() if ngo_role else 0
            ),
        }

        top_recycler_entry = get_top_recyclers(limit=1)
        top_recycler = None
        if top_recycler_entry:
            data = top_recycler_entry[0]
            org = Organization.objects.filter(
                user__id=data["recycler_id"], org_type="RECYCLER"
            ).first()
            top_recycler = {
                "id": data["recycler_id"],
                "name": org.name if org else data["full_name"],
                "metric_value": data["total_weight_kg"],
            }

        top_ngo_row = (
            DonationRequest.objects.filter(
                status="completed", accepted_by__isnull=False
            )
            .values("accepted_by__id")
            .annotate(total_donations=Count("id"))
            .order_by("-total_donations")
            .first()
        )
        top_ngo = None
        if top_ngo_row:
            org = Organization.objects.filter(
                user__id=top_ngo_row["accepted_by__id"], org_type="NGO"
            ).first()
            top_ngo = {
                "id": str(top_ngo_row["accepted_by__id"]),
                "name": org.name if org else "Unknown NGO",
                "metric_value": float(top_ngo_row["total_donations"]),
            }

        monthly_activity = {}
        monthly_products = get_monthly_chart_data(
            Product.objects.filter(status="sold"), date_field="created_at", months=12
        )
        monthly_donations = get_monthly_chart_data(
            DonationRequest.objects.filter(status="completed"),
            date_field="request_date",
            months=12,
        )
        monthly_scraps = get_monthly_chart_data(
            ScrapRequest.objects.filter(status="completed"),
            date_field="request_date",
            months=12,
        )

        for item in monthly_products:
            monthly_activity[item["month"]] = (
                monthly_activity.get(item["month"], 0) + item["count"]
            )
        for item in monthly_donations:
            monthly_activity[item["month"]] = (
                monthly_activity.get(item["month"], 0) + item["count"]
            )
        for item in monthly_scraps:
            monthly_activity[item["month"]] = (
                monthly_activity.get(item["month"], 0) + item["count"]
            )

        monthly_activity_chart = [
            {"month": month, "count": count}
            for month, count in sorted(monthly_activity.items())
        ]

        total_reports = Report.objects.count()
        resolved_reports = Report.objects.filter(
            status__in=["resolved", "closed"]
        ).count()
        resolution_rate = (
            round((resolved_reports / total_reports) * 100, 2) if total_reports else 0.0
        )

        result = {
            "platform_totals": platform_totals,
            "active_users": active_users,
            "top_recycler": top_recycler,
            "top_ngo": top_ngo,
            "monthly_activity_chart": monthly_activity_chart,
            "dispute_stats": {
                "total_reports": total_reports,
                "resolved_reports": resolved_reports,
                "resolution_rate": resolution_rate,
            },
            "new_registrations_chart": get_monthly_chart_data(
                User.objects.all(), date_field="date_joined", months=12
            ),
        }

        serializer = AdminImpactSerializer(result)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )


class CommunityHighlightsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Impact"],
        summary="Get community highlights",
        description="Returns top donors and top recyclers for the user dashboard.",
        responses={
            200: CommunityHighlightsSerializer,
            401: OpenApiResponse(description="Unauthorized"),
        },
    )
    def get(self, request):
        result = {
            "top_donors": get_top_donors(limit=10),
            "top_recyclers": get_top_recyclers(limit=10),
        }

        serializer = CommunityHighlightsSerializer(result)
        return api_response(
            result=serializer.data,
            is_success=True,
            status_code=status.HTTP_200_OK,
        )
