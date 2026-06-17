"""
Модели данных для интернет-магазина Argentic Jewelry.

Содержит все модели: пользователь, категории, товары, корзина, заказы,
отзывы, избранное, промокоды, коллекции.
"""

import os
import uuid
import random
from typing import List, Tuple, Optional, Union
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from allauth.account.signals import user_logged_in as allauth_user_logged_in


def product_image_upload_path(instance: 'Product', filename: str) -> str:
    """
    Путь для загрузки изображений товаров.

    Args:
        instance: Экземпляр товара
        filename: Имя файла

    Returns:
        Путь для сохранения файла
    """
    return f'products/{instance.slug}/{filename}'


class UserManager(BaseUserManager):
    """
    Кастомный менеджер для модели User с email в качестве логина.
    """

    def create_user(self, email: str, password: Optional[str] = None, **extra_fields) -> 'User':
        """
        Создаёт обычного пользователя.

        Args:
            email: Email пользователя
            password: Пароль
            **extra_fields: Дополнительные поля

        Returns:
            Созданный пользователь

        Raises:
            ValueError: Если email не указан
        """
        if not email:
            raise ValueError('Email обязателен')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: Optional[str] = None, **extra_fields) -> 'User':
        """
        Создаёт суперпользователя.

        Args:
            email: Email суперпользователя
            password: Пароль
            **extra_fields: Дополнительные поля

        Returns:
            Созданный суперпользователь

        Raises:
            ValueError: Если is_staff или is_superuser не True
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


def generate_order_number() -> str:
    """
    Генерирует уникальный номер заказа.

    Формат: ORD-YYYYMMDD-XXXX (где XXXX - случайные символы)

    Returns:
        Уникальный номер заказа
    """
    date_part = timezone.now().strftime('%Y%m%d')
    random_part = str(uuid.uuid4())[:4].upper()
    return f"ORD-{date_part}-{random_part}"


class User(AbstractUser):
    """
    Модель пользователя с email в качестве логина.
    """
    username = None  # type: ignore
    email = models.EmailField(unique=True, verbose_name='Email')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    bonus_points = models.IntegerField(default=0, verbose_name='Бонусные баллы')
    birthday = models.DateField(null=True, blank=True, verbose_name='Дата рождения')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: List[str] = []

    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self) -> str:
        """Возвращает email пользователя."""
        return self.email

    def is_product_in_wishlist(self, product_id: int) -> bool:
        """
        Проверяет, находится ли товар в избранном у пользователя.

        Args:
            product_id: ID товара

        Returns:
            True если товар в избранном, иначе False
        """
        return self.wishlist.filter(product_id=product_id).exists()


class Category(models.Model):
    """
    Категория товара с поддержкой вложенности.
    """
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='URL-идентификатор')
    description = models.TextField(blank=True, verbose_name='Описание')
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория'
    )
    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True,
        verbose_name='Изображение'
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self) -> str:
        """Возвращает название категории."""
        return self.name


class Collection(models.Model):
    """
    Коллекция товаров (например: "Весенняя коллекция", "Премиум", "Свадебная").
    """
    name = models.CharField(max_length=255, verbose_name='Название коллекции')
    slug = models.SlugField(unique=True, verbose_name='URL-идентификатор')
    description = models.TextField(blank=True, verbose_name='Описание коллекции')
    image = models.ImageField(
        upload_to='collections/',
        blank=True,
        null=True,
        verbose_name='Фото коллекции'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок сортировки')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Коллекция'
        verbose_name_plural = 'Коллекции'
        ordering = ['order', 'name']

    def __str__(self) -> str:
        """Возвращает название коллекции."""
        return self.name

    def save(self, *args, **kwargs) -> None:
        """Создаёт slug, если не указан."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    Ювелирное изделие.
    """

    # Типы серебра
    SILVER_TYPE_CHOICES: List[Tuple[str, str]] = [
        ('sterling', 'Стерлинговое серебро (925)'),
        ('fine', 'Чистое серебро (999)'),
        ('argentium', 'Аргентиум серебро'),
        ('mexican', 'Мексиканское серебро'),
        ('oxidized', 'Оксидированное серебро'),
        ('rhodium_plated', 'Серебро с родиевым покрытием'),
        ('black', 'Черненое серебро'),
        ('matte', 'Матовое серебро'),
    ]

    # Пробы серебра
    FINENESS_CHOICES: List[Tuple[str, str]] = [
        ('800', '800 проба'),
        ('830', '830 проба'),
        ('875', '875 проба'),
        ('900', '900 проба'),
        ('916', '916 проба'),
        ('925', '925 проба'),
        ('960', '960 проба'),
        ('999', '999 проба'),
    ]

    # Типы камней
    STONE_TYPE_CHOICES: List[Tuple[str, str]] = [
        ('diamond', 'Бриллиант'),
        ('ruby', 'Рубин'),
        ('sapphire', 'Сапфир'),
        ('emerald', 'Изумруд'),
        ('topaz', 'Топаз'),
        ('amethyst', 'Аметист'),
        ('garnet', 'Гранат'),
        ('peridot', 'Перидот'),
        ('citrine', 'Цитрин'),
        ('aquamarine', 'Аквамарин'),
        ('tourmaline', 'Турмалин'),
        ('opal', 'Опал'),
        ('pearl', 'Жемчуг'),
        ('cubic_zirconia', 'Фианит'),
        ('moonstone', 'Лунный камень'),
        ('none', 'Нет камней'),
    ]

    # Основная информация
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='URL-идентификатор')
    description = models.TextField(verbose_name='Описание')

    # Цены и наличие
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Старая цена'
    )

    # Связь с категорией
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products',
        verbose_name='Категория'
    )

    # Страна производства
    country = models.CharField(
        max_length=100,
        blank=True,
        default='Италия',
        verbose_name='Страна производства'
    )

    # Фотографии
    image = models.ImageField(
        upload_to=product_image_upload_path,
        blank=True,
        null=True,
        verbose_name='Главное фото',
        help_text='Основное фото товара'
    )
    image_2 = models.ImageField(
        upload_to=product_image_upload_path,
        blank=True,
        null=True,
        verbose_name='Дополнительное фото 2'
    )
    image_3 = models.ImageField(
        upload_to=product_image_upload_path,
        blank=True,
        null=True,
        verbose_name='Дополнительное фото 3'
    )
    image_4 = models.ImageField(
        upload_to=product_image_upload_path,
        blank=True,
        null=True,
        verbose_name='Дополнительное фото 4'
    )
    image_5 = models.ImageField(
        upload_to=product_image_upload_path,
        blank=True,
        null=True,
        verbose_name='Дополнительное фото 5'
    )

    # Характеристики серебра
    silver_type = models.CharField(
        max_length=30,
        choices=SILVER_TYPE_CHOICES,
        default='sterling',
        verbose_name='Тип серебра'
    )
    fineness = models.CharField(
        max_length=4,
        choices=FINENESS_CHOICES,
        default='925',
        verbose_name='Проба серебра'
    )

    # Физические характеристики
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Вес изделия (г)'
    )

    # Камни
    stones = models.BooleanField(default=False, verbose_name='Наличие драгоценных камней')
    stone_type = models.CharField(
        max_length=30,
        choices=STONE_TYPE_CHOICES,
        blank=True,
        null=True,
        verbose_name='Тип камня'
    )
    stone_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Вес камней (карат)',
        help_text='Общий вес всех камней в каратах'
    )

    # Коллекция
    collection = models.ForeignKey(
        Collection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Коллекция'
    )

    # Мета-информация
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products_created',
        verbose_name='Создал'
    )
    name_lower = models.CharField(
        max_length=255,
        blank=True,
        editable=False,
        verbose_name='Название (нижний регистр)'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'price']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self) -> str:
        """Возвращает строковое представление товара."""
        silver_display = self.get_silver_type_display()
        fineness_display = self.get_fineness_display()
        return f"{self.name} - {silver_display} ({fineness_display}) - {self.price}₽"

    @property
    def available_quantity(self) -> int:
        """
        Общее доступное количество товара по всем вариантам.
        """
        return sum(
            max(0, variant.available_quantity)
            for variant in self.variants.all()
        )

    @property
    def average_rating(self) -> float:
        """
        Возвращает средний рейтинг товара на основе отзывов.

        Returns:
            Средний рейтинг (0-5), округлённый до 1 знака
        """
        reviews = self.reviews.filter(moderated=True)
        if not reviews:
            return 0
        total = sum(review.rating for review in reviews)
        return round(total / reviews.count(), 1)

    @property
    def discount_percent(self) -> int:
        """
        Возвращает процент скидки на товар.

        Returns:
            Процент скидки (0-100)
        """
        if self.old_price and self.old_price > self.price:
            return int((1 - self.price / self.old_price) * 100)
        return 0

    @property
    def has_discount(self) -> bool:
        """
        Проверяет, есть ли скидка на товар.

        Returns:
            True если есть скидка, иначе False
        """
        return self.old_price is not None and self.old_price > self.price

    @property
    def all_images(self) -> List[Tuple[str, Union[str, 'models.ImageField']]]:
        """
        Возвращает список всех загруженных изображений товара.

        Returns:
            Список кортежей (ключ, изображение)
        """
        images = []
        if self.image:
            images.append(('main', self.image.url if hasattr(self.image, 'url') else self.image))
        if self.image_2:
            images.append(('2', self.image_2.url if hasattr(self.image_2, 'url') else self.image_2))
        if self.image_3:
            images.append(('3', self.image_3.url if hasattr(self.image_3, 'url') else self.image_3))
        if self.image_4:
            images.append(('4', self.image_4.url if hasattr(self.image_4, 'url') else self.image_4))
        if self.image_5:
            images.append(('5', self.image_5.url if hasattr(self.image_5, 'url') else self.image_5))
        return images

    @property
    def images_count(self) -> int:
        """
        Возвращает количество загруженных изображений товара.

        Returns:
            Количество изображений
        """
        count = 0
        if self.image:
            count += 1
        if self.image_2:
            count += 1
        if self.image_3:
            count += 1
        if self.image_4:
            count += 1
        if self.image_5:
            count += 1
        return count

    @property
    def main_image(self) -> Optional[str]:
        """
        Возвращает URL главного фото товара.

        Returns:
            URL главного фото или None
        """
        if self.image:
            return self.image.url if hasattr(self.image, 'url') else self.image
        return None

    def is_in_wishlist(self, user: Optional[User]) -> bool:
        """
        Проверяет, находится ли товар в избранном у пользователя.

        Args:
            user: Пользователь

        Returns:
            True если товар в избранном, иначе False
        """
        if not user or not user.is_authenticated:
            return False
        return Wishlist.objects.filter(user=user, product=self).exists()

    def clean(self) -> None:
        """
        Валидация данных перед сохранением товара.

        Raises:
            ValidationError: При нарушении валидации
        """
        from django.core.exceptions import ValidationError

        # Проверка старой цены
        if self.old_price and self.old_price <= self.price:
            raise ValidationError({'old_price': 'Старая цена должна быть больше текущей'})

        # Проверка камней
        if self.stones and not self.stone_type:
            raise ValidationError({'stone_type': 'Укажите тип камней'})

        if self.stones and self.stone_type == 'none':
            raise ValidationError({'stone_type': 'Выберите конкретный тип камня'})

        if self.stone_weight and not self.stones:
            raise ValidationError({'stones': 'Отметьте наличие камней для указания веса'})

        # Проверка веса
        if self.weight and self.weight <= 0:
            raise ValidationError({'weight': 'Вес должен быть положительным числом'})

    def save(self, *args, **kwargs) -> None:
        """
        Сохраняет товар, создавая slug и name_lower перед сохранением.
        """
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1

            self.slug = slug
        self.name_lower = self.name.lower()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> None:
        """
        Удаляет товар и его изображения.
        """

        images = [
            self.image,
            self.image_2,
            self.image_3,
            self.image_4,
            self.image_5,
        ]

        for image in images:
            if image:
                image.delete(save=False)

        super().delete(*args, **kwargs)

class ProductVariant(models.Model):
    """
    Вариант товара (например размер).
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Товар'
    )

    size = models.CharField(
        max_length=20,
        verbose_name='Размер'
    )

    stock_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество на складе'
    )

    reserved_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name='Зарезервировано'
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Артикул'
    )

    class Meta:
        verbose_name = 'Вариант товара'
        verbose_name_plural = 'Варианты товаров'
        unique_together = ('product', 'size')

    @property
    def available_quantity(self) -> int:
        """
        Доступное количество товара.
        """
        return max(0, self.stock_quantity - self.reserved_quantity)

    def __str__(self) -> str:
        return f"{self.product.name} / {self.size}"

