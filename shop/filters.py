from django_filters import rest_framework as filters
from django.db import models
from .models import Product


class ProductFilter(filters.FilterSet):
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')
    stones = filters.BooleanFilter(field_name='stones')
    silver_type = filters.ChoiceFilter(
        field_name='silver_type',
        choices=Product.SILVER_TYPE_CHOICES,
        lookup_expr='exact'
    )
    fineness = filters.ChoiceFilter(
        field_name='fineness',
        choices=Product.FINENESS_CHOICES,
        lookup_expr='exact'
    )
    stone_type = filters.ChoiceFilter(  # ← добавить этот фильтр
        field_name='stone_type',
        choices=Product.STONE_TYPE_CHOICES,
        lookup_expr='exact'
    )
    has_discount = filters.BooleanFilter(method='filter_has_discount')
    
    def filter_has_discount(self, queryset, name, value):
        if value:
            return queryset.filter(old_price__isnull=False, old_price__gt=models.F('price'))
        return queryset

    class Meta:
        model = Product
        fields = [
            'category', 'silver_type', 'fineness', 'stones', 'stone_type',
            'collection', 'is_active', 'price_min', 'price_max', 'has_discount'
        ]