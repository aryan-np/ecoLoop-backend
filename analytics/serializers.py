from rest_framework import serializers


class RoleFlagsSerializer(serializers.Serializer):
    is_user = serializers.BooleanField()
    is_ngo = serializers.BooleanField()
    is_recycler = serializers.BooleanField()


class UserImpactSerializer(serializers.Serializer):
    total_requests = serializers.IntegerField()
    total_donation_requests = serializers.IntegerField()
    total_scrap_requests = serializers.IntegerField()
    completed_donations = serializers.IntegerField()
    completed_scrap_requests = serializers.IntegerField()
    completed_scrap_weight_kg = serializers.FloatField()
    connected_ngos = serializers.IntegerField()
    connected_recyclers = serializers.IntegerField()
    completion_rate_percent = serializers.FloatField()


class NGOImpactSerializer(serializers.Serializer):
    offers_made = serializers.IntegerField()
    offers_completed = serializers.IntegerField()
    requests_accepted = serializers.IntegerField()
    pending_pickups = serializers.IntegerField()
    completed_pickups = serializers.IntegerField()
    donors_supported = serializers.IntegerField()
    completion_rate_percent = serializers.FloatField()


class RecyclerImpactSerializer(serializers.Serializer):
    offers_made = serializers.IntegerField()
    offers_completed = serializers.IntegerField()
    requests_accepted = serializers.IntegerField()
    pending_pickups = serializers.IntegerField()
    completed_pickups = serializers.IntegerField()
    households_served = serializers.IntegerField()
    total_weight_recycled_kg = serializers.FloatField()
    estimated_earnings = serializers.FloatField()
    completion_rate_percent = serializers.FloatField()


class ImpactAnalyticsSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    role_flags = RoleFlagsSerializer()
    user_impact = UserImpactSerializer()
    ngo_impact = NGOImpactSerializer(allow_null=True)
    recycler_impact = RecyclerImpactSerializer(allow_null=True)
