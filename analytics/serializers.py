from rest_framework import serializers


class DonorEntrySerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    full_name = serializers.CharField()
    total_donations = serializers.IntegerField()


class RecyclerEntrySerializer(serializers.Serializer):
    recycler_id = serializers.UUIDField()
    full_name = serializers.CharField()
    total_weight_kg = serializers.FloatField()


class CommunityHighlightsSerializer(serializers.Serializer):
    top_donors = DonorEntrySerializer(many=True)
    top_recyclers = RecyclerEntrySerializer(many=True)


class PartnerOrganizationEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    org_type = serializers.CharField()
    user_id = serializers.UUIDField()


class PartnerOrganizationsSerializer(serializers.Serializer):
    ngos = PartnerOrganizationEntrySerializer(many=True)
    recyclers = PartnerOrganizationEntrySerializer(many=True)


class UserImpactSerializer(serializers.Serializer):
    items_sold = serializers.IntegerField()
    items_donated = serializers.IntegerField()
    scrap_recycled_kg = serializers.FloatField()
    co2_saved_kg = serializers.FloatField()
    community_highlights = CommunityHighlightsSerializer()
    partner_organizations = PartnerOrganizationsSerializer()


class CategoryWeightSerializer(serializers.Serializer):
    category = serializers.CharField()
    weight_kg = serializers.FloatField()
    percentage = serializers.FloatField()


class MonthlyCountSerializer(serializers.Serializer):
    month = serializers.CharField()
    count = serializers.IntegerField()


class RecyclerImpactSerializer(serializers.Serializer):
    total_pickups_completed = serializers.IntegerField()
    total_weight_collected_kg = serializers.FloatField()
    weight_by_category = CategoryWeightSerializer(many=True)
    total_co2_saved_kg = serializers.FloatField()
    total_unique_users_served = serializers.IntegerField()
    monthly_pickups_chart = MonthlyCountSerializer(many=True)
    top_scrap_category = serializers.CharField(allow_null=True)
    top_scrap_category_percentage = serializers.FloatField()
    estimated_earnings = serializers.FloatField()


class DonationCategoryCountSerializer(serializers.Serializer):
    category = serializers.CharField()
    count = serializers.IntegerField()


class NGODonorEntrySerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    full_name = serializers.CharField()
    donations_count = serializers.IntegerField()


class NGOImpactSerializer(serializers.Serializer):
    total_donation_requests_fulfilled = serializers.IntegerField()
    items_by_category = DonationCategoryCountSerializer(many=True)
    total_beneficiaries_served = serializers.IntegerField()
    donor_leaderboard = NGODonorEntrySerializer(many=True)
    monthly_donations_chart = MonthlyCountSerializer(many=True)
    photo_proof_completion_rate = serializers.FloatField()


class PlatformTotalsSerializer(serializers.Serializer):
    items_sold = serializers.IntegerField()
    items_donated = serializers.IntegerField()
    items_recycled_kg = serializers.FloatField()
    co2_saved_kg = serializers.FloatField()


class ActiveUsersSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_recyclers = serializers.IntegerField()
    total_ngos = serializers.IntegerField()


class TopPerformerSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    metric_value = serializers.FloatField()


class DisputeStatsSerializer(serializers.Serializer):
    total_reports = serializers.IntegerField()
    resolved_reports = serializers.IntegerField()
    resolution_rate = serializers.FloatField()


class AdminImpactSerializer(serializers.Serializer):
    platform_totals = PlatformTotalsSerializer()
    active_users = ActiveUsersSerializer()
    top_recycler = TopPerformerSerializer(allow_null=True)
    top_ngo = TopPerformerSerializer(allow_null=True)
    monthly_activity_chart = MonthlyCountSerializer(many=True)
    dispute_stats = DisputeStatsSerializer()
    new_registrations_chart = MonthlyCountSerializer(many=True)
