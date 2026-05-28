"""
Тесты для API интернет-магазина Argentic Jewelry

Тестируются основные эндпоинты: товары, категории, корзина, заказы, отзывы, избранное, аутентификация.
"""

import json
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone

from shop.models import (
    Category, Product, Collection, Cart, CartItem,
    Order, OrderItem, Review, Wishlist, PromoCode, PromoCodeUsage, ProductVariant
)

User = get_user_model()


class AuthenticationTests(TestCase):
    """Тесты для аутентификации и регистрации"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.me_url = '/api/auth/me/'
        
    def test_01_user_registration_success(self):
        """Тест успешной регистрации нового пользователя"""
        data = {
            'email': 'newuser@example.com',
            'first_name': 'Тест',
            'last_name': 'Пользователь',
            'phone': '+79991234567',
            'password': 'TestPass123!',
            'password2': 'TestPass123!'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.first().email, 'newuser@example.com')
    
    def test_02_user_registration_password_mismatch(self):
        """Тест регистрации с несовпадающими паролями"""
        data = {
            'email': 'newuser@example.com',
            'password': 'TestPass123!',
            'password2': 'DifferentPass123!'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_03_user_registration_duplicate_email(self):
        """Тест регистрации с уже существующим email"""
        User.objects.create_user(email='existing@example.com', password='pass123')
        data = {
            'email': 'existing@example.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_04_user_login_success(self):
        """Тест успешного входа в систему"""
        User.objects.create_user(email='test@example.com', password='TestPass123!')
        data = {'email': 'test@example.com', 'password': 'TestPass123!'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_05_user_login_invalid_credentials(self):
        """Тест входа с неверными данными"""
        User.objects.create_user(email='test@example.com', password='TestPass123!')
        data = {'email': 'test@example.com', 'password': 'WrongPassword!'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProductTests(TestCase):
    """Тесты для товаров и каталога"""
    
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Кольца', slug='rings')
        self.collection = Collection.objects.create(name='Весенняя коллекция', slug='spring', is_active=True)
        
        self.product = Product.objects.create(
            name='Серебряное кольцо',
            slug='silver-ring',
            description='Красивое серебряное кольцо',
            price=Decimal('15000.00'),
            category=self.category,
            collection=self.collection,
            is_active=True
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='17',
            stock_quantity=10,
            reserved_quantity=0
        )
        
    def test_06_get_products_list(self):
        """Тест получения списка товаров"""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if 'results' in response.data:
            self.assertTrue(len(response.data['results']) > 0)
        else:
            self.assertTrue(len(response.data) > 0)
    
    def test_07_get_product_detail(self):
        """Тест получения детальной информации о товаре"""
        response = self.client.get(f'/api/products/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Серебряное кольцо')
        self.assertEqual(str(response.data['price']), '15000.00')
        self.assertIn('variants', response.data)
        self.assertEqual(len(response.data['variants']), 1)
        self.assertEqual(response.data['variants'][0]['size'], '17')
    
    def test_08_filter_products_by_price(self):
        """Тест фильтрации товаров по цене"""
        product2 = Product.objects.create(
            name='Дорогое кольцо',
            slug='expensive-ring',
            description='Дорогое кольцо',
            price=Decimal('50000.00'),
            category=self.category,
            is_active=True
        )
        ProductVariant.objects.create(
            product=product2,
            size='18',
            stock_quantity=5,
            reserved_quantity=0
        )
        
        response = self.client.get('/api/products/?price_min=10000&price_max=30000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        products = response.data.get('results', response.data)
        for product in products:
            price = Decimal(str(product['price']))
            self.assertTrue(price >= 10000)
            self.assertTrue(price <= 30000)
    
    def test_09_filter_products_with_discount(self):
        """Тест фильтрации товаров со скидкой"""
        product2 = Product.objects.create(
            name='Товар со скидкой',
            slug='discount-product',
            description='Товар со скидкой',
            price=Decimal('10000.00'),
            old_price=Decimal('15000.00'),
            category=self.category,
            is_active=True
        )
        ProductVariant.objects.create(
            product=product2,
            size='16',
            stock_quantity=5,
            reserved_quantity=0
        )
        
        response = self.client.get('/api/products/?has_discount=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        products = response.data.get('results', response.data)
        for product in products:
            self.assertIsNotNone(product.get('old_price'))
    
    def test_10_get_categories(self):
        """Тест получения списка категорий"""
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
    
    def test_11_get_collections(self):
        """Тест получения списка коллекций"""
        response = self.client.get('/api/collections/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)


class CartTests(TestCase):
    """Тесты для корзины"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='cartuser@example.com', password='TestPass123!')
        self.client.force_authenticate(user=self.user)
        
        self.category = Category.objects.create(name='Браслеты', slug='bracelets')
        self.product = Product.objects.create(
            name='Серебряный браслет',
            slug='silver-bracelet',
            description='Красивый браслет',
            price=Decimal('12000.00'),
            category=self.category,
            is_active=True
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='18',
            stock_quantity=10,
            reserved_quantity=0
        )
        
    def test_12_get_cart_empty(self):
        """Тест получения пустой корзины"""
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_items'], 0)
    
    def test_13_add_item_to_cart(self):
        """Тест добавления товара в корзину (по variant_id)"""
        data = {'variant_id': self.variant.id, 'quantity': 2}
        response = self.client.post('/api/cart/add_item/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_items'], 2)
    
    def test_14_update_cart_item_quantity(self):
        """Тест изменения количества товара в корзине"""
        self.client.post('/api/cart/add_item/', {'variant_id': self.variant.id, 'quantity': 1}, format='json')
        
        cart = Cart.objects.get(user=self.user)
        cart_item = cart.items.first()
        
        data = {'cart_item_id': cart_item.id, 'quantity': 5}
        response = self.client.post('/api/cart/update_item/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_15_remove_item_from_cart(self):
        """Тест удаления товара из корзины"""
    
        self.client.post('/api/cart/add_item/', {'variant_id': self.variant.id, 'quantity': 1}, format='json')
 
        cart = Cart.objects.get(user=self.user)
        cart_item = cart.items.first()

        data = {'cart_item_id': cart_item.id}
        response = self.client.post('/api/cart/remove_item/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart.items.count(), 0)


class OrderTests(TestCase):
    """Тесты для заказов"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='orderuser@example.com', password='TestPass123!')
        self.client.force_authenticate(user=self.user)
        
        self.category = Category.objects.create(name='Серьги', slug='earrings')
        self.product = Product.objects.create(
            name='Серебряные серьги',
            slug='silver-earrings',
            description='Красивые серьги',
            price=Decimal('18000.00'),
            category=self.category,
            is_active=True
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='One Size',
            stock_quantity=10,
            reserved_quantity=0
        )

        self.cart, created = Cart.objects.get_or_create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            variant=self.variant,
            quantity=1
        )
    
    def test_16_create_order_success(self):
        """Тест успешного создания заказа"""
        data = {
            'delivery_address': 'Москва, ул. Тверская, д. 1',
            'delivery_method': 'courier',
            'payment_method': 'card',
            'phone': '+79991234567'
        }
        response = self.client.post('/api/orders/create_order/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data.get('order_number'))
        self.assertEqual(response.data['status'], 'new')
    
    def test_17_get_user_orders(self):
        """Тест получения списка заказов пользователя"""
        data = {
            'delivery_address': 'Москва, ул. Тверская, д. 1',
            'delivery_method': 'courier',
            'payment_method': 'card',
            'phone': '+79991234567'
        }
        self.client.post('/api/orders/create_order/', data, format='json')
        
        response = self.client.get('/api/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)


class FavoriteTests(TestCase):
    """Тесты для избранного"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='favuser@example.com', password='TestPass123!')
        self.client.force_authenticate(user=self.user)
        
        self.category = Category.objects.create(name='Подвески', slug='pendants')
        self.product = Product.objects.create(
            name='Серебряная подвеска',
            slug='silver-pendant',
            description='Красивая подвеска',
            price=Decimal('8000.00'),
            category=self.category,
            is_active=True
        )

        ProductVariant.objects.create(
            product=self.product,
            size='One Size',
            stock_quantity=15,
            reserved_quantity=0
        )
    
    def test_18_add_to_favorites(self):
        """Тест добавления товара в избранное"""
        data = {'product_id': self.product.id}
        response = self.client.post('/api/favorites/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Wishlist.objects.filter(user=self.user).count(), 1)
    
    def test_19_get_favorites_list(self):
        """Тест получения списка избранного"""
        Wishlist.objects.create(user=self.user, product=self.product)
        response = self.client.get('/api/favorites/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
    
    def test_20_remove_from_favorites(self):
        """Тест удаления товара из избранного"""
        wishlist = Wishlist.objects.create(user=self.user, product=self.product)
        response = self.client.delete(f'/api/favorites/{wishlist.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Wishlist.objects.filter(user=self.user).count(), 0)


class UnauthorizedAccessTests(TestCase):
    """Тесты для проверки доступа неавторизованных пользователей"""
    
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Тестовая категория', slug='test')
        self.product = Product.objects.create(
            name='Тестовый товар',
            slug='test-product',
            description='Тестовое описание',
            price=Decimal('5000.00'),
            category=self.category,
            is_active=True
        )

        ProductVariant.objects.create(
            product=self.product,
            size='One Size',
            stock_quantity=10,
            reserved_quantity=0
        )
    
    def test_21_unauthorized_cart_access_allowed(self):
        """Тест: неавторизованный пользователь может работать с корзиной (гостевая корзина)"""
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_items', response.data)
    
    def test_22_unauthorized_orders_access_denied(self):
        """Тест: неавторизованный пользователь не может получить заказы"""
        response = self.client.get('/api/orders/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_23_unauthorized_favorites_access_denied(self):
        """Тест: неавторизованный пользователь не может получить избранное"""
        response = self.client.get('/api/favorites/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_24_unauthorized_can_see_products(self):
        """Тест: неавторизованный пользователь может просматривать товары"""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_25_unauthorized_can_see_categories(self):
        """Тест: неавторизованный пользователь может просматривать категории"""
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)