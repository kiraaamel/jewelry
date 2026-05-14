"""
Административная панель для интернет-магазина Argentic Jewelry.

Содержит настройки отображения и управления всеми моделями:
пользователи, товары, категории, заказы, отзывы, корзины, промокоды, коллекции.
"""

from typing import Any, Optional
from decimal import Decimal
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from .models import (
    User, Category, Product, Collection, Cart, CartItem, Order, OrderItem,
    Review, Wishlist, PromoCode, PromoCodeUsage
)


class ReviewAdmin(admin.ModelAdmin):
    """
    Настройки отображения отзывов в админке.
    """
    list_display: list = ['id', 'user', 'product', 'rating', 'created_at', 'moderated']
    list_filter: list = ['rating', 'moderated', 'created_at']
    search_fields: list = ['user__email', 'product__name', 'comment']
    list_editable: list = ['moderated']
    readonly_fields: list = ['created_at']

    fieldsets: tuple = (
        ('Основная информация', {
            'fields': ('user', 'product', 'rating', 'created_at')
        }),
        ('Содержание', {
            'fields': ('comment', 'image')
        }),
        ('Модерация', {
            'fields': ('moderated',)
        }),
    )


class OrderItemInline(admin.TabularInline):
    """
    Встроенная форма для позиций заказа.
    """
    model = OrderItem
    extra: int = 1
    fields: list = ['product', 'quantity', 'item_total_display']
    readonly_fields: list = ['item_total_display']

    def item_total_display(self, obj: OrderItem) -> str:
        """
        Рассчитывает стоимость позиции.

        Args:
            obj (OrderItem): Объект позиции заказа

        Returns:
            str: Стоимость позиции в формате "X ₽"
        """
        if obj.pk and obj.product and obj.quantity:
            total = obj.product.price * obj.quantity
            return f"{total} ₽"
        elif obj.pk and obj.price and obj.quantity:
            total = obj.price * obj.quantity
            return f"{total} ₽"
        return "0 ₽"
    item_total_display.short_description = "Стоимость"


class OrderAdmin(admin.ModelAdmin):
    """
    Настройки отображения заказа в админке.
    total_price не вводится, а рассчитывается автоматически.
    """
    inlines: list = [OrderItemInline]
    list_display: list = [
        'order_number', 'user', 'created_at', 'status',
        'total_price_display', 'delivery_method', 'delivery_date', 'delivery_time'
    ]
    list_filter: list = ['status', 'delivery_method', 'payment_method', 'created_at']
    search_fields: list = ['order_number', 'user__email', 'delivery_address']
    readonly_fields: list = ['order_number', 'created_at', 'total_price_display']
    list_editable: list = ['status']
    exclude: list = ['total_price']

    fieldsets: tuple = (
        ('Основная информация', {
            'fields': ('order_number', 'user', 'status', 'total_price_display', 'created_at')
        }),
        ('Доставка', {
            'fields': ('delivery_address', 'delivery_method', 'delivered_at', 'delivery_date', 'delivery_time')
        }),
        ('Оплата', {
            'fields': ('payment_method',)
        }),
        ('Дополнительно', {
            'fields': ('gift_wrap', 'gift_message', 'comment'),
            'classes': ('collapse',)
        }),
    )

    def total_price_display(self, obj: Order) -> str:
        """
        Рассчитывает общую стоимость заказа из позиций.

        Args:
            obj (Order): Объект заказа

        Returns:
            str: Общая стоимость в формате "X ₽"
        """
        if obj.pk:
            total = 0
            for item in obj.items.all():
                if item.product and item.quantity:
                    total += item.product.price * item.quantity
                elif item.price and item.quantity:
                    total += item.price * item.quantity
            return f"{total} ₽"
        return "0 ₽"
    total_price_display.short_description = "Общая стоимость"

    def save_related(self, request: HttpRequest, form, formsets, change: bool) -> None:
        """
        Сохраняет позиции и обновляет total_price в заказе.

        Args:
            request (HttpRequest): HTTP запрос
            form: Форма заказа
            formsets: Форсеты позиций
            change (bool): Флаг изменения
        """
        super().save_related(request, form, formsets, change)

        order = form.instance

        for item in order.items.all():
            if item.product:
                if not item.product_name or item.product_name != item.product.name:
                    item.product_name = item.product.name
                if not item.price or item.price != item.product.price:
                    item.price = item.product.price
                item.save()

        total = 0
        for item in order.items.all():
            if item.product and item.quantity:
                total += item.product.price * item.quantity
            elif item.price and item.quantity:
                total += item.price * item.quantity

        if total != order.total_price:
            order.total_price = total
            order.save(update_fields=['total_price'])


