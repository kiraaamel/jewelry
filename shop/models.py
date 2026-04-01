from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.base_user import BaseUserManager

def product_image_upload_path(instance, filename):
    """Путь для загрузки изображений товаров"""
    return f'products/{instance.slug}/{filename}'

class UserManager(BaseUserManager):
    """
    Кастомный менеджер для модели User с email в качестве логина.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

def generate_order_number():
    """
    Генерирует уникальный номер заказа.
    Формат: ORD-YYYYMMDD-XXXX (где XXXX - случайные символы)
    """
    date_part = timezone.now().strftime('%Y%m%d')
    random_part = str(uuid.uuid4())[:4].upper()
    return f"ORD-{date_part}-{random_part}"


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name='Email')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    bonus_points = models.IntegerField(default=0, verbose_name='Бонусные баллы')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()  # ← кастомный менеджер

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

    def is_product_in_wishlist(self, product_id):
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

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Ювелирное изделие.
    """
    # Типы серебра
    SILVER_TYPE_CHOICES = [
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
    FINENESS_CHOICES = [
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
    STONE_TYPE_CHOICES = [
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
    old_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Старая цена')
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='Количество на складе')
    reserved_quantity = models.PositiveIntegerField(default=0, verbose_name='Зарезервированное количество')
    
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
    
    # Фотографии (5 полей вместо отдельной модели)
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
    size = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Размер',
        help_text='Например: 16.5, 17, 18, S, M, L'
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
    collection = models.CharField(max_length=255, blank=True, verbose_name='Коллекция')
    
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
    
    # Активность (мягкое удаление)
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

    def __str__(self):
        silver_display = self.get_silver_type_display()
        fineness_display = self.get_fineness_display()
        return f"{self.name} - {silver_display} ({fineness_display}) - {self.price}₽"

    # ========== СВОЙСТВА ==========
    
    @property
    def available_quantity(self):
        return self.stock_quantity - self.reserved_quantity

    @property
    def average_rating(self):
        reviews = self.reviews.filter(moderated=True)
        if not reviews:
            return 0
        total = sum(review.rating for review in reviews)
        return round(total / reviews.count(), 1)

    @property
    def reviews_count(self):
        return self.reviews.filter(moderated=True).count()

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int((1 - self.price / self.old_price) * 100)
        return 0
    
    @property
    def has_discount(self):
        return self.old_price is not None and self.old_price > self.price
    
    @property
    def all_images(self):
        """Список всех загруженных изображений"""
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
    def images_count(self):
        """Количество загруженных изображений"""
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
    def main_image(self):
        """Возвращает URL главного фото"""
        if self.image:
            return self.image.url if hasattr(self.image, 'url') else self.image
        return None

    # ========== МЕТОДЫ ==========
    
    def is_in_wishlist(self, user):
        if not user or not user.is_authenticated:
            return False
        return Wishlist.objects.filter(user=user, product=self).exists()
    
    def clean(self):
        """Валидация данных перед сохранением"""
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
        
        # Проверка количества на складе
        if self.stock_quantity < 0:
            raise ValidationError({'stock_quantity': 'Количество на складе не может быть отрицательным'})
    
    def save(self, *args, **kwargs):
        """Создаём slug, если не указан"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Удаляем файлы изображений при удалении товара"""
        if self.image and self.image.name and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        if self.image_2 and self.image_2.name and os.path.isfile(self.image_2.path):
            os.remove(self.image_2.path)
        if self.image_3 and self.image_3.name and os.path.isfile(self.image_3.path):
            os.remove(self.image_3.path)
        if self.image_4 and self.image_4.name and os.path.isfile(self.image_4.path):
            os.remove(self.image_4.path)
        if self.image_5 and self.image_5.name and os.path.isfile(self.image_5.path):
            os.remove(self.image_5.path)
        super().delete(*args, **kwargs)



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
    size = models.CharField(max_length=20, blank=True, null=True)
    
    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )

    class Meta:
        verbose_name = 'Элемент корзины'
        verbose_name_plural = 'Элементы корзины'
        unique_together = ('cart', 'product')

    def clean(self):
        """
        Проверка наличия товара на складе перед сохранением.
        """
        if self.quantity > self.product.available_quantity:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f'Доступно только {self.product.available_quantity} единиц товара "{self.product.name}"'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def total_price(self):
        """
        Стоимость этой позиции (цена товара * количество).
        """
        if self.product and self.product.price is not None and self.quantity is not None:
            return self.product.price * self.quantity
        return 0


class Order(models.Model):
    """
    Заказ покупателя.
    """
    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        CONFIRMED = 'confirmed', 'Подтверждён'
        SHIPPED = 'shipped', 'Отправлен'
        DELIVERED = 'delivered', 'Доставлен'
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
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name='Статус'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,  # ← значение по умолчанию
        verbose_name='Общая стоимость'
    )
    delivery_address = models.TextField(
        verbose_name='Адрес доставки'
    )
    delivery_method = models.CharField(
        max_length=100,
        verbose_name='Способ доставки'
    )
    payment_method = models.CharField(
        max_length=100,
        verbose_name='Способ оплаты'
    )
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
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата получения'
    )
    def save(self, *args, **kwargs):
        """
        Автоматически вычисляем общую стоимость заказа.
        """
        if not self.total_price and self.pk:
            # Если заказ уже существует, считаем сумму по позициям
            self.total_price = sum(item.total_price for item in self.items.all())
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ №{self.order_number}"


class OrderItem(models.Model):
    """
    Позиция заказа (товар в заказе).
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
    product_name = models.CharField(
        max_length=255,
        verbose_name='Название товара (на момент заказа)'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Цена на момент заказа'
    )
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
        if self.price is not None and self.quantity is not None:
            return self.price * self.quantity
        return 0


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
    comment = models.TextField(
        blank=True,
        verbose_name='Текст отзыва'
    )
    image = models.ImageField(
        upload_to='reviews/',
        blank=True,
        null=True,
        verbose_name='Фото'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата'
    )
    moderated = models.BooleanField(
        default=False,
        verbose_name='Промодерировано'
    )
    def clean(self):
        """
        Проверка, что пользователь действительно покупал этот товар.
        """
        has_purchased = Order.objects.filter(
            user=self.user,
            items__product=self.product,
            status=Order.Status.DELIVERED
        ).exists()
        
        if not has_purchased:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                'Вы можете оставить отзыв только на товары, которые вы купили и получили.'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
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
    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.email} -> {self.product.name}"