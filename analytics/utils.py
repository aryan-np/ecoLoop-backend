from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone


CO2_FACTORS_BY_CATEGORY = {
    "metal": Decimal("1.8"),
    "plastic": Decimal("1.5"),
    "paper": Decimal("0.9"),
    "glass": Decimal("0.3"),
}
DEFAULT_CO2_FACTOR = Decimal("1.0")


def _get_co2_factor_for_category(material_type):
    value = (material_type or "").strip().lower()
    for key, factor in CO2_FACTORS_BY_CATEGORY.items():
        if key in value:
            return factor
    return DEFAULT_CO2_FACTOR


def calculate_co2_saved(scrap_requests_qs):
    total_co2 = Decimal("0.0")

    for request in scrap_requests_qs.select_related("category"):
        weight = request.weight_kg or 0
        material_type = request.category.material_type if request.category else ""
        co2_factor = _get_co2_factor_for_category(material_type)
        total_co2 += Decimal(str(weight)) * Decimal(str(co2_factor))

    return float(total_co2)


def get_monthly_chart_data(queryset, date_field="request_date", months=12):
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30 * months)

    monthly_data = (
        queryset.filter(**{f"{date_field}__gte": start_date})
        .annotate(month=TruncMonth(date_field))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    result = []
    for item in monthly_data:
        if item["month"]:
            result.append(
                {
                    "month": item["month"].strftime("%Y-%m"),
                    "count": item["count"],
                }
            )

    return result


def get_scrap_weight_by_category(scrap_requests_qs):
    category_data = (
        scrap_requests_qs.values("category__material_type")
        .annotate(total_weight=Sum("weight_kg"))
        .order_by("-total_weight")
    )

    total_weight = float(sum(item["total_weight"] or 0 for item in category_data))

    result = []
    for item in category_data:
        weight = float(item["total_weight"] or 0)
        percentage = (weight / total_weight * 100) if total_weight > 0 else 0
        result.append(
            {
                "category": item["category__material_type"],
                "weight_kg": weight,
                "percentage": round(percentage, 2),
            }
        )

    return result


def get_donation_items_by_category(donation_requests_qs):
    category_data = (
        donation_requests_qs.values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return [
        {
            "category": item["category__name"],
            "count": item["count"],
        }
        for item in category_data
    ]


def get_top_donors(limit=10):
    from donations.models import DonationRequest

    top_donors = (
        DonationRequest.objects.filter(status="completed")
        .values("user__id", "user__full_name")
        .annotate(total_donations=Count("id"))
        .order_by("-total_donations")[:limit]
    )

    return [
        {
            "user_id": str(donor["user__id"]),
            "full_name": donor["user__full_name"],
            "total_donations": donor["total_donations"],
        }
        for donor in top_donors
    ]


def get_top_recyclers(limit=10):
    from recycle.models import ScrapRequest

    top_recyclers = (
        ScrapRequest.objects.filter(status="completed", accepted_by__isnull=False)
        .values("accepted_by__id", "accepted_by__full_name")
        .annotate(total_weight=Sum("weight_kg"))
        .order_by("-total_weight")[:limit]
    )

    return [
        {
            "recycler_id": str(recycler["accepted_by__id"]),
            "full_name": recycler["accepted_by__full_name"],
            "total_weight_kg": float(recycler["total_weight"] or 0),
        }
        for recycler in top_recyclers
    ]


def get_partner_organizations(user):
    from accounts.models import Organization
    from donations.models import DonationRequest
    from recycle.models import ScrapRequest

    ngo_ids = (
        DonationRequest.objects.filter(
            user=user, accepted_by__isnull=False, status="completed"
        )
        .values_list("accepted_by__id", flat=True)
        .distinct()
    )

    recycler_ids = (
        ScrapRequest.objects.filter(
            user=user, accepted_by__isnull=False, status="completed"
        )
        .values_list("accepted_by__id", flat=True)
        .distinct()
    )

    ngos = Organization.objects.filter(user__id__in=ngo_ids, org_type="NGO").values(
        "id", "name", "user__id"
    )
    recyclers = Organization.objects.filter(
        user__id__in=recycler_ids, org_type="RECYCLER"
    ).values("id", "name", "user__id")

    return {
        "ngos": [
            {
                "id": str(ngo["id"]),
                "name": ngo["name"],
                "org_type": "NGO",
                "user_id": str(ngo["user__id"]),
            }
            for ngo in ngos
        ],
        "recyclers": [
            {
                "id": str(recycler["id"]),
                "name": recycler["name"],
                "org_type": "RECYCLER",
                "user_id": str(recycler["user__id"]),
            }
            for recycler in recyclers
        ],
    }


def get_photo_proof_completion_rate(donation_requests_qs):
    completed = donation_requests_qs.filter(status="completed")
    total = completed.count()

    if total == 0:
        return 0.0

    with_proof = completed.filter(ngo_offers__photo_proof__isnull=False).distinct().count()
    return round((with_proof / total) * 100, 2)


def get_donor_leaderboard_for_ngo(ngo_user, limit=10):
    from donations.models import DonationRequest

    top_donors = (
        DonationRequest.objects.filter(accepted_by=ngo_user, status="completed")
        .values("user__id", "user__full_name")
        .annotate(total_donations=Count("id"))
        .order_by("-total_donations")[:limit]
    )

    return [
        {
            "user_id": str(donor["user__id"]),
            "full_name": donor["user__full_name"],
            "donations_count": donor["total_donations"],
        }
        for donor in top_donors
    ]
