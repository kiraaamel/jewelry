from django_filters import rest_framework as filters
from .models import Product


class ProductFilter(filters.FilterSet):
    """
    Кастомный фильтр для товаров.
    Поддерживает фильтрацию по цене в диапазоне.
    """
    # Фильтр для цены с диапазоном (от и до)
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')

    class Meta:
        model = Product
        fields = ['category', 'metal', 'stones', 'collection', 'price_min', 'price_max']