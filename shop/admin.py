from django.contrib import admin
from .models import User, Category, Brand, Product, ProductImage

class ProductImageInline(admin.TabularInline):
    """
    Встроенная форма для изображений товара (позволяет добавлять 
    изображения прямо в карточке товара).
    """
    model = ProductImage
    extra = 1  

class ProductAdmin(admin.ModelAdmin):
    """
    Настройки отображения товара в админке.
    """
    inlines = [ProductImageInline] 
    list_display = ['name', 'price', 'stock_quantity', 'category', 'created_at']
    list_filter = ['category', 'brand', 'metal', 'stones']
    search_fields = ['name', 'description']

# Регистрируем все модели
admin.site.register(User)
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Product, ProductAdmin)