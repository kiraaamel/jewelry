from django.contrib import admin
from .models import (
    User, Category, Brand, Product, ProductImage, 
    Cart, CartItem, Order, OrderItem  # добавили Order и OrderItem
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
    list_editable = ['status']  # можно менять статус прямо из списка
    
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
            'classes': ('collapse',)  # сворачиваемый блок
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

# Регистрируем все модели
admin.site.register(User)
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem)
admin.site.register(Order, OrderAdmin)  # используем специальный класс
admin.site.register(OrderItem)