class CartItemInline(admin.TabularInline):
    """
    Встроенная форма для элементов корзины.
    """
    model = CartItem
    extra: int = 0
    readonly_fields: list = ['product', 'quantity', 'added_at', 'total_price']


class CartAdmin(admin.ModelAdmin):
    """
    Настройки отображения корзины в админке.
    """
    inlines: list = [CartItemInline]
    list_display: list = ['id', 'user', 'session_key', 'total_items', 'total_price', 'updated_at']
    list_filter: list = ['updated_at']
    search_fields: list = ['user__email', 'session_key']
    readonly_fields: list = ['created_at', 'updated_at']


class ProductAdmin(admin.ModelAdmin):
    """
    Настройки отображения товаров в админке.
    """
    list_display: list = [
        'id', 'name', 'category', 'price_display', 'collection',
        'silver_info', 'weight', 'stock_status', 'has_discount_display',
        'stones_display', 'image_preview', 'images_count_display', 'created_at'
    ]
    list_filter: list = ['category', 'silver_type', 'fineness', 'stones', 'created_at', 'collection']
    list_display_links: list = ['name']
    search_fields: list = ['name', 'description', 'collection']
    prepopulated_fields: dict = {'slug': ('name',)}
    readonly_fields: list = ['created_at', 'updated_at', 'available_quantity_display',
                             'full_silver_info', 'images_preview']
    raw_id_fields: list = ['created_by', 'category']
    date_hierarchy: str = 'created_at'

    fieldsets: tuple = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Цены', {
            'fields': ('price', 'old_price'),
            'classes': ('wide',)
        }),
        ('Остатки на складе', {
            'fields': ('stock_quantity', 'reserved_quantity', 'available_quantity_display'),
            'classes': ('wide',)
        }),
        ('Фотографии товара', {
            'fields': ('image', 'image_2', 'image_3', 'image_4', 'image_5', 'images_preview'),
            'description': 'Загрузите фотографии товара. Первое фото (Главное) обязательно для отображения',
            'classes': ('wide',)
        }),
        ('Характеристики серебра', {
            'fields': ('silver_type', 'fineness', 'weight', 'size', 'full_silver_info'),
            'description': 'Информация о типе и пробе серебряного изделия'
        }),
        ('Драгоценные камни', {
            'fields': ('stones', 'stone_type', 'stone_weight'),
            'classes': ('collapse',),
            'description': 'Если в изделии есть камни, укажите их характеристики'
        }),
        ('Метаданные', {
            'fields': ('collection', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions: list = ['apply_discount', 'increase_price']

    @admin.display(description='Цена')
    def price_display(self, obj: Product) -> str:
        """
        Отображает цену товара со скидкой, если есть.

        Args:
            obj (Product): Объект товара

        Returns:
            str: HTML с отображением цены
        """
        if obj.has_discount:
            discount_percent = int((obj.old_price - obj.price) / obj.old_price * 100)
            return format_html(
                '<span style="color: red; font-weight: bold;">{} ₽</span> '
                '<del style="color: gray;">{} ₽</del> '
                '<span style="color: green;">(-{}%)</span>',
                obj.price, obj.old_price, discount_percent
            )
        return format_html('<span style="font-weight: bold;">{} ₽</span>', obj.price)

    @admin.display(description='Серебро')
    def silver_info(self, obj: Product) -> str:
        """
        Отображает информацию о серебре товара.

        Args:
            obj (Product): Объект товара

        Returns:
            str: HTML с информацией о типе и пробе
        """
        silver_type_display = obj.get_silver_type_display()
        fineness_display = obj.get_fineness_display()

        color = '#666'
        if 'sterling' in obj.silver_type:
            color = '#2c3e50'
        elif 'oxidized' in obj.silver_type:
            color = '#34495e'
        elif 'rhodium' in obj.silver_type:
            color = '#7f8c8d'
        elif 'black' in obj.silver_type:
            color = '#2c3e50'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span><br>'
            '<span style="color: gray; font-size: 0.9em;">{}</span>',
            color, silver_type_display, fineness_display
        )

    @admin.display(description='Полное описание')
    def full_silver_info(self, obj: Product) -> str:
        """
        Отображает полную информацию о серебре товара.

        Args:
            obj (Product): Объект товара

        Returns:
            str: HTML с информацией о типе, пробе, весе, размере
        """
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">'
            '<strong>Тип:</strong> {}<br>'
            '<strong>Проба:</strong> {}<br>'
            '<strong>Вес:</strong> {} г<br>'
            '<strong>Размер:</strong> {}</div>',
            obj.get_silver_type_display(),
            obj.get_fineness_display(),
            obj.weight,
            obj.size or 'Не указан'
        )

    @admin.display(description='Превью фото')
    def image_preview(self, obj: Product) -> str:
        """
        Отображает превью главного фото товара.

        Args:
            obj (Product): Объект товара

        Returns:
            str: HTML с изображением или '-'
        """
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px; border-radius: 5px;" />',
                obj.image.url
            )
        return '-'

    @admin.display(description='Все фото')
    def images_preview(self, obj: Product) -> str:
        """
        Отображает все фото товара в виде миниатюр.

        Args:
            obj (Product): Объект товара

        Returns:
            str: HTML с изображениями или текст
        """
        images_html = '<div style="display: flex; gap: 10px; flex-wrap: wrap;">'
        if obj.image:
            images_html += format_html(
                '<div><img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 5px;" /><br><small>Главное</small></div>',
                obj.image.url
            )
        if obj.image_2:
            images_html += format_html(
                '<div><img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 5px;" /></div>',
                obj.image_2.url
            )
        if obj.image_3:
            images_html += format_html(
                '<div><img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 5px;" /></div>',
                obj.image_3.url
            )
        if obj.image_4:
            images_html += format_html(
                '<div><img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 5px;" /></div>',
                obj.image_4.url
            )
        if obj.image_5:
            images_html += format_html(
                '<div><img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 5px;" /></div>',
                obj.image_5.url
            )
        images_html += '</div>'

        if obj.images_count == 0:
            return 'Нет фотографий'
        return format_html(images_html)

    @admin.display(description='Кол-во фото')
    def images_count_display(self, obj: Product) -> str:
        """
        Отображает количество фото товара.

        Args:
            obj (Product): Объект товара

        Returns:
            str: HTML с количеством фото
        """
        count = obj.images_count
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        elif count == 1:
            return format_html('<span style="color: orange;">{} (нет доп.)</span>', count)
        else:
            return format_html('<span style="color: green;">{} ({} доп.)</span>', count, count - 1)

    @admin.display(description='Доступно')
    def available_quantity_display(self, obj: Product) -> str:
        """
        Отображает доступное количество товара.

        Args:
            obj (Product): Объект товара

        Returns:
            str: HTML с информацией о наличии
        """
        available = obj.available_quantity
        if available <= 0:
            return format_html('<span style="color: red; font-weight: bold;">Нет в наличии</span>')
        elif available < 10:
            return format_html('<span style="color: orange; font-weight: bold;">Осталось {} шт</span>', available)
        elif available < 50:
            return format_html('<span style="color: green;">В наличии {} шт</span>', available)
        else:
            return format_html('<span style="color: blue;">В наличии {} шт</span>', available)

    @admin.display(boolean=True, description='Скидка')
    def has_discount_display(self, obj: Product) -> bool:
        """
        Проверяет наличие скидки у товара.

        Args:
            obj (Product): Объект товара

        Returns:
            bool: True если есть скидка, иначе False
        """
        return obj.has_discount

    @admin.display(description='Статус')
    def stock_status(self, obj: Product) -> str:
        """
        Возвращает статус наличия товара.

        Args:
            obj (Product): Объект товара

        Returns:
            str: Статус наличия
        """
        available = obj.available_quantity
        if available <= 0:
            return 'Нет в наличии'
        elif available < 10:
            return 'Мало'
        return 'В наличии'

    @admin.display(description='Камни')
    def stones_display(self, obj: Product) -> str:
        """
        Отображает информацию о камнях товара.

        Args:
            obj (Product): Объект товара

        Returns:
            str: Информация о камнях
        """
        if not obj.stones:
            return 'Без камней'

        stone_display = obj.get_stone_type_display()
        if obj.stone_weight:
            return f"{stone_display} ({obj.stone_weight} кар)"
        return stone_display

    @admin.action(description='Применить скидку 10 процентов к выбранным товарам')
    def apply_discount(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        """
        Применяет скидку 10% к выбранным товарам.

        Args:
            request (HttpRequest): HTTP запрос
            queryset (QuerySet[Product]): Выбранные товары
        """
        for product in queryset:
            if not product.old_price:
                product.old_price = product.price
            product.price = product.price * Decimal('0.9')
            product.save()
        self.message_user(request, f'Скидка применена к {queryset.count()} товарам')

    @admin.action(description='Увеличить цену на 5 процентов')
    def increase_price(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        """
        Увеличивает цену на 5% для выбранных товаров.

        Args:
            request (HttpRequest): HTTP запрос
            queryset (QuerySet[Product]): Выбранные товары
        """
        for product in queryset:
            product.price = product.price * Decimal('1.05')
            product.save()
        self.message_user(request, f'Цена увеличена для {queryset.count()} товарам')


class WishlistAdmin(admin.ModelAdmin):
    """
    Настройки отображения избранного в админке.
    """
    list_display: list = ['id', 'user', 'product', 'added_at']
    list_filter: list = ['added_at']
    search_fields: list = ['user__email', 'product__name']
    readonly_fields: list = ['added_at']


class UserAdmin(admin.ModelAdmin):
    """
    Настройки отображения пользователя в админке.
    """
    list_display: list = ['email', 'first_name', 'last_name', 'phone', 'birthday', 'bonus_points', 'is_staff', 'is_active']
    list_filter: list = ['is_staff', 'is_active']
    search_fields: list = ['email', 'first_name', 'last_name', 'phone']
    fieldsets: tuple = (
        ('Личная информация', {
            'fields': ('email', 'first_name', 'last_name', 'phone', 'birthday', 'bonus_points')
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Важные даты', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields: list = ['last_login', 'date_joined']


class PromoCodeAdmin(admin.ModelAdmin):
    """
    Настройки отображения промокодов в админке.
    """
    list_display: list = ['code', 'discount_display', 'min_order_amount', 'valid_from', 'valid_to', 'is_valid', 'used_count']
    list_filter: list = ['discount_type', 'is_active', 'only_new_users']
    search_fields: list = ['code']
    filter_horizontal: list = ['applicable_categories']
    fieldsets: tuple = (
        ('Основная информация', {
            'fields': ('code', 'discount_type', 'discount_value', 'min_order_amount', 'max_discount_amount')
        }),
        ('Даты действия', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Ограничения', {
            'fields': ('usage_limit', 'user_limit', 'only_new_users')
        }),
        ('Статус', {
            'fields': ('is_active', 'applicable_categories')
        }),
    )

    def discount_display(self, obj: PromoCode) -> str:
        """
        Отображает скидку промокода.

        Args:
            obj (PromoCode): Объект промокода

        Returns:
            str: Строковое представление скидки
        """
        return obj.discount_display
    discount_display.short_description = 'Скидка'

    def is_valid(self, obj: PromoCode) -> bool:
        """
        Проверяет активность промокода.

        Args:
            obj (PromoCode): Объект промокода

        Returns:
            bool: True если активен, иначе False
        """
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = 'Активен'


class PromoCodeUsageAdmin(admin.ModelAdmin):
    """
    Настройки отображения использований промокодов в админке.
    """
    list_display: list = ['user', 'promo_code', 'order', 'discount_amount', 'used_at']
    list_filter: list = ['used_at']
    search_fields: list = ['user__email', 'promo_code__code', 'order__order_number']
    readonly_fields: list = ['used_at']


class CollectionAdmin(admin.ModelAdmin):
    """
    Настройки отображения коллекций в админке.
    """
    list_display: list = ['name', 'slug', 'order', 'is_active', 'products_count', 'image_preview']
    list_filter: list = ['is_active', 'created_at']
    search_fields: list = ['name', 'description']
    prepopulated_fields: dict = {'slug': ('name',)}
    list_editable: list = ['order', 'is_active']

    fieldsets: tuple = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'description', 'image')
        }),
        ('Настройки отображения', {
            'fields': ('order', 'is_active')
        }),
    )

    def products_count(self, obj: Collection) -> int:
        """
        Возвращает количество товаров в коллекции.

        Args:
            obj (Collection): Объект коллекции

        Returns:
            int: Количество товаров
        """
        return obj.products.count()
    products_count.short_description = 'Товаров в коллекции'

    def image_preview(self, obj: Collection) -> str:
        """
        Отображает превью изображения коллекции.

        Args:
            obj (Collection): Объект коллекции

        Returns:
            str: HTML с изображением или '-'
        """
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; border-radius: 5px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Превью'


# Регистрация всех моделей в админке
admin.site.register(Collection, CollectionAdmin)
admin.site.register(PromoCode, PromoCodeAdmin)
admin.site.register(PromoCodeUsage, PromoCodeUsageAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Category)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Wishlist, WishlistAdmin)