from django.contrib import admin
from .models import (
    User, Category, Brand, Product, ProductImage, 
    Cart, CartItem, Order, OrderItem, Review, Wishlist,
    Promotion, Payment, Employee
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
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'price', 'quantity', 'total_price']

class OrderAdmin(admin.ModelAdmin):
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
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'added_at', 'total_price']

class CartAdmin(admin.ModelAdmin):
    inlines = [CartItemInline]
    list_display = ['id', 'user', 'session_key', 'total_items', 'total_price', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['user__email', 'session_key']
    readonly_fields = ['created_at', 'updated_at']

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ['name', 'price', 'stock_quantity', 'category', 'created_at']
    list_filter = ['category', 'brand', 'metal', 'stones']
    search_fields = ['name', 'description']

class WishlistAdmin(admin.ModelAdmin):
    """
    Настройки отображения избранного в админке.
    """
    list_display = ['id', 'user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__email', 'product__name']
    readonly_fields = ['added_at']

class PromotionAdmin(admin.ModelAdmin):
    """
    Настройки отображения акций в админке.
    """
    list_display = ['name', 'discount_type', 'discount_value', 'start_date', 'end_date', 'is_active']
    list_filter = ['discount_type', 'is_active', 'start_date', 'end_date']
    search_fields = ['name', 'description']
    filter_horizontal = ['products', 'categories']  # удобный виджет для ManyToMany полей
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Скидка', {
            'fields': ('discount_type', 'discount_value')
        }),
        ('Срок действия', {
            'fields': ('start_date', 'end_date')
        }),
        ('Применяется к', {
            'fields': ('products', 'categories'),
            'classes': ('collapse',)
        }),
    )

class PaymentAdmin(admin.ModelAdmin):
    """
    Настройки отображения платежей в админке.
    """
    list_display = ['id', 'order', 'amount', 'method', 'status', 'created_at']
    list_filter = ['status', 'method', 'created_at']
    search_fields = ['order__order_number', 'transaction_id']
    readonly_fields = ['created_at']

class EmployeeAdmin(admin.ModelAdmin):
    """
    Настройки отображения сотрудников в админке.
    """
    list_display = ['name', 'position', 'email', 'phone', 'is_active']
    list_filter = ['position', 'is_active']
    search_fields = ['name', 'email', 'phone']
# Регистрируем все модели
admin.site.register(User)
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Review, ReviewAdmin)  
admin.site.register(Wishlist, WishlistAdmin)
admin.site.register(Promotion, PromotionAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Employee, EmployeeAdmin)