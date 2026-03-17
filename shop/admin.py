from django.contrib import admin
from .models import User, Category, Brand, Product, ProductImage, Cart, CartItem

class CartItemInline(admin.TabularInline):
    """
    Встроенная форма для элементов корзины.
    """
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'added_at']

class CartAdmin(admin.ModelAdmin):
    """
    Настройки отображения корзины в админке.
    """
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
admin.site.register(Cart, CartAdmin)  # используем специальный класс
admin.site.register(CartItem)  # можно оставить простую регистрацию