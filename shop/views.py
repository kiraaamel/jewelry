from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .models import User
# Create your views here.
from django.http import HttpResponse
from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from django.shortcuts import get_object_or_404
from .filters import ProductFilter
from decimal import Decimal
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import (
    Category, Product, Cart, CartItem, 
    Order, Review, Wishlist
)
from .serializers import (
    CategorySerializer, ProductSerializer, CartSerializer,
    OrderSerializer, OrderCreateSerializer, ReviewSerializer,
    WishlistSerializer, UserSerializer, RegisterSerializer,
    CustomTokenObtainPairSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView
from allauth.account.views import SignupView
from django.urls import reverse_lazy


class CustomSignupView(SignupView):
    """
    Кастомное представление регистрации для сохранения дополнительных полей.
    """
    def form_valid(self, form):
        # Сохраняем дополнительные поля в сессию или обрабатываем
        self.request.session['signup_first_name'] = form.cleaned_data.get('first_name', '')
        self.request.session['signup_last_name'] = form.cleaned_data.get('last_name', '')
        self.request.session['signup_phone'] = form.cleaned_data.get('phone', '')
        return super().form_valid(form)
def product_detail(request, pk):
    """Детальная страница товара"""
    return render(request, 'shop/product_detail.html', {'product_id': pk})
    
def index(request):
    return HttpResponse("Добро пожаловать в ювелирный магазин!")

class RegisterView(generics.CreateAPIView):
    """
    Регистрация нового пользователя.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]  # доступно всем

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Получение JWT токена при входе.
    """
    serializer_class = CustomTokenObtainPairSerializer

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Просмотр и редактирование профиля текущего пользователя.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]  # только авторизованные

    def get_object(self):
        return self.request.user

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для категорий (только чтение).
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]  # доступно всем

from django.db import models

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.select_related('category').prefetch_related('reviews').all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ProductFilter
    ordering_fields = ['price', 'created_at', 'average_rating']

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            # Приводим поисковый запрос к нижнему регистру
            search_lower = search.lower()
            # Ищем в name_lower (там уже всё в нижнем регистре)
            queryset = queryset.filter(name_lower__icontains=search_lower)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        product = self.get_object()
        reviews = product.reviews.filter(moderated=True).order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)
    
class CartViewSet(viewsets.GenericViewSet):
    """
    ViewSet для корзины.
    """
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def list(self, request):
        """
        Просмотр корзины.
        """
        cart = self.get_object()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """
        Добавление товара в корзину.
        """
        try:
            cart = self.get_object()
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)
            size = request.data.get('size', '')

            if not product_id:
                return Response({'error': 'product_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)

            product = get_object_or_404(Product, id=product_id)

            # Проверяем наличие товара на складе
            if quantity > product.available_quantity:
                return Response(
                    {'error': f'Доступно только {product.available_quantity} единиц'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Ищем товар с таким же размером в корзине
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            serializer = self.get_serializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            print("Ошибка в add_item:", str(e))
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """
        Изменение количества товара в корзине.
        """
        cart = self.get_object()
        cart_item_id = request.data.get('cart_item_id')
        quantity = request.data.get('quantity')

        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart=cart)

        if quantity <= 0:
            cart_item.delete()
        else:
            if quantity > cart_item.product.available_quantity:
                return Response(
                    {'error': f'Доступно только {cart_item.product.available_quantity} единиц'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.quantity = quantity
            cart_item.save()

        return Response(self.get_serializer(cart).data)
    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        cart = self.get_object()
        cart_item_id = request.data.get('cart_item_id')
        CartItem.objects.filter(id=cart_item_id, cart=cart).delete()
        return Response({'status': 'ok'})
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """
        Очистка корзины.
        """
        cart = self.get_object()
        cart.items.all().delete()
        return Response(self.get_serializer(cart).data)

from decimal import Decimal

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра заказов.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items').order_by('-created_at')

    @action(detail=False, methods=['post'])
    def create_order(self, request):
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            
            # Начисляем бонусы (5% от суммы заказа)
            bonus_earned = int(order.total_price * Decimal('0.05'))
            order.bonus_earned = bonus_earned
            order.save()
            
            # Добавляем бонусы пользователю
            if order.user:
                order.user.bonus_points += bonus_earned
                order.user.save()
            
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_address(self, request, pk=None):
        """
        Изменение адреса доставки (только для новых и подтверждённых заказов).
        """
        order = self.get_object()
        
        # Проверяем, можно ли изменять адрес
        if order.status not in [Order.Status.NEW, Order.Status.CONFIRMED]:
            return Response(
                {'error': 'Нельзя изменить адрес для заказа в текущем статусе'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_address = request.data.get('delivery_address')
        if not new_address:
            return Response(
                {'error': 'Укажите новый адрес доставки'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.delivery_address = new_address
        order.save()
        
        return Response({'status': 'ok', 'delivery_address': new_address})
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Отмена заказа (только для новых и подтверждённых заказов).
        """
        order = self.get_object()
        
        # Проверяем, можно ли отменить заказ
        if order.status not in [Order.Status.NEW, Order.Status.CONFIRMED]:
            return Response(
                {'error': 'Нельзя отменить заказ в текущем статусе'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = Order.Status.CANCELLED
        order.save()
        
        # Возвращаем товары на склад
        for item in order.items.all():
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.save()
        
        return Response({'status': 'ok'})

class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet для отзывов.
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Показываем только промодерированные отзывы (всем) и все отзывы (автору и админу)
        user = self.request.user
        if user.is_staff:
            return Review.objects.all().order_by('-created_at')
        return Review.objects.filter(moderated=True).order_by('-created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class WishlistViewSet(viewsets.ModelViewSet):
    """
    ViewSet для избранного.
    """
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).order_by('-added_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

def home(request):
    """Главная страница"""
    return render(request, 'shop/home.html')

def catalog(request):
    """Страница каталога"""
    return render(request, 'shop/catalog.html')

def cart_page(request):
    """Страница корзины"""
    return render(request, 'shop/cart.html')

@login_required
def profile(request):
    """Страница профиля пользователя"""
    return render(request, 'shop/profile.html')

@login_required
def orders(request):
    """Страница заказов"""
    return render(request, 'shop/orders.html')

@login_required
def favorites(request):
    """Страница избранного"""
    return render(request, 'shop/favorites.html')

def checkout_page(request):
    """Страница оформления заказа"""
    return render(request, 'shop/checkout.html')

def orders(request):
    """Страница моих заказов"""
    return render(request, 'shop/orders.html')

def about(request):
    """Страница О нас"""
    return render(request, 'shop/about.html')

def stores(request):
    """Страница магазинов и пунктов самовывоза"""
    return render(request, 'shop/stores.html')