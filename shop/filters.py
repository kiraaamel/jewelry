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

from typing import Any, Optional, Union
from django_filters import rest_framework as filters
from django.db import models
from django.db.models import QuerySet, Q, F
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

    Attributes:
        price_min: Минимальная цена (>=)
        price_max: Максимальная цена (<=)
        stones: Наличие камней (True/False)
        silver_type: Тип серебра (Sterling, Oxidized, Rhodium, Black)
        fineness: Проба серебра (925, 960, 999)
        stone_type: Тип камня (Amethyst, Citrine, Garnet и т.д.)
        has_discount: Наличие скидки (кастомный метод)
        collection: ID коллекции (точное совпадение)
        collection_slug: Slug коллекции (точное совпадение)
    """

    # Фильтрация по цене (минимальная и максимальная)
    price_min: filters.NumberFilter = filters.NumberFilter(
        field_name='price',
        lookup_expr='gte',
        help_text='Минимальная цена товара (>=)'
    )
    price_max: filters.NumberFilter = filters.NumberFilter(
        field_name='price',
        lookup_expr='lte',
        help_text='Максимальная цена товара (<=)'
    )

    # Фильтрация по наличию камней
    stones: filters.BooleanFilter = filters.BooleanFilter(
        field_name='stones',
        help_text='Наличие драгоценных камней (true - с камнями, false - без камней)'
    )

    # Фильтрация по типу серебра
    silver_type: filters.ChoiceFilter = filters.ChoiceFilter(
        field_name='silver_type',
        choices=Product.SILVER_TYPE_CHOICES,
        lookup_expr='exact',
        help_text='Тип серебра (sterling, oxidized, rhodium, black)'
    )

    # Фильтрация по пробе серебра
    fineness: filters.ChoiceFilter = filters.ChoiceFilter(
        field_name='fineness',
        choices=Product.FINENESS_CHOICES,
        lookup_expr='exact',
        help_text='Проба серебра (925, 960, 999)'
    )

    # Фильтрация по типу камня
    stone_type: filters.ChoiceFilter = filters.ChoiceFilter(
        field_name='stone_type',
        choices=Product.STONE_TYPE_CHOICES,
        lookup_expr='exact',
        help_text='Тип драгоценного камня'
    )

    # Фильтрация по наличию скидки
    has_discount: filters.BooleanFilter = filters.BooleanFilter(
        method='filter_has_discount',
        help_text='Товары со скидкой (true - только со скидкой, false - все товары)'
    )

    # Фильтрация по коллекции (по ID или slug)
    collection: filters.NumberFilter = filters.NumberFilter(
        field_name='collection__id',
        help_text='ID коллекции'
    )
    collection_slug: filters.CharFilter = filters.CharFilter(
        field_name='collection__slug',
        help_text='Slug коллекции (человекочитаемый идентификатор)'
    )

    def filter_has_discount(self, queryset: QuerySet[Product], name: str, value: bool) -> QuerySet[Product]:
        """
        Фильтрует товары по наличию скидки.

        Товар считается со скидкой, если:
        - old_price не равен NULL
        - old_price больше текущей price

        Args:
            queryset: Исходный QuerySet товаров.
            name: Имя поля (has_discount) — используется для совместимости с API фильтров.
            value: Значение фильтра.
                - True: возвращает только товары со скидкой.
                - False: возвращает все товары (без фильтрации).

        Returns:
            QuerySet[Product]: Отфильтрованный QuerySet.

        Example:
            >>> filter = ProductFilter(data={'has_discount': True})
            >>> filter.qs  # Только товары с old_price > price
        """
        if value:
            return queryset.filter(
                old_price__isnull=False,
                old_price__gt=F('price')
            )
        return queryset

    class Meta:
        """
        Метакласс для настройки фильтра.

        Attributes:
            model: Модель, для которой создаётся фильтр.
            fields: Список полей, доступных для фильтрации.
        """
        model: type[Product] = Product
        fields: list[str] = [
            'category',           # Фильтр по категории (ID)
            'silver_type',        # Фильтр по типу серебра
            'fineness',           # Фильтр по пробе
            'stones',             # Фильтр по наличию камней
            'stone_type',         # Фильтр по типу камня
            'collection',         # Фильтр по ID коллекции
            'collection_slug',    # Фильтр по slug коллекции
            'is_active',          # Фильтр по активности товара
            'price_min',          # Фильтр по минимальной цене
            'price_max',          # Фильтр по максимальной цене
            'has_discount',       # Фильтр по наличию скидки
        ]