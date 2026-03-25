from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from .models import Category, Product, Cart, CartItem, Order, Review, Wishlist

User = get_user_model()


class UserModelTest(TestCase):
    """Тесты для модели пользователя"""

    def test_create_user(self):
        """Тест 1: Создание пользователя"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Тест',
            last_name='Пользователь'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))

    def test_user_phone_field(self):
        """Тест 2: Проверка поля телефона"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            phone='+79161234567'
        )
        self.assertEqual(user.phone, '+79161234567')

    def test_bonus_points_default(self):
        """Тест 3: Бонусные баллы по умолчанию = 0"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.bonus_points, 0)


class CategoryModelTest(TestCase):
    """Тесты для модели категории"""

    def test_create_category(self):
        """Тест 4: Создание категории"""
        category = Category.objects.create(
            name='Кольца',
            slug='kolca'
        )
        self.assertEqual(category.name, 'Кольца')
        self.assertEqual(str(category), 'Кольца')


class ProductModelTest(TestCase):
    """Тесты для модели товара"""

    def setUp(self):
        self.category = Category.objects.create(name='Кольца', slug='kolca')
        self.product = Product.objects.create(
            name='Кольцо серебряное',
            slug='kolco-serebryanoe',
            description='Красивое кольцо',
            price=Decimal('5000.00'),
            stock_quantity=10,
            category=self.category,
            metal='Серебро',
            fineness=925
        )

    def test_product_available_quantity(self):
        """Тест 5: Проверка доступного количества"""
        self.assertEqual(self.product.available_quantity, 10)

    def test_discount_percent_no_discount(self):
        """Тест 6: Скидка отсутствует"""
        self.assertEqual(self.product.discount_percent, 0)

    def test_discount_percent_with_discount(self):
        """Тест 7: Скидка рассчитывается правильно"""
        self.product.old_price = Decimal('10000.00')
        self.product.save()
        # Скидка: (10000 - 5000) / 10000 * 100 = 50%
        self.assertEqual(self.product.discount_percent, 50)


class CartModelTest(TestCase):
    """Тесты для модели корзины"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='cartuser@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Кольца', slug='kolca')
        self.product = Product.objects.create(
            name='Кольцо',
            slug='kolco',
            description='Описание',
            price=Decimal('5000.00'),
            stock_quantity=10,
            category=self.category
        )
        # Корзина уже создаётся автоматически при создании пользователя
        self.cart = self.user.cart  # получаем существующую корзину

    def test_cart_created_for_user(self):
        """Тест 8: Корзина создаётся для пользователя"""
        self.assertIsNotNone(self.user.cart)  # проверяем, что корзина есть

    def test_add_item_to_cart(self):
        """Тест 9: Добавление товара в корзину"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.total_price, Decimal('10000.00'))

    def test_cart_total_price(self):
        """Тест 10: Общая стоимость корзины"""
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.assertEqual(self.cart.total_price, Decimal('10000.00'))


class OrderModelTest(TestCase):
    """Тесты для модели заказа"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='orderuser@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Кольца', slug='kolca')
        self.product = Product.objects.create(
            name='Кольцо',
            slug='kolco',
            description='Описание',
            price=Decimal('5000.00'),
            stock_quantity=10,
            category=self.category
        )

    def test_order_creation(self):
        """Тест 11: Создание заказа"""
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('10000.00'),
            delivery_address='Москва, ул. Пушкина, д. 1',
            delivery_method='Курьер',
            payment_method='Карта онлайн'
        )
        self.assertEqual(order.status, Order.Status.NEW)
        self.assertIsNotNone(order.order_number)
        self.assertTrue(order.order_number.startswith('ORD-'))


class ReviewModelTest(TestCase):
    """Тесты для модели отзыва"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='reviewuser@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Кольца', slug='kolca')
        self.product = Product.objects.create(
            name='Кольцо',
            slug='kolco',
            description='Описание',
            price=Decimal('5000.00'),
            stock_quantity=10,
            category=self.category
        )
        # Создаём доставленный заказ для возможности отзыва
        self.order = Order.objects.create(
            user=self.user,
            total_price=Decimal('5000.00'),
            delivery_address='Москва',
            delivery_method='Курьер',
            payment_method='Карта',
            status=Order.Status.DELIVERED
        )

    def test_review_validation_purchased(self):
        """Тест 12: Отзыв можно оставить только после покупки"""
        review = Review(
            user=self.user,
            product=self.product,
            rating=5,
            comment='Отлично!'
        )
        # У товара нет заказа в статусе DELIVERED, поэтому должна быть ошибка
        with self.assertRaises(Exception):
            review.clean()


class APITestCase(TestCase):
    """Тесты для API"""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Кольца', slug='kolca')
        self.product = Product.objects.create(
            name='Кольцо',
            slug='kolco',
            description='Описание',
            price=Decimal('5000.00'),
            stock_quantity=10,
            category=self.category
        )

    def test_products_list(self):
        """Тест 13: GET /api/products/ возвращает список товаров"""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_product_detail(self):
        """Тест 14: GET /api/products/{id}/ возвращает детали товара"""
        response = self.client.get(f'/api/products/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Кольцо')

    def test_categories_list(self):
        """Тест 15: GET /api/categories/ возвращает список категорий"""
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_by_category(self):
        """Тест 16: Фильтрация товаров по категории"""
        response = self.client.get(f'/api/products/?category={self.category.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_by_price_min(self):
        """Тест 17: Фильтрация по минимальной цене"""
        response = self.client.get('/api/products/?price_min=6000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # товар стоит 5000, не попадает

    def test_filter_by_price_max(self):
        """Тест 18: Фильтрация по максимальной цене"""
        response = self.client.get('/api/products/?price_max=4000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # товар стоит 5000, не попадает

    def test_filter_by_price_range(self):
        """Тест 19: Фильтрация по диапазону цен"""
        response = self.client.get('/api/products/?price_min=4000&price_max=6000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # товар попадает

    def test_register_user(self):
        """Тест 20: Регистрация пользователя"""
        data = {
            'email': 'newuser@example.com',
            'password': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Новый',
            'last_name': 'Пользователь'
        }
        response = self.client.post('/api/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())