class Cart(models.Model):
    """
    Корзина покупок (привязана к пользователю или сессии).
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart',
        verbose_name='Пользователь'
    )
    session_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Ключ сессии'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self) -> str:
        """Возвращает строковое представление корзины."""
        if self.user:
            return f"Корзина {self.user.email}"
        return f"Корзина гостя (сессия: {self.session_key})"

    @property
    def total_price(self) -> Decimal:
        """
        Общая стоимость всех товаров в корзине.

        Returns:
            Общая стоимость
        """
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self) -> int:
        """
        Общее количество товаров в корзине.

        Returns:
            Количество товаров
        """
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """
    Элемент корзины.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True, 
        blank=True,
        verbose_name='Вариант товара'
    )

    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='Количество'
    )

    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )

    class Meta:
        verbose_name = 'Элемент корзины'
        verbose_name_plural = 'Элементы корзины'
        unique_together = ('cart', 'variant')
        ordering = ['-added_at'] 

    def clean(self) -> None:
        """
        Проверка корректности данных.
        """
        if self.variant.product != self.product:
            raise ValidationError(
                'Выбранный вариант не принадлежит товару.'
            )

        if self.quantity > self.variant.available_quantity:
            raise ValidationError(
                f'Доступно только '
                f'{self.variant.available_quantity} шт.'
            )

    def save(self, *args, **kwargs) -> None:
        """
        Сохранение с полной валидацией.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_price(self) -> Decimal:
        """
        Общая стоимость позиции.
        """
        return self.product.price * self.quantity

    def __str__(self) -> str:
        return (
            f"{self.product.name} "
            f"({self.variant.size}) x{self.quantity}"
        )

class PromoCode(models.Model):
    """
    Модель промокода для скидок.
    """

    class DiscountType(models.TextChoices):
        PERCENT = 'percent', 'Процентная скидка'
        FIXED = 'fixed', 'Фиксированная скидка'

    code = models.CharField(max_length=50, unique=True, verbose_name='Код промокода')
    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        default=DiscountType.PERCENT,
        verbose_name='Тип скидки'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Значение скидки')

    # Ограничения
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Минимальная сумма заказа')
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Максимальная сумма скидки'
    )

    # Даты действия
    valid_from = models.DateTimeField(default=timezone.now, verbose_name='Действует с')
    valid_to = models.DateTimeField(verbose_name='Действует до')

    # Ограничения по использованию
    usage_limit = models.PositiveIntegerField(default=1, verbose_name='Лимит использований')
    used_count = models.PositiveIntegerField(default=0, verbose_name='Количество использований')
    user_limit = models.PositiveIntegerField(default=1, verbose_name='Лимит на одного пользователя')

    # Для новых пользователей
    only_new_users = models.BooleanField(default=False, verbose_name='Только для новых пользователей')

    # Активность
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    applicable_categories = models.ManyToManyField('Category', blank=True, verbose_name='Применяется к категориям')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'
        ordering = ['-created_at']

    def __str__(self) -> str:
        """Возвращает строковое представление промокода."""
        return f"{self.code} ({self.discount_value}{'%' if self.discount_type == 'percent' else '₽'})"

    @property
    def is_valid(self) -> bool:
        """
        Проверяет, активен ли промокод в данный момент.

        Returns:
            True если промокод активен, иначе False
        """
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_to and
            (self.usage_limit is None or self.used_count < self.usage_limit)
        )

    @property
    def discount_display(self) -> str:
        """
        Возвращает строковое представление скидки.

        Returns:
            Строка скидки (например "10%" или "500 ₽")
        """
        if self.discount_type == 'percent':
            return f"{self.discount_value}%"
        return f"{self.discount_value} ₽"


class PromoCodeUsage(models.Model):
    """
    История использования промокодов пользователями.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='promo_uses',
        verbose_name='Пользователь'
    )
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.CASCADE,
        related_name='uses',
        verbose_name='Промокод'
    )
    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        related_name='promo_use',
        verbose_name='Заказ'
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма скидки')
    used_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата использования')

    class Meta:
        verbose_name = 'Использование промокода'
        verbose_name_plural = 'Использования промокодов'
        unique_together = ('user', 'promo_code', 'order')

    def __str__(self) -> str:
        """Возвращает строковое представление использования промокода."""
        return f"{self.user.email} - {self.promo_code.code}"


