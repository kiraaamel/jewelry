"""
Фильтры для товаров в каталоге.

Используется django-filter для фильтрации товаров по различным критериям:
- Цена (min/max)
- Наличие камней
- Тип серебра
- Проба
- Тип камня
- Наличие скидки
- Коллекция
"""

from typing import Any
from django_filters import rest_framework as filters
from django.db import models
from django.db.models import QuerySet
from .models import Product


class ProductFilter(filters.FilterSet):
    """
    Фильтр для модели Product.

    Позволяет фильтровать товары по:
    - диапазону цены (price_min, price_max)
    - наличию камней (stones)
    - типу серебра (silver_type)
    - пробе (fineness)
    - типу камня (stone_type)
    - наличию скидки (has_discount)
    - коллекции (collection, collection_slug)
    """

    # Фильтрация по цене (минимальная и максимальная)
    price_min: filters.NumberFilter = filters.NumberFilter(
        field_name='price',
        lookup_expr='gte'
    )
    price_max: filters.NumberFilter = filters.NumberFilter(
        field_name='price',
        lookup_expr='lte'
    )

    # Фильтрация по наличию камней
    stones: filters.BooleanFilter = filters.BooleanFilter(field_name='stones')

    # Фильтрация по типу серебра
    silver_type: filters.ChoiceFilter = filters.ChoiceFilter(
        field_name='silver_type',
        choices=Product.SILVER_TYPE_CHOICES,
        lookup_expr='exact'
    )

    # Фильтрация по пробе серебра
    fineness: filters.ChoiceFilter = filters.ChoiceFilter(
        field_name='fineness',
        choices=Product.FINENESS_CHOICES,
        lookup_expr='exact'
    )

    # Фильтрация по типу камня
    stone_type: filters.ChoiceFilter = filters.ChoiceFilter(
        field_name='stone_type',
        choices=Product.STONE_TYPE_CHOICES,
        lookup_expr='exact'
    )

    # Фильтрация по наличию скидки
    has_discount: filters.BooleanFilter = filters.BooleanFilter(
        method='filter_has_discount'
    )

    # Фильтрация по коллекции (по ID или slug)
    collection: filters.NumberFilter = filters.NumberFilter(
        field_name='collection__id'
    )
    collection_slug: filters.CharFilter = filters.CharFilter(
        field_name='collection__slug'
    )

    def filter_has_discount(self, queryset: QuerySet[Product], name: str, value: bool) -> QuerySet[Product]:
        """
        Фильтрует товары по наличию скидки.

        Args:
            queryset (QuerySet[Product]): Исходный QuerySet товаров
            name (str): Имя поля (has_discount)
            value (bool): True - товары со скидкой, False - все товары

        Returns:
            QuerySet[Product]: Отфильтрованный QuerySet
        """
        if value:
            return queryset.filter(
                old_price__isnull=False,
                old_price__gt=models.F('price')
            )
        return queryset

    class Meta:
        model = Product
        fields: list = [
            'category', 'silver_type', 'fineness', 'stones', 'stone_type',
            'collection', 'collection_slug', 'is_active', 'price_min',
            'price_max', 'has_discount'
        ]