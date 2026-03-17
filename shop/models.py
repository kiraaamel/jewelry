from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

def generate_order_number():
    """
    Генерирует уникальный номер заказа.
    Формат: ORD-YYYYMMDD-XXXX (где XXXX - случайные символы)
    """
    date_part = timezone.now().strftime('%Y%m%d')
    random_part = str(uuid.uuid4())[:4].upper()
    return f"ORD-{date_part}-{random_part}"

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
    
    def is_product_in_wishlist(self, product_id):
        """
        Проверяет, находится ли товар с указанным ID в избранном у пользователя.
        Возвращает True или False.
        """
        return self.wishlist.filter(product_id=product_id).exists()

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
    def average_rating(self):
        """
        Средний рейтинг товара на основе отзывов.
        """
        reviews = self.reviews.filter(moderated=True)  # только промодерированные
        if not reviews:
            return 0
        total = sum(review.rating for review in reviews)
        return round(total / reviews.count(), 1)  # округляем до 1 знака
    
    @property
    def reviews_count(self):
        """
        Количество отзывов на товар.
        """
        return self.reviews.filter(moderated=True).count()

    def is_in_wishlist(self, user):
        """
        Проверяет, находится ли товар в избранном у указанного пользователя.
        """
        if not user or not user.is_authenticated:
            return False
        return Wishlist.objects.filter(user=user, product=self).exists()

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

class Order(models.Model):
    """
    Заказ покупателя.
    """
    class Status(models.TextChoices):
        """
        Возможные статусы заказа.
        TextChoices - специальный класс Django для создания выпадающих списков.
        """
        NEW = 'new', 'Новый'              # (значение в БД, отображаемое имя)
        CONFIRMED = 'confirmed', 'Подтверждён'
        SHIPPED = 'shipped', 'Отправлен'
        DELIVERED = 'delivered', 'Доставлен'
        CANCELLED = 'cancelled', 'Отменён'

    # Связь с пользователем (может быть NULL, если пользователь удалён)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Пользователь'
    )
    
    # Уникальный номер заказа для клиента
    order_number = models.CharField(
        max_length=50,
        unique=True,
        default=generate_order_number,
        verbose_name='Номер заказа'
    )
    
    # Дата создания
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    # Статус заказа (используем класс Status выше)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,  # выпадающий список из Status
        default=Status.NEW,
        verbose_name='Статус'
    )
    
    # Общая стоимость заказа
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Общая стоимость'
    )
    
    # Информация о доставке
    delivery_address = models.TextField(
        verbose_name='Адрес доставки'
    )
    delivery_method = models.CharField(
        max_length=100,
        verbose_name='Способ доставки'
    )
    
    # Информация об оплате
    payment_method = models.CharField(
        max_length=100,
        verbose_name='Способ оплаты'
    )
    
    # Дополнительные опции
    gift_wrap = models.BooleanField(
        default=False,
        verbose_name='Подарочная упаковка'
    )
    gift_message = models.TextField(
        blank=True,
        verbose_name='Текст открытки'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий к заказу'
    )
    
    # Дата фактического получения (заполняется при доставке)
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата получения'
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']  # сначала новые заказы

    def __str__(self):
        return f"Заказ №{self.order_number}"


class OrderItem(models.Model):
    """
    Позиция заказа (товар в заказе).
    """
    # Связь с заказом
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )
    
    # Связь с товаром (может быть NULL, если товар удалён из каталога)
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Товар'
    )
    
    # Копия названия товара на момент заказа (для истории)
    product_name = models.CharField(
        max_length=255,
        verbose_name='Название товара (на момент заказа)'
    )
    
    # Цена на момент заказа (для истории)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена на момент заказа'
    )
    
    # Количество
    quantity = models.PositiveIntegerField(
        verbose_name='Количество'
    )

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"
    
    @property
    def total_price(self):
        """
        Стоимость этой позиции (цена * количество).
        """
        return self.price * self.quantity