class Order(models.Model):
    """
    Заказ покупателя.
    """

    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        CONFIRMED = 'confirmed', 'Подтверждён'
        SHIPPED = 'shipped', 'Отправлен'
        DELIVERED = 'delivered', 'Доставлен'
        RECEIVED = 'received', 'Получен'
        CANCELLED = 'cancelled', 'Отменён'

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Пользователь'
    )
    order_number = models.CharField(
        max_length=50,
        unique=True,
        default=generate_order_number,
        verbose_name='Номер заказа'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name='Статус'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Общая стоимость'
    )
    bonus_earned = models.IntegerField(default=0, verbose_name='Начислено бонусов')
    delivery_address = models.TextField(verbose_name='Адрес доставки')
    delivery_method = models.CharField(max_length=100, verbose_name='Способ доставки')
    payment_method = models.CharField(max_length=100, verbose_name='Способ оплаты')
    
    delivery_date = models.CharField(max_length=50, blank=True, null=True, verbose_name='Дата доставки')
    delivery_time = models.CharField(max_length=50, blank=True, null=True, verbose_name='Время доставки')

    gift_wrap = models.BooleanField(default=False, verbose_name='Подарочная упаковка')
    gift_message = models.TextField(blank=True, verbose_name='Текст открытки')
    comment = models.TextField(blank=True, verbose_name='Комментарий к заказу')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата получения')
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Промокод'
    )
    promo_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Скидка по промокоду'
    )
    pickup_code = models.CharField(max_length=6, blank=True, null=True, verbose_name='Код получения')
    code_generated_at = models.DateTimeField(blank=True, null=True, verbose_name='Время генерации кода')
   
    def save(self, *args, **kwargs) -> None:
        """
        Автоматически вычисляет общую стоимость заказа перед сохранением.
        """
        if self.pk and self.total_price == 0:
            self.total_price = sum(item.total_price for item in self.items.all())
        super().save(*args, **kwargs)
    
    def generate_pickup_code(self) -> str:
        """
        Генерирует случайный 6-значный код для получения заказа.
        
        Returns:
            6-значный код
        """
        return str(random.randint(100000, 999999))
    
    def regenerate_pickup_code(self) -> None:
        """
        Обновляет код получения, если прошло больше 10 минут.
        """
        if not self.pickup_code or not self.code_generated_at:
            self.pickup_code = self.generate_pickup_code()
            self.code_generated_at = timezone.now()
            self.save(update_fields=['pickup_code', 'code_generated_at'])
        else:
            time_diff = timezone.now() - self.code_generated_at
            if time_diff.total_seconds() > 600:
                self.pickup_code = self.generate_pickup_code()
                self.code_generated_at = timezone.now()
                self.save(update_fields=['pickup_code', 'code_generated_at'])
    
    def mark_as_received(self) -> None:
        """
        Отмечает заказ как полученный и устанавливает дату получения.
        """
        self.status = self.Status.RECEIVED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self) -> str:
        """Возвращает строковое представление заказа."""
        return f"Заказ №{self.order_number}"


