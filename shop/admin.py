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
    extra = 0
    readonly_fields = ['product_name', 'price', 'quantity', 'total_price']


class OrderAdmin(admin.ModelAdmin):
    """
    Настройки отображения заказа в админке.
    """
    inlines = [OrderItemInline]
    list_display = [
        'order_number', 'user', 'created_at', 'status', 
        'total_price', 'delivery_method'
    ]
    list_filter = ['status', 'delivery_method', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__email', 'delivery_address']
    readonly_fields = ['order_number', 'created_at', 'total_price']
    list_editable = ['status']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order_number', 'user', 'status', 'total_price', 'created_at')
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