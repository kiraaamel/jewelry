from django_filters import rest_framework as filters
from django.db.models import Q
from django.db import models
from .models import Product


class ProductFilter(filters.FilterSet):
    """
    Кастомный фильтр для товаров.
    """
    # Фильтр по цене
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')
    
    # Фильтр по наличию камней
    stones = filters.BooleanFilter(field_name='stones')
    
    # Фильтр по скидке (товары, у которых old_price > price)
    has_discount = filters.BooleanFilter(method='filter_has_discount')
    
    def filter_has_discount(self, queryset, name, value):
        """
        Фильтр товаров со скидкой.
        """
        if value:
            return queryset.filter(old_price__isnull=False, old_price__gt=models.F('price'))
        return queryset

    class Meta:
        model = Product
        fields = ['category', 'metal', 'fineness', 'stones', 'price_min', 'price_max', 'has_discount']