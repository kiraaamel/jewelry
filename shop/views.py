"""
Представления (views) для интернет-магазина Argentic Jewelry.

Содержит API ViewSet'ы для товаров, корзины, заказов, отзывов, избранного,
промокодов, а также HTML-страницы для рендеринга шаблонов.
"""

from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.db.models import Avg, Value, FloatField
from django.db.models.functions import Coalesce
from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView
from allauth.account.views import SignupView

from .models import (
    Category, Product, Cart, CartItem, Order, Review, Wishlist, User, Collection,
    PromoCode, PromoCodeUsage
)
from .serializers import (
    CategorySerializer, ProductSerializer, CartSerializer, OrderSerializer,
    OrderCreateSerializer, ReviewSerializer, WishlistSerializer, UserSerializer,
    RegisterSerializer, CustomTokenObtainPairSerializer, CollectionSerializer,
    PromoCodeSerializer, ApplyPromoCodeSerializer
)
from .filters import ProductFilter


class CustomSignupView(SignupView):
    """
    Кастомное представление регистрации для сохранения дополнительных полей.
    """

    def form_valid(self, form) -> HttpResponse:
        """
        Обрабатывает валидную форму регистрации.

        Args:
            form: Форма регистрации

        Returns:
            HttpResponse: Ответ после успешной регистрации
        """
        self.request.session['signup_first_name'] = form.cleaned_data.get('first_name', '')
        self.request.session['signup_last_name'] = form.cleaned_data.get('last_name', '')
        self.request.session['signup_phone'] = form.cleaned_data.get('phone', '')
        return super().form_valid(form)


