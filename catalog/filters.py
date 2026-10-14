import django_filters

from catalog.models import Product


class ProductFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category_id")

    class Meta:
        model = Product
        fields = ("category",)
