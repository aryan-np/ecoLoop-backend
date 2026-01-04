from django_filters import (
    FilterSet,
    ChoiceFilter,
    ModelChoiceFilter,
    CharFilter,
    NumberFilter,
)
from .models import Product, Category, Condition


class ProductStatusFilter(FilterSet):
    status = ChoiceFilter(
        field_name="status",
        choices=Product.STATUS_CHOICES,
        label="Product Status",
    )
    category = ModelChoiceFilter(
        field_name="category",
        queryset=Category.objects.filter(is_active=True),
        label="Category",
    )
    condition = ModelChoiceFilter(
        field_name="condition",
        queryset=Condition.objects.filter(is_active=True),
        label="Condition",
    )
    search = CharFilter(
        field_name="title",
        lookup_expr="icontains",
        label="Search",
    )
    price_min = NumberFilter(
        field_name="price",
        lookup_expr="gte",
        label="Min Price",
    )
    price_max = NumberFilter(
        field_name="price",
        lookup_expr="lte",
        label="Max Price",
    )

    class Meta:
        model = Product
        fields = ["status", "category", "condition", "search", "price_min", "price_max"]