def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Детальная страница товара.

    Args:
        request (HttpRequest): HTTP запрос
        pk (int): ID товара

    Returns:
        HttpResponse: Рендер страницы товара
    """
    product = get_object_or_404(Product, id=pk, is_active=True)
    context = {'product': product}
    return render(request, 'shop/product_detail.html', context)


def index(request: HttpRequest) -> HttpResponse:
    """
    Индексная страница.

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Приветственное сообщение
    """
    return HttpResponse("Добро пожаловать в ювелирный магазин!")


class RegisterView(generics.CreateAPIView):
    """
    Регистрация нового пользователя.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


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
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self) -> User:
        """
        Возвращает текущего авторизованного пользователя.

        Returns:
            User: Текущий пользователь
        """
        return self.request.user


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для категорий (только чтение).
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для товаров (только чтение).
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = ProductFilter
    ordering_fields = ['price', 'created_at']
    search_fields = ['name', 'name_lower', 'description']

    def get_queryset(self) -> Product:
        """
        Возвращает QuerySet товаров с учётом фильтрации по поиску и ids.

        Returns:
            QuerySet: Отфильтрованный QuerySet товаров
        """
        try:
            queryset = Product.objects.filter(is_active=True).select_related('category', 'collection')

            # Обработка ids параметра для отзывов
            ids: Optional[str] = self.request.query_params.get('ids', None)
            if ids:
                ids_list: List[str] = ids.split(',')
                queryset = queryset.filter(id__in=ids_list)

            # Поиск
            search: Optional[str] = self.request.query_params.get('search', None)
            if search:
                search_lower: str = search.lower()
                queryset = queryset.filter(name_lower__icontains=search_lower)

            return queryset
        except Exception as e:
            print(f"Error in get_queryset: {e}")
            return Product.objects.none()

    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        Возвращает список товаров с пагинацией.

        Args:
            request (Request): HTTP запрос

        Returns:
            Response: Ответ с пагинированным списком товаров
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())

            # Пагинация
            page_size: int = int(request.query_params.get('page_size', 9))
            page: int = int(request.query_params.get('page', 1))
            start: int = (page - 1) * page_size
            end: int = start + page_size

            total: int = queryset.count()
            paginated_queryset = queryset[start:end]

            serializer = self.get_serializer(paginated_queryset, many=True)

            return Response({
                'count': total,
                'next': f"/api/products/?page={page + 1}&page_size={page_size}" if end < total else None,
                'previous': f"/api/products/?page={page - 1}&page_size={page_size}" if page > 1 else None,
                'results': serializer.data
            })
        except Exception as e:
            print(f"Error in list: {e}")
            return Response({'error': str(e), 'results': []}, status=200)

    def get_serializer_context(self) -> Dict[str, Any]:
        """
        Добавляет request в контекст сериализатора.

        Returns:
            dict: Контекст сериализатора
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['get'])
    def reviews(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Возвращает отзывы для конкретного товара.

        Args:
            request (Request): HTTP запрос
            pk (int, optional): ID товара

        Returns:
            Response: Список отзывов
        """
        try:
            product: Product = self.get_object()
            reviews = product.reviews.filter(moderated=True).order_by('-created_at')
            for review in reviews:
                review.product_name = product.name
            serializer = ReviewSerializer(reviews, many=True, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class CartViewSet(viewsets.GenericViewSet):
    """
    ViewSet для корзины.
    """
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request: Request, *args, **kwargs) -> Response:
        """
        Обрабатывает запрос с CSRF cookie.

        Args:
            request (Request): HTTP запрос

        Returns:
            Response: Ответ
        """
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> Cart:
        """
        Возвращает корзину текущего пользователя.

        Returns:
            QuerySet: QuerySet корзины пользователя
        """
        return Cart.objects.filter(user=self.request.user)

    def get_object(self) -> Cart:
        """
        Возвращает или создаёт корзину для текущего пользователя.

        Returns:
            Cart: Объект корзины
        """
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def list(self, request: Request) -> Response:
        """
        Просмотр корзины.

        Args:
            request (Request): HTTP запрос

        Returns:
            Response: Данные корзины
        """
        cart: Cart = self.get_object()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request: Request) -> Response:
        """
        Добавление товара в корзину.

        Args:
            request (Request): HTTP запрос с данными товара

        Returns:
            Response: Обновлённые данные корзины или ошибка
        """
        try:
            cart: Cart = self.get_object()
            product_id: Optional[int] = request.data.get('product_id')
            quantity: int = int(request.data.get('quantity', 1))
            size: str = request.data.get('size', '')

            if not product_id:
                return Response({'error': 'product_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)

            product: Product = get_object_or_404(Product, id=product_id)

            if quantity > product.available_quantity:
                return Response(
                    {'error': f'Доступно только {product.available_quantity} единиц'},
                    status=status.HTTP_400_BAD_REQUEST
                )

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
    def update_item(self, request: Request) -> Response:
        """
        Изменение количества товара в корзине.

        Args:
            request (Request): HTTP запрос с cart_item_id и quantity

        Returns:
            Response: Обновлённые данные корзины
        """
        cart: Cart = self.get_object()
        cart_item_id: Optional[int] = request.data.get('cart_item_id')
        quantity: int = request.data.get('quantity')

        cart_item: CartItem = get_object_or_404(CartItem, id=cart_item_id, cart=cart)

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
    def remove_item(self, request: Request) -> Response:
        """
        Удаление товара из корзины.

        Args:
            request (Request): HTTP запрос с cart_item_id

        Returns:
            Response: Статус операции
        """
        cart: Cart = self.get_object()
        cart_item_id: Optional[int] = request.data.get('cart_item_id')
        CartItem.objects.filter(id=cart_item_id, cart=cart).delete()
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'])
    def clear(self, request: Request) -> Response:
        """
        Очистка корзины.

        Args:
            request (Request): HTTP запрос

        Returns:
            Response: Очищенная корзина
        """
        cart: Cart = self.get_object()
        cart.items.all().delete()
        return Response(self.get_serializer(cart).data)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра заказов.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Order:
        """
        Возвращает заказы текущего пользователя.

        Returns:
            QuerySet: Заказы пользователя
        """
        return Order.objects.filter(user=self.request.user).prefetch_related('items').order_by('-created_at')

    @action(detail=False, methods=['post'])
    def create_order(self, request: Request) -> Response:
        """
        Создание нового заказа из корзины.

        Args:
            request (Request): HTTP запрос с данными заказа

        Returns:
            Response: Созданный заказ или ошибка
        """
        try:
            print("=== CREATE ORDER REQUEST ===")
            print("User:", request.user)
            print("Data:", request.data)

            serializer = OrderCreateSerializer(data=request.data, context={'request': request})

            if serializer.is_valid():
                order: Order = serializer.save()

                bonus_earned: int = int(order.total_price * Decimal('0.05'))
                order.bonus_earned = bonus_earned
                order.save()

                if order.user:
                    order.user.bonus_points += bonus_earned
                    order.user.save()

                return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
            else:
                print("Serializer errors:", serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print("ERROR:", str(e))
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def update_address(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Изменение адреса доставки заказа (только для новых и подтверждённых).

        Args:
            request (Request): HTTP запрос с новым адресом
            pk (int, optional): ID заказа

        Returns:
            Response: Статус операции
        """
        order: Order = self.get_object()

        if order.status not in [Order.Status.NEW, Order.Status.CONFIRMED]:
            return Response(
                {'error': 'Нельзя изменить адрес для заказа в текущем статусе'},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_address: Optional[str] = request.data.get('delivery_address')
        if not new_address:
            return Response(
                {'error': 'Укажите новый адрес доставки'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.delivery_address = new_address
        order.save()

        return Response({'status': 'ok', 'delivery_address': new_address})

    @action(detail=True, methods=['post'])
    def cancel(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Отмена заказа (только для новых и подтверждённых).

        Args:
            request (Request): HTTP запрос
            pk (int, optional): ID заказа

        Returns:
            Response: Статус операции
        """
        order: Order = self.get_object()

        if order.status not in [Order.Status.NEW, Order.Status.CONFIRMED]:
            return Response(
                {'error': 'Нельзя отменить заказ в текущем статусе'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = Order.Status.CANCELLED
        order.save()

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

    def get_queryset(self) -> Review:
        """
        Возвращает отзывы с учётом прав пользователя.

        Returns:
            QuerySet: Отзывы
        """
        user: User = self.request.user
        if user.is_staff:
            return Review.objects.all().order_by('-created_at')
        return Review.objects.filter(moderated=True).order_by('-created_at')

    def get_serializer_context(self) -> Dict[str, Any]:
        """
        Добавляет request в контекст сериализатора.

        Returns:
            dict: Контекст сериализатора
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class WishlistViewSet(viewsets.ModelViewSet):
    """
    ViewSet для избранного.
    """
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> Wishlist:
        """
        Возвращает избранное текущего пользователя.

        Returns:
            QuerySet: Избранное пользователя
        """
        return Wishlist.objects.filter(user=self.request.user).order_by('-added_at')

    def get_serializer_context(self) -> Dict[str, Any]:
        """
        Добавляет request в контекст сериализатора.

        Returns:
            dict: Контекст сериализатора
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


def home(request: HttpRequest) -> HttpResponse:
    """
    Главная страница.

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Рендер главной страницы
    """
    from django.templatetags.static import static
    context = {'banner_image': static('shop/images/main_banner.jpeg')}
    return render(request, 'shop/home.html', context)


def catalog(request: HttpRequest) -> HttpResponse:
    """
    Страница каталога.

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Рендер страницы каталога
    """
    return render(request, 'shop/catalog.html')


def cart_page(request: HttpRequest) -> HttpResponse:
    """
    Страница корзины.

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Рендер страницы корзины
    """
    return render(request, 'shop/cart.html')


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """
    Страница профиля пользователя.

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Рендер страницы профиля
    """
    return render(request, 'shop/profile.html')


@login_required
def orders(request: HttpRequest) -> HttpResponse:
    """
    Страница заказов пользователя.

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Рендер страницы заказов
    """
    return render(request, 'shop/orders.html')


@login_required
def favorites(request: HttpRequest) -> HttpResponse:
    """
    Страница избранного пользователя.

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Рендер страницы избранного
    """
    return render(request, 'shop/favorites.html')


def checkout_page(request: HttpRequest) -> HttpResponse:
    """
    Страница оформления заказа.

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Рендер страницы оформления заказа
    """
    return render(request, 'shop/checkout.html')


def about(request: HttpRequest) -> HttpResponse:
    """
    Страница "О нас".

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Рендер страницы о компании
    """
    return render(request, 'shop/about.html')


def faq(request: HttpRequest) -> HttpResponse:
    """
    Страница часто задаваемых вопросов.

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Рендер страницы FAQ
    """
    return render(request, 'shop/faq.html')


def stores(request: HttpRequest) -> HttpResponse:
    """
    Страница магазинов и пунктов самовывоза.

    Args:
        request (HttpRequest): HTTP запрос

    Returns:
        HttpResponse: Рендер страницы магазинов
    """
    return render(request, 'shop/stores.html')


class PromoCodeViewSet(viewsets.GenericViewSet):
    """
    ViewSet для работы с промокодами.
    """
    permission_classes = [permissions.AllowAny]

    def list(self, request: Request) -> Response:
        """
        Получение списка активных промокодов.

        Args:
            request (Request): HTTP запрос

        Returns:
            Response: Список активных промокодов
        """
        now: DateTime = timezone.now()
        promoCodes = PromoCode.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now
        ).order_by('-discount_value')

        serializer = PromoCodeSerializer(promoCodes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def apply(self, request: Request) -> Response:
        """
        Применение промокода.

        Args:
            request (Request): HTTP запрос с кодом промокода и суммой заказа

        Returns:
            Response: Результат применения промокода
        """
        serializer = ApplyPromoCodeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            return Response({
                'valid': True,
                'discount_amount': float(serializer.validated_data['discount_amount']),
                'promo_code': serializer.validated_data['promo'].code,
                'message': f'Промокод применён! Скидка: {serializer.validated_data["discount_amount"]} ₽'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def remove(self, request: Request) -> Response:
        """
        Удаление применённого промокода.

        Args:
            request (Request): HTTP запрос

        Returns:
            Response: Статус операции
        """
        request.session.pop('applied_promo', None)
        return Response({'message': 'Промокод удалён'})


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для коллекций (только чтение).
    """
    queryset = Collection.objects.filter(is_active=True).order_by('order', 'name')
    serializer_class = CollectionSerializer
    permission_classes = [permissions.AllowAny]
    
#def trigger_error(request):
#    """Тестовая функция для проверки Sentry"""
#    division_by_zero = 1 / 0