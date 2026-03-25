from django.shortcuts import render

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

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для товаров (только чтение, фильтрация).
    """
    queryset = Product.objects.select_related('category').prefetch_related('reviews').all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = ProductFilter  # ← используем кастомный фильтр
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'average_rating']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class CartViewSet(viewsets.GenericViewSet):
    """
    ViewSet для корзины.
    """
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

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
        cart = self.get_object()
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        product = get_object_or_404(Product, id=product_id)

        # Проверяем наличие товара на складе
        if quantity > product.available_quantity:
            return Response(
                {'error': f'Доступно только {product.available_quantity} единиц'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return Response(self.get_serializer(cart).data)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """
        Изменение количества товара в корзине.
        """
        cart = self.get_object()
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')

        cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)

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
        """
        Удаление товара из корзины.
        """
        cart = self.get_object()
        product_id = request.data.get('product_id')

        CartItem.objects.filter(cart=cart, product_id=product_id).delete()
        return Response(self.get_serializer(cart).data)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """
        Очистка корзины.
        """
        cart = self.get_object()
        cart.items.all().delete()
        return Response(self.get_serializer(cart).data)

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
        """
        Создание заказа.
        """
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

