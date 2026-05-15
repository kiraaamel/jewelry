"""
Административная панель для интернет-магазина Argentic Jewelry.

Содержит настройки отображения и управления всеми моделями:
пользователи, товары, категории, заказы, отзывы, корзины, промокоды, коллекции.
"""

from typing import Any, Optional
from decimal import Decimal
from datetime import datetime
from io import BytesIO
from django.contrib import admin
from django.db.models import QuerySet, Sum, Count
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.shortcuts import render
from django.template.loader import get_template
from django.urls import path

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
    
    actions: list = ['mark_as_moderated']

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

    @admin.action(description='Отметить выбранные отзывы как промодерированные')
    def mark_as_moderated(self, request: HttpRequest, queryset: QuerySet[Review]) -> None:
        """
        Отмечает выбранные отзывы как промодерированные.
        """
        updated = queryset.update(moderated=True)
        self.message_user(request, f'{updated} отзывов отмечено как промодерированные')


class OrderItemInline(admin.TabularInline):
    """
    Встроенная форма для позиций заказа.
    """
    model = OrderItem
    extra: int = 1
    fields: list = ['product', 'quantity', 'price', 'item_total_display']
    readonly_fields: list = ['item_total_display']
    ordering = ['-id']

    def item_total_display(self, obj: OrderItem) -> str:
        """
        Рассчитывает стоимость позиции.
        """
        if obj.pk and obj.product and obj.quantity:
            total = obj.product.price * obj.quantity
            return f"{total} ₽"
        elif obj.pk and obj.price and obj.quantity:
            total = obj.price * obj.quantity
            return f"{total} ₽"
        return "0 ₽"
    item_total_display.short_description = "Стоимость"

class OrderItemAdmin(admin.ModelAdmin):
    """
    Настройки отображения позиций заказа в админке.
    """
    list_display: list = ['id', 'order', 'product', 'product_name', 'quantity', 'price', 'total_price_display']
    list_filter: list = ['order__created_at']
    search_fields: list = ['product__name', 'product_name', 'order__order_number']
    readonly_fields: list = ['total_price_display']
    ordering: list = ['-id']
    
    def total_price_display(self, obj: OrderItem) -> str:
        if obj.price and obj.quantity:
            total = obj.price * obj.quantity
            return f"{total} ₽"
        return "0 ₽"
    total_price_display.short_description = "Стоимость"

