from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import (
    Category, Product, Cart, CartItem, Collection,
    Order, OrderItem, Review, Wishlist, PromoCode, PromoCodeUsage
)
from django.utils import timezone

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации нового пользователя.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone', 'password', 'password2')

    def validate(self, attrs):
        """
        Проверяем, что пароли совпадают.
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают."})
        return attrs

    def create(self, validated_data):
        """
        Создаём пользователя.
        """
        validated_data.pop('password2')  # удаляем поле password2, оно не нужно в модели
        user = User.objects.create_user(**validated_data)
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Кастомный сериализатор для входа.
    Добавляем email в ответ.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
        }
        return data

class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для просмотра и редактирования профиля.
    """
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 'bonus_points', 'date_joined', 'birthday')
        read_only_fields = ('id', 'email', 'date_joined')

class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор для категории.
    """
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'parent', 'image')

class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для товара.
    """
    average_rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    is_in_favorites = serializers.SerializerMethodField()
    
    silver_type_display = serializers.CharField(source='get_silver_type_display', read_only=True)
    fineness_display = serializers.CharField(source='get_fineness_display', read_only=True)
    stone_type_display = serializers.CharField(source='get_stone_type_display', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    collection_name = serializers.CharField(source='collection.name', read_only=True)
    collection_slug = serializers.CharField(source='collection.slug', read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'description', 'price', 'old_price',
            'stock_quantity', 'reserved_quantity', 'available_quantity',
            'category', 'category_name', 'country',
            'silver_type', 'silver_type_display',
            'fineness', 'fineness_display',
            'weight', 'size',
            'stones', 'stone_type', 'stone_type_display', 'stone_weight',
            'collection', 'collection_name', 'collection_slug',
            'image', 'image_2', 'image_3', 'image_4', 'image_5',
            'average_rating', 'reviews_count', 'discount_percent',
            'created_at', 'is_in_favorites', 'is_active'
        )

    def get_is_in_favorites(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_in_wishlist(request.user)
        return False

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', read_only=True, max_digits=10, decimal_places=2)
    old_price = serializers.DecimalField(source='product.old_price', read_only=True, max_digits=10, decimal_places=2)  # ← добавить
    product_image = serializers.ImageField(source='product.image', read_only=True)
    total_price = serializers.DecimalField(read_only=True, max_digits=10, decimal_places=2)

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'product_name', 'product_price', 'old_price', 'product_image', 
                  'quantity', 'size', 'added_at', 'total_price')
class CartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для корзины.
    """
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(read_only=True, max_digits=10, decimal_places=2)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ('id', 'user', 'items', 'total_price', 'total_items', 'updated_at')

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для позиции заказа.
    """
    total_price = serializers.DecimalField(read_only=True, max_digits=10, decimal_places=2)
    product_image = serializers.ImageField(source='product.image', read_only=True)  # ← добавить
    size = serializers.CharField(source='product.size', read_only=True)  # ← добавить (если нужно)

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'price', 'quantity', 'total_price', 'product_image', 'size')
        
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'user', 'created_at', 'status', 'status_display',
            'total_price', 'delivery_address', 'delivery_method', 'payment_method', 'delivery_date', 'delivery_time', 
            'gift_wrap', 'gift_message', 'comment', 'delivered_at', 'items', 'bonus_earned'
        )
        read_only_fields = ('id', 'order_number', 'created_at', 'total_price')

import re

class OrderCreateSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(write_only=True, required=True)
    promo_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Order
        fields = (
            'delivery_address', 'delivery_method', 'payment_method',
            'delivery_date', 'delivery_time',
            'gift_wrap', 'gift_message', 'comment', 'phone', 'promo_code'
        )

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        
        phone = validated_data.pop('phone', None)
        promo_code_str = validated_data.pop('promo_code', None)
        
        if phone and user.is_authenticated:
            user.phone = phone
            user.save()

        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Корзина не найдена")
        
        if not cart.items.exists():
            raise serializers.ValidationError("Корзина пуста")

        # Рассчитываем общую сумму
        total_price = cart.total_price
        promo_discount = 0
        promo_obj = None
        
        # Применяем промокод, если он есть
        if promo_code_str:
            try:
                promo = PromoCode.objects.get(code__iexact=promo_code_str)
                if promo.is_valid:
                    # Проверяем для новых пользователей
                    if not (promo.only_new_users and Order.objects.filter(user=user).exists()):
                        # Рассчитываем скидку
                        if promo.discount_type == 'percent':
                            discount = total_price * (promo.discount_value / 100)
                            if promo.max_discount_amount and discount > promo.max_discount_amount:
                                discount = promo.max_discount_amount
                        else:
                            discount = min(promo.discount_value, total_price)
                        
                        promo_discount = discount
                        promo_obj = promo
            except PromoCode.DoesNotExist:
                pass
        
        final_price = total_price - promo_discount
        
        # Создаём заказ
        order = Order.objects.create(
            user=user,
            total_price=final_price,
            promo_code=promo_obj,
            promo_discount=promo_discount,
            **validated_data
        )

        # Переносим товары из корзины в заказ
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                price=cart_item.product.price,
                quantity=cart_item.quantity
            )
            
            product = cart_item.product
            product.stock_quantity -= cart_item.quantity
            product.save()
        
        # Сохраняем использование промокода
        if promo_obj:
            PromoCodeUsage.objects.create(
                user=user,
                promo_code=promo_obj,
                order=order,
                discount_amount=promo_discount
            )
            promo_obj.used_count += 1
            promo_obj.save()

        # Очищаем корзину
        cart.items.all().delete()
        
        # Удаляем промокод из сессии
        request.session.pop('applied_promo', None)

        return order

class ReviewSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отзыва.
    """
    user_name = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'user', 'user_name', 'product', 'rating', 'comment', 'image', 'created_at', 'moderated')
        read_only_fields = ('id', 'user', 'created_at', 'moderated')

    def validate(self, attrs):
        """
        Проверяем, что пользователь покупал этот товар.
        """
        request = self.context.get('request')
        user = request.user
        product = attrs.get('product')

        # Проверяем, есть ли у пользователя доставленный заказ с этим товаром
        has_purchased = Order.objects.filter(
            user=user,
            items__product=product,
            status=Order.Status.DELIVERED
        ).exists()

        if not has_purchased:
            raise serializers.ValidationError(
                "Вы можете оставить отзыв только на товары, которые вы купили и получили."
            )
        return attrs

    def create(self, validated_data):
        """
        Создаём отзыв, автоматически подставляя пользователя.
        """
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)

class WishlistSerializer(serializers.ModelSerializer):
    """
    Сериализатор для избранного.
    """
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Wishlist
        fields = ('id', 'user', 'product', 'product_id', 'added_at')
        read_only_fields = ('id', 'user', 'added_at')

    def create(self, validated_data):
        """
        Создаём запись в избранном, автоматически подставляя пользователя.
        """
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)

from .models import PromoCode, PromoCodeUsage

class PromoCodeSerializer(serializers.ModelSerializer):
    discount_display = serializers.CharField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    days_left = serializers.SerializerMethodField()
    
    class Meta:
        model = PromoCode
        fields = (
            'id', 'code', 'discount_type', 'discount_value', 'discount_display',
            'min_order_amount', 'max_discount_amount', 'valid_from', 'valid_to',
            'is_valid', 'only_new_users', 'days_left'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_days_left(self, obj):
        if obj.valid_to:
            days = (obj.valid_to - timezone.now()).days
            return max(0, days)
        return None

class ApplyPromoCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    order_total = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, attrs):
        code = attrs.get('code')
        order_total = attrs.get('order_total')
        user = self.context.get('request').user
        
        try:
            promo = PromoCode.objects.get(code__iexact=code)
        except PromoCode.DoesNotExist:
            raise serializers.ValidationError({'code': 'Промокод не найден'})
        
        # Проверяем активность
        if not promo.is_valid:
            raise serializers.ValidationError({'code': 'Промокод неактивен или истёк срок действия'})
        
        # Проверка минимальной суммы заказа
        if order_total < promo.min_order_amount:
            raise serializers.ValidationError({'code': f'Минимальная сумма заказа для этого промокода: {promo.min_order_amount} ₽'})
        
        # Проверка для новых пользователей
        if promo.only_new_users:
            user_orders_count = Order.objects.filter(user=user).count()
            if user_orders_count > 0:
                raise serializers.ValidationError({'code': 'Этот промокод только для новых пользователей'})
        
        # Проверка лимита использований пользователем
        user_uses_count = PromoCodeUsage.objects.filter(user=user, promo_code=promo).count()
        if user_uses_count >= promo.user_limit:
            raise serializers.ValidationError({'code': f'Вы уже использовали этот промокод (максимум {promo.user_limit} раз)'})
        
        # Рассчитываем скидку
        if promo.discount_type == 'percent':
            discount = order_total * (promo.discount_value / 100)
            if promo.max_discount_amount and discount > promo.max_discount_amount:
                discount = promo.max_discount_amount
        else:  # fixed
            discount = promo.discount_value
            if discount > order_total:
                discount = order_total
        
        attrs['promo'] = promo
        attrs['discount_amount'] = discount
        
        return attrs
class CollectionSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(source='products.count', read_only=True)
    
    class Meta:
        model = Collection
        fields = ('id', 'name', 'slug', 'description', 'image', 'order', 'is_active', 'products_count', 'created_at')