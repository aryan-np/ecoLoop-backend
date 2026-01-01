from django_filters import FilterSet, ChoiceFilter
from .models import Product


class ProductStatusFilter(FilterSet):
    status = ChoiceFilter(
        field_name="status",
        choices=Product.STATUS_CHOICES,
        label="Product Status",
    )

    class Meta:
        model = Product
        fields = ["status"]
