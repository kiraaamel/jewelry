import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jewelryproject.settings')
django.setup()

from django.core import serializers
from shop.models import User, Category, Product, Cart, CartItem, Order, OrderItem, Review, Wishlist

def import_model(model, filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = f.read()
        objects = list(serializers.deserialize('json', data))
        for obj in objects:
            obj.save()
        print(f'✅ Импортировано {model.__name__}: {len(objects)} записей')
    except FileNotFoundError:
        print(f'⚠️ Файл {filename} не найден, пропускаем')

print("📥 Начинаю импорт данных...")

import_model(User, 'users.json')
import_model(Category, 'categories.json')
import_model(Product, 'products.json')
import_model(Cart, 'carts.json')
import_model(CartItem, 'cart_items.json')
import_model(Order, 'orders.json')
import_model(OrderItem, 'order_items.json')
import_model(Review, 'reviews.json')
import_model(Wishlist, 'wishlists.json')

print("\n🎉 Готово! Данные импортированы в PostgreSQL.")