from django.contrib import admin
from django.utils.html import format_html 
from .models import (
    User, Category, Product, 
    Cart, CartItem, Order, OrderItem, Review, Wishlist
)


class ReviewAdmin(admin.ModelAdmin):
    """
    Настройки отображения отзывов в админке.
    """
    list_display = ['id', 'user', 'product', 'rating', 'created_at', 'moderated']
    list_filter = ['rating', 'moderated', 'created_at']
    search_fields = ['user__email', 'product__name', 'comment']
    list_editable = ['moderated']
    readonly_fields = ['created_at']
    
    fieldsets = (
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
    extra = 1
    fields = ['product', 'quantity', 'item_total_display']
    readonly_fields = ['item_total_display']
    
    def item_total_display(self, obj):
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


class OrderAdmin(admin.ModelAdmin):
    """
    Настройки отображения заказа в админке.
    total_price не вводится, а рассчитывается автоматически.
    """
    inlines = [OrderItemInline]
    list_display = [
        'order_number', 'user', 'created_at', 'status', 
        'total_price_display', 'delivery_method'
    ]
    list_filter = ['status', 'delivery_method', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__email', 'delivery_address']
    readonly_fields = ['order_number', 'created_at', 'total_price_display']
    list_editable = ['status']
    exclude = ['total_price']  # ← скрываем поле total_price из формы
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order_number', 'user', 'status', 'total_price_display', 'created_at')
        }),
        ('Доставка', {
            'fields': ('delivery_address', 'delivery_method', 'delivered_at')
        }),
        ('Оплата', {
            'fields': ('payment_method',)
        }),
        ('Дополнительно', {
            'fields': ('gift_wrap', 'gift_message', 'comment'),
            'classes': ('collapse',)
        }),
    )
    
    def total_price_display(self, obj):
        """
        Рассчитывает общую стоимость заказа из позиций.
        """
        if obj.pk:
            total = 0
            for item in obj.items.all():
                if item.product and item.quantity:
                    total += item.product.price * item.quantity
                elif item.price and item.quantity:
                    # fallback: если нет product, используем сохранённую цену
                    total += item.price * item.quantity
            return f"{total} ₽"
        return "0 ₽"
    total_price_display.short_description = "Общая стоимость"
    
    def save_related(self, request, form, formsets, change):
        """
        Сохраняем позиции и обновляем total_price в заказе.
        """
        super().save_related(request, form, formsets, change)
        
        order = form.instance
        
        # Заполняем поля позиций из товара
        for item in order.items.all():
            if item.product:
                # Название товара
                if not item.product_name or item.product_name != item.product.name:
                    item.product_name = item.product.name
                # Цена из товара
                if not item.price or item.price != item.product.price:
                    item.price = item.product.price
                item.save()
        
        # Вычисляем и сохраняем общую сумму заказа
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
    extra = 0
    readonly_fields = ['product', 'quantity', 'added_at', 'total_price']


class CartAdmin(admin.ModelAdmin):
    """
    Настройки отображения корзины в админке.
    """
    inlines = [CartItemInline]
    list_display = ['id', 'user', 'session_key', 'total_items', 'total_price', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['user__email', 'session_key']
    readonly_fields = ['created_at', 'updated_at']


class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'price_display', 
                   'silver_info', 'weight', 'stock_status', 'has_discount_display', 
                   'stones_display', 'image_preview', 'images_count_display', 'created_at']
    list_filter = ['category', 'silver_type', 'fineness', 'stones', 'created_at', 'collection']
    list_display_links = ['name']
    search_fields = ['name', 'description', 'collection']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'available_quantity_display', 
                      'full_silver_info', 'images_preview']
    raw_id_fields = ['created_by', 'category']
    date_hierarchy = 'created_at'
    
    fieldsets = (
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
    
    @admin.display(description='Цена')
    def price_display(self, obj):
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
    def silver_info(self, obj):
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
    def full_silver_info(self, obj):
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
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px; border-radius: 5px;" />',
                obj.image.url
            )
        return '-'
    
    @admin.display(description='Все фото')
    def images_preview(self, obj):
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
    def images_count_display(self, obj):
        count = obj.images_count
        if count == 0:
            return format_html('<span style="color: red;">0</span>')
        elif count == 1:
            return format_html('<span style="color: orange;">{} (нет доп.)</span>', count)
        else:
            return format_html('<span style="color: green;">{} ({} доп.)</span>', count, count - 1)
    
    @admin.display(description='Доступно')
    def available_quantity_display(self, obj):
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
    def has_discount_display(self, obj):
        return obj.has_discount
    
    @admin.display(description='Статус')
    def stock_status(self, obj):
        available = obj.available_quantity
        if available <= 0:
            return 'Нет в наличии'
        elif available < 10:
            return 'Мало'
        return 'В наличии'
    
    @admin.display(description='Камни')
    def stones_display(self, obj):
        if not obj.stones:
            return 'Без камней'
        
        stone_display = obj.get_stone_type_display()
        if obj.stone_weight:
            return f"{stone_display} ({obj.stone_weight} кар)"
        return stone_display
    
    actions = ['apply_discount', 'increase_price']
    
    @admin.action(description='Применить скидку 10 процентов к выбранным товарам')
    def apply_discount(self, request, queryset):
        for product in queryset:
            if not product.old_price:
                product.old_price = product.price
            product.price = product.price * Decimal('0.9')
            product.save()
        self.message_user(request, f'Скидка применена к {queryset.count()} товарам')
    
    @admin.action(description='Увеличить цену на 5 процентов')
    def increase_price(self, request, queryset):
        for product in queryset:
            product.price = product.price * Decimal('1.05')
            product.save()
        self.message_user(request, f'Цена увеличена для {queryset.count()} товаров')


class WishlistAdmin(admin.ModelAdmin):
    """
    Настройки отображения избранного в админке.
    """
    list_display = ['id', 'user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__email', 'product__name']
    readonly_fields = ['added_at']


class UserAdmin(admin.ModelAdmin):
    """
    Настройки отображения пользователя в админке.
    """
    list_display = ['email', 'first_name', 'last_name', 'phone', 'bonus_points', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    fieldsets = (
        ('Личная информация', {
            'fields': ('email', 'first_name', 'last_name', 'phone', 'bonus_points')
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Важные даты', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['last_login', 'date_joined']


# Регистрируем все модели
admin.site.register(User, UserAdmin)
admin.site.register(Category)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Wishlist, WishlistAdmin)