class OrderAdmin(admin.ModelAdmin):
    """
    Настройки отображения заказа в админке.
    """
    inlines: list = [OrderItemInline]
    list_display: list = [
        'order_number', 'user', 'created_at', 'status',
        'total_price_display', 'delivery_method', 'delivery_date', 'delivery_time', 'pickup_code'
    ]
    list_filter: list = ['status', 'delivery_method', 'payment_method', 'created_at']
    search_fields: list = ['order_number', 'user__email', 'delivery_address']
    readonly_fields: list = ['order_number', 'created_at', 'total_price_display', 'pickup_code', 'code_generated_at']
    list_editable: list = ['status']
    exclude: list = ['total_price']
    date_hierarchy: str = 'created_at'

    actions: list = ['generate_order_report_pdf', 'export_orders_csv']

    fieldsets: tuple = (
        ('Основная информация', {
            'fields': ('order_number', 'user', 'status', 'total_price_display', 'created_at')
        }),
        ('Доставка', {
            'fields': ('delivery_address', 'delivery_method', 'delivery_date', 'delivery_time', 'delivered_at')
        }),
        ('Получение', {
            'fields': ('pickup_code', 'code_generated_at'),
            'classes': ('collapse',)
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

    def save_model(self, request: HttpRequest, obj: Order, form, change: bool) -> None:
        """
        При изменении статуса автоматически обновляет даты.
        """
        if change:
            original = Order.objects.get(pk=obj.pk)
            
            if original.status != Order.Status.DELIVERED and obj.status == Order.Status.DELIVERED:
                obj.delivered_at = timezone.now()
            
            if original.status != Order.Status.RECEIVED and obj.status == Order.Status.RECEIVED:
                obj.delivered_at = timezone.now()
                if not obj.pickup_code:
                    obj.pickup_code = self.generate_pickup_code()
                    obj.code_generated_at = timezone.now()
        
        super().save_model(request, obj, form, change)

    def generate_pickup_code(self) -> str:
        """
        Генерирует случайный 6-значный код для получения заказа.
        """
        import random
        return str(random.randint(100000, 999999))

    @admin.action(description='Создать PDF отчёт по выбранным заказам')
    def generate_order_report_pdf(self, request: HttpRequest, queryset: QuerySet[Order]) -> None:
        """
        Генерирует PDF отчёт по выбранным заказам используя reportlab.
        """
        if not queryset.exists():
            self.message_user(request, 'Не выбрано ни одного заказа', level='ERROR')
            return
        
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase.pdfmetrics import registerFont
        import os
        
        # Регистрируем шрифт для русских букв (используем стандартный)
        try:
            # Пробуем зарегистрировать Helvetica (она есть везде)
            registerFont(TTFont('Helvetica', '/System/Library/Fonts/Helvetica.ttc'))
            font_name = 'Helvetica'
        except:
            font_name = 'Helvetica'
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="orders_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        
        # Создаём стили
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=16,
            alignment=1,
            spaceAfter=20
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=12,
            spaceAfter=10
        )
        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=9,
            leading=12
        )
        
        elements = []
        
        # Заголовок
        elements.append(Paragraph("Отчет по заказам", title_style))
        elements.append(Spacer(1, 10))
        
        # Общая статистика
        total_sum = queryset.aggregate(total=Sum('total_price'))['total'] or 0
        stats_data = [
            [f"Всего заказов: {queryset.count()}", f"Общая сумма: {total_sum:.2f} RUB"]
        ]
        stats_table = Table(stats_data, colWidths=[90*mm, 90*mm])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 20))
        
        for order in queryset:
            # Заголовок заказа
            elements.append(Paragraph(f"Заказ No {order.order_number}", header_style))
            
            # Информация о заказе
            info_data = [
                ["Дата создания:", order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else "-"],
                ["Статус:", order.get_status_display()],
                ["Общая стоимость:", f"{order.total_price} RUB"],
                ["Способ доставки:", self.get_delivery_method_ru(order.delivery_method)],
                ["Адрес доставки:", order.delivery_address or "-"],
            ]
            if order.delivered_at:
                info_data.append(["Дата получения:", order.delivered_at.strftime("%d.%m.%Y %H:%M")])
            if order.comment:
                info_data.append(["Комментарий:", order.comment[:50]])
            
            info_table = Table(info_data, colWidths=[45*mm, 130*mm])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(info_table)
            
            elements.append(Spacer(1, 8))
            
            # Товары в заказе
            items_data = [["Товар", "Кол-во", "Цена", "Сумма"]]
            for item in order.items.all():
                items_data.append([
                    item.product_name[:40] + "..." if len(item.product_name) > 40 else item.product_name,
                    str(item.quantity),
                    f"{item.price:.0f} RUB",
                    f"{item.price * item.quantity:.0f} RUB"
                ])
            
            items_table = Table(items_data, colWidths=[80*mm, 30*mm, 40*mm, 40*mm])
            items_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(items_table)
            elements.append(Spacer(1, 15))
        
        doc.build(elements)
        self.message_user(request, f'PDF отчёт создан для {queryset.count()} заказов')
        return response

    @admin.action(description='Экспортировать выбранные заказы в CSV')
    def export_orders_csv(self, request: HttpRequest, queryset: QuerySet[Order]) -> None:
        """
        Экспортирует выбранные заказы в CSV файл.
        """
        import csv
        
        if not queryset.exists():
            self.message_user(request, 'Не выбрано ни одного заказа', level='ERROR')
            return
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="orders_export_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Номер заказа', 'Пользователь', 'Дата создания', 'Статус',
            'Способ доставки', 'Адрес доставки', 'Способ оплаты', 
            'Общая стоимость', 'Дата получения'
        ])
        
        for order in queryset:
            writer.writerow([
                order.order_number,
                order.user.email if order.user else '-',
                order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else '-',
                order.get_status_display(),
                self.get_delivery_method_ru(order.delivery_method),
                order.delivery_address,
                self.get_payment_method_ru(order.payment_method),
                f"{order.total_price}",
                order.delivered_at.strftime("%d.%m.%Y %H:%M") if order.delivered_at else '-'
            ])
        
        self.message_user(request, f'Экспортировано {queryset.count()} заказов')
        return response

    def get_delivery_method_ru(self, method: str) -> str:
        """
        Возвращает русское название способа доставки.
        """
        methods = {
            'courier': 'Курьер',
            'pickup': 'Самовывоз',
            'post': 'Почта'
        }
        return methods.get(method, method)

    def get_payment_method_ru(self, method: str) -> str:
        """
        Возвращает русское название способа оплаты.
        """
        methods = {
            'card': 'Карта онлайн',
            'sbp': 'СБП',
            'cash': 'Наличные'
        }
        return methods.get(method, method)


class CartItemInline(admin.TabularInline):
    """
    Встроенная форма для элементов корзины.
    """
    model = CartItem
    extra: int = 0
    fields: list = ['product', 'quantity', 'size', 'added_at', 'total_price']
    readonly_fields: list = ['added_at', 'total_price']
    ordering = ['-added_at']


class CartAdmin(admin.ModelAdmin):
    """
    Настройки отображения корзины в админке.
    """
    inlines: list = [CartItemInline]
    list_display: list = ['id', 'user', 'session_key', 'total_items', 'total_price', 'updated_at']
    list_filter: list = ['updated_at', 'created_at']
    search_fields: list = ['user__email', 'session_key']
    readonly_fields: list = ['created_at', 'updated_at']
    date_hierarchy: str = 'created_at' 