class Review(models.Model):
    """
    Отзыв на товар от покупателя.
    """
    # Связь с пользователем (кто оставил отзыв)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Пользователь'
    )
    
    # Связь с товаром (на какой товар отзыв)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Товар'
    )
    
    # Оценка (от 1 до 5)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка'
    )
    
    # Текст отзыва
    comment = models.TextField(
        blank=True,
        verbose_name='Текст отзыва'
    )
    
    # Фото к отзыву (необязательно)
    image = models.ImageField(
        upload_to='reviews/',
        blank=True,
        null=True,
        verbose_name='Фото'
    )
    
    # Дата создания
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата'
    )
    
    # Флаг модерации (прошёл ли отзыв проверку)
    moderated = models.BooleanField(
        default=False,
        verbose_name='Промодерировано'
    )

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        # Один пользователь может оставить только один отзыв на товар
        unique_together = ('user', 'product')
        ordering = ['-created_at']  # сначала новые отзывы

    def __str__(self):
        return f"Отзыв {self.user.email} на {self.product.name} - {self.rating}★"

class Wishlist(models.Model):
    """
    Список избранного пользователя.
    """
    # Связь с пользователем
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist',
        verbose_name='Пользователь'
    )
    
    # Связь с товаром
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by',
        verbose_name='Товар'
    )
    
    # Дата добавления
    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        # Один пользователь может добавить один товар в избранное только один раз
        unique_together = ('user', 'product')
        ordering = ['-added_at']  # сначала новые добавления

    def __str__(self):
        return f"{self.user.email} -> {self.product.name}"

class Promotion(models.Model):
    """
    Акция (скидка на товары или категории).
    """
    class DiscountType(models.TextChoices):
        """Типы скидок"""
        PERCENT = 'percent', 'Процент'
        FIXED = 'fixed', 'Фиксированная сумма'

    # Основная информация
    name = models.CharField(
        max_length=255,
        verbose_name='Название акции'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    
    # Тип и размер скидки
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        verbose_name='Тип скидки'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Значение скидки'
    )
    
    # Срок действия
    start_date = models.DateTimeField(
        verbose_name='Начало действия'
    )
    end_date = models.DateTimeField(
        verbose_name='Окончание действия'
    )
    
    # На какие товары действует (связи)
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name='promotions',
        verbose_name='Товары'
    )
    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name='promotions',
        verbose_name='Категории'
    )
    
    # Активна ли акция (можно отключить вручную)
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Акция'
        verbose_name_plural = 'Акции'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_discount_type_display()}: {self.discount_value})"
    
    @property
    def is_valid(self):
        """
        Проверяет, действует ли акция сейчас.
        """
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

class Payment(models.Model):
    """
    Информация о платеже по заказу.
    """
    class Status(models.TextChoices):
        """Статусы платежа"""
        PENDING = 'pending', 'В обработке'
        SUCCESS = 'success', 'Успешно'
        FAILED = 'failed', 'Ошибка'
        REFUNDED = 'refunded', 'Возврат'

    # Связь с заказом
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Заказ'
    )
    
    # Сумма платежа
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма'
    )
    
    # Способ оплаты
    method = models.CharField(
        max_length=100,
        verbose_name='Метод оплаты'
    )
    
    # Статус
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус платежа'
    )
    
    # ID транзакции в платёжной системе
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='ID транзакции'
    )
    
    # Дата платежа
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата платежа'
    )

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f"Платёж {self.id} по заказу {self.order.order_number} - {self.get_status_display()}"

class Employee(models.Model):
    """
    Сотрудник компании.
    """
    # Основная информация
    name = models.CharField(
        max_length=255,
        verbose_name='Полное имя'
    )
    position = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Должность'
    )
    hire_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата приёма'
    )
    
    # Связь с учётной записью пользователя (если есть)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profile',
        verbose_name='Учётная запись'
    )
    
    # Контактные данные
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Телефон'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )
    
    # Дополнительно
    is_active = models.BooleanField(
        default=True,
        verbose_name='Работает'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Примечания'
    )

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'

    def __str__(self):
        return self.name