class OrderItem(models.Model):
    """
    Позиция заказа.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Товар'
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Вариант товара'
    )

    product_name = models.CharField(
        max_length=255,
        verbose_name='Название товара'
    )

    size = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Размер'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Цена'
    )

    quantity = models.PositiveIntegerField(
        verbose_name='Количество'
    )

    added_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата добавления'
    )

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    @property
    def total_price(self) -> Decimal:
        """
        Стоимость позиции.
        """
        return self.price * self.quantity

    def __str__(self) -> str:
        return f"{self.product_name} ({self.size}) x{self.quantity}"

class Review(models.Model):
    """
    Отзыв на товар от покупателя.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Пользователь'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Товар'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка'
    )
    comment = models.TextField(blank=True, verbose_name='Текст отзыва')
    image = models.ImageField(
        upload_to='reviews/',
        blank=True,
        null=True,
        verbose_name='Фото'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата')
    moderated = models.BooleanField(default=False, verbose_name='Промодерировано')

    def clean(self) -> None:
        """
        Проверяет, что пользователь действительно покупал этот товар.

        Raises:
            ValidationError: Если пользователь не покупал товар
        """
        has_purchased = Order.objects.filter(
            user=self.user,
            items__product=self.product,
            status=Order.Status.RECEIVED
        ).exists()

        if not has_purchased:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                'Вы можете оставить отзыв только на товары, которые вы купили и получили.'
            )

    def save(self, *args, **kwargs) -> None:
        """Сохраняет отзыв с предварительной валидацией."""
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self) -> str:
        """Возвращает строковое представление отзыва."""
        return f"Отзыв {self.user.email} на {self.product.name} - {self.rating}★"


