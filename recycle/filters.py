from django_filters import FilterSet, ChoiceFilter, ModelChoiceFilter, CharFilter
from .models import ScrapCategory, ScrapRequest


class ScrapRequestFilter(FilterSet):
    """
    FilterSet for filtering scrap requests by category, condition, and weight range.
    """

    category = ModelChoiceFilter(
        field_name="category",
        queryset=ScrapCategory.objects.all(),
        label="Category",
    )
    condition = ChoiceFilter(
        field_name="condition",
        choices=ScrapRequest.CONDITION_CHOICES,
        label="Condition",
    )
    weight_range = ChoiceFilter(
        field_name="weight_kg",
        method="filter_weight_range",
        choices=[
            ("0-10", "0 to 10 kg"),
            ("10-20", "10 to 20 kg"),
            ("20+", "20+ kg"),
        ],
        label="Weight Range",
    )

    class Meta:
        model = ScrapRequest
        fields = ["category", "condition", "weight_range"]

    def filter_weight_range(self, queryset, name, value):
        """
        Custom filter method for weight ranges.
        """
        if value == "0-10":
            return queryset.filter(weight_kg__gte=0, weight_kg__lt=10)
        elif value == "10-20":
            return queryset.filter(weight_kg__gte=10, weight_kg__lt=20)
        elif value == "20+":
            return queryset.filter(weight_kg__gte=20)
        return queryset
