from django.contrib import admin
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
    """
    Настройки отображения товара в админке.
    """
    list_display = ['name', 'price', 'stock_quantity', 'category', 'metal', 'stones', 'created_at']
    list_filter = ['category', 'metal', 'stones', 'created_at']
    search_fields = ['name', 'description', 'collection']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Цены и наличие', {
            'fields': ('price', 'old_price', 'stock_quantity', 'reserved_quantity')
        }),
        ('Характеристики', {
            'fields': ('metal', 'fineness', 'weight', 'size', 'stones', 'stone_type', 'collection')
        }),
        ('Изображение', {
            'fields': ('image',)
        }),
        ('Мета-информация', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


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