class Wishlist(models.Model):
    """
    Список избранного пользователя.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist',
        verbose_name='Пользователь'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by',
        verbose_name='Товар'
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self) -> str:
        """Возвращает строковое представление избранного."""
        return f"{self.user.email} -> {self.product.name}"

@receiver(user_logged_in)
@receiver(allauth_user_logged_in)
def merge_cart_after_login(sender, user, request, **kwargs):
    """
    Перенос корзины гостя после входа.
    """

    if not request.session.session_key:
        return

    session_key = request.session.session_key

    try:
        guest_cart = Cart.objects.get(
            session_key=session_key,
            user__isnull=True
        )
    except Cart.DoesNotExist:
        return

    user_cart, created = Cart.objects.get_or_create(user=user)

    for guest_item in guest_cart.items.all():

        user_item, item_created = CartItem.objects.get_or_create(
            cart=user_cart,
            variant=guest_item.variant,
            defaults={
                'product': guest_item.product,
                'quantity': guest_item.quantity
            }
        )

        if not item_created:

            new_quantity = (
                user_item.quantity +
                guest_item.quantity
            )

            user_item.quantity = min(
                new_quantity,
                user_item.variant.available_quantity
            )

            user_item.save()

    guest_cart.delete()

    request.session['cart_merged'] = True