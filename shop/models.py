from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Модель пользователя.
    """
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Телефон'
    )
    bonus_points = models.IntegerField(
        default=0,
        verbose_name='Бонусные баллы'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

class Category(models.Model):
    """
    Категория товара с поддержкой вложенности.
    """
    name = models.CharField(
        max_length=255,
        verbose_name='Название'
    )
    slug = models.SlugField(
        unique=True,
        verbose_name='URL-идентификатор'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    parent = models.ForeignKey(
        'self',  # ссылка на эту же модель
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
        ordering = ['name']  # сортировка по названию

    def __str__(self):
        return self.name

class Brand(models.Model):
    """
    Бренд производителя.
    """
    name = models.CharField(
        max_length=255,
        verbose_name='Название'
    )
    slug = models.SlugField(
        unique=True,
        verbose_name='URL-идентификатор'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    logo = models.ImageField(
        upload_to='brands/',
        blank=True,
        null=True,
        verbose_name='Логотип'
    )

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Ювелирное изделие.
    """
    # Основная информация
    name = models.CharField(
        max_length=255,
        verbose_name='Название'
    )
    slug = models.SlugField(
        unique=True,
        verbose_name='URL-идентификатор'
    )
    description = models.TextField(
        verbose_name='Описание'
    )
    
    # Цены и наличие
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена'
    )
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Старая цена'
    )
    stock_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество на складе'
    )
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name='Зарезервированное количество'
    )
    
    # Связи с другими таблицами
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products',
        verbose_name='Категория'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Бренд'
    )
    
    # Характеристики ювелирного изделия
    metal = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Металл'
    )
    fineness = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Проба'
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Вес (г)'
    )
    size = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Размер'
    )
    stones = models.BooleanField(
        default=False,
        verbose_name='Наличие камней'
    )
    stone_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Тип камня'
    )
    collection = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Коллекция'
    )
    
    # Мета-информация
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products_created',
        verbose_name='Создал'
    )

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']  # сортировка по убыванию даты создания
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'price']),
        ]

    def __str__(self):
        return self.name
    
    @property
    def available_quantity(self):
        """
        Доступное количество товара (на складе минус зарезервированное).
        Это вычисляемое поле, не хранится в БД.
        """
        return self.stock_quantity - self.reserved_quantity
    
    @property
    def discount_percent(self):
        """
        Процент скидки (если есть старая цена).
        """
        if self.old_price and self.old_price > self.price:
            return int((1 - self.price / self.old_price) * 100)
        return 0

class ProductImage(models.Model):
    """
    Изображения товара (одно или несколько).
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Товар'
    )
    image = models.ImageField(
        upload_to='products/',
        verbose_name='Изображение'
    )
    is_main = models.BooleanField(
        default=False,
        verbose_name='Основное'
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок сортировки'
    )

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.product.name} - изображение {self.id}"

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
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        if self.user:
            return f"Корзина {self.user.email}"
        return f"Корзина гостя (сессия: {self.session_key})"
    
    @property
    def total_price(self):
        """
        Общая стоимость всех товаров в корзине.
        """
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total_items(self):
        """
        Общее количество товаров в корзине.
        """
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """
    Элемент корзины (связь товара и корзины с количеством).
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
        unique_together = ('cart', 'product')  # один товар в корзине может быть только один раз

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
    
    @property
    def total_price(self):
        """
        Стоимость этой позиции (цена товара * количество).
        """
        return self.product.price * self.quantity