class CartItemAdmin(admin.ModelAdmin):
    """
    Настройки отображения элементов корзины в админке.
    """
    list_display: list = ['id', 'cart', 'product', 'quantity', 'size', 'added_at', 'total_price']
    list_filter: list = ['added_at', 'size']
    search_fields: list = ['product__name', 'cart__user__email', 'cart__session_key']
    readonly_fields: list = ['added_at', 'total_price']
    ordering: list = ['-added_at']
    date_hierarchy: str = 'added_at'

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
            'fields': ('name', 'slug', 'description', 'category', 'collection')
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
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions: list = ['apply_discount', 'increase_price', 'duplicate_product']

    @admin.display(description='Цена')
    def price_display(self, obj: Product) -> str:
        """
        Отображает цену товара со скидкой, если есть.
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
        """
        return obj.has_discount

    @admin.display(description='Статус')
    def stock_status(self, obj: Product) -> str:
        """
        Возвращает статус наличия товара.
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
        """
        for product in queryset:
            product.price = product.price * Decimal('1.05')
            product.save()
        self.message_user(request, f'Цена увеличена для {queryset.count()} товарам')

    @admin.action(description='Копировать выбранные товары')
    def duplicate_product(self, request: HttpRequest, queryset: QuerySet[Product]) -> None:
        """
        Создаёт копии выбранных товаров.
        """
        from django.utils.text import slugify
        import copy
        
        count = 0
        for product in queryset:
            product_copy = copy.copy(product)
            product_copy.id = None
            product_copy.name = f"{product.name} (копия)"
            product_copy.slug = slugify(f"{product.slug}-copy-{timezone.now().timestamp()}")
            product_copy.stock_quantity = 0
            product_copy.save()
            
            if product.image:
                product_copy.image = product.image
            if product.image_2:
                product_copy.image_2 = product.image_2
            if product.image_3:
                product_copy.image_3 = product.image_3
            if product.image_4:
                product_copy.image_4 = product.image_4
            if product.image_5:
                product_copy.image_5 = product.image_5
            product_copy.save()
            count += 1
        
        self.message_user(request, f'Создано {count} копий товаров')


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
    list_filter: list = ['is_staff', 'is_active', 'is_superuser']
    search_fields: list = ['email', 'first_name', 'last_name', 'phone']
    
    actions: list = ['add_bonus_points', 'make_active', 'make_inactive']
    
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

    @admin.action(description='Добавить 100 бонусных баллов выбранным пользователям')
    def add_bonus_points(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        """
        Добавляет 100 бонусных баллов выбранным пользователям.
        """
        for user in queryset:
            user.bonus_points += 100
            user.save()
        self.message_user(request, f'Добавлено 100 бонусов {queryset.count()} пользователям')

    @admin.action(description='Активировать выбранных пользователей')
    def make_active(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        """
        Активирует выбранных пользователей.
        """
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано {updated} пользователей')

    @admin.action(description='Деактивировать выбранных пользователей')
    def make_inactive(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        """
        Деактивирует выбранных пользователей.
        """
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано {updated} пользователей')


class PromoCodeAdmin(admin.ModelAdmin):
    """
    Настройки отображения промокодов в админке.
    """
    list_display: list = ['code', 'discount_display', 'min_order_amount', 'valid_from', 'valid_to', 'is_valid', 'used_count']
    list_filter: list = ['discount_type', 'is_active', 'only_new_users']
    search_fields: list = ['code']
    filter_horizontal: list = ['applicable_categories']
    
    actions: list = ['activate_promocodes', 'deactivate_promocodes']
    
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
        """
        return obj.discount_display
    discount_display.short_description = 'Скидка'

    def is_valid(self, obj: PromoCode) -> bool:
        """
        Проверяет активность промокода.
        """
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = 'Активен'

    @admin.action(description='Активировать выбранные промокоды')
    def activate_promocodes(self, request: HttpRequest, queryset: QuerySet[PromoCode]) -> None:
        """
        Активирует выбранные промокоды.
        """
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано {updated} промокодов')

    @admin.action(description='Деактивировать выбранные промокоды')
    def deactivate_promocodes(self, request: HttpRequest, queryset: QuerySet[PromoCode]) -> None:
        """
        Деактивирует выбранные промокоды.
        """
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано {updated} промокодов')


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
        """
        return obj.products.count()
    products_count.short_description = 'Товаров в коллекции'

    def image_preview(self, obj: Collection) -> str:
        """
        Отображает превью изображения коллекции.
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
admin.site.register(Order, OrderAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Wishlist, WishlistAdmin)
admin.site.register(CartItem, CartItemAdmin)
admin.site.register(OrderItem, OrderItemAdmin)