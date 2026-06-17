"""
Представления (views) для интернет-магазина Argentic Jewelry.

Содержит API ViewSet'ы для товаров, корзины, заказов, отзывов, избранного,
промокодов, а также HTML-страницы для рендеринга шаблонов.
"""

from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import models
from django.db.models import Avg, Value, FloatField, Q, Count
from django.db.models.functions import Coalesce
from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView
from allauth.account.views import SignupView
from django.contrib.admin.views.decorators import staff_member_required

from .models import (
    Category, Product, Cart, CartItem, Order, Review, Wishlist, User, Collection,
    PromoCode, PromoCodeUsage, OrderItem, ProductVariant
)
from .serializers import (
    CategorySerializer, ProductSerializer, CartSerializer, OrderSerializer,
    OrderCreateSerializer, ReviewSerializer, WishlistSerializer, UserSerializer,
    RegisterSerializer, CustomTokenObtainPairSerializer, CollectionSerializer,
    PromoCodeSerializer, ApplyPromoCodeSerializer
)
from .filters import ProductFilter


@login_required
@require_http_methods(["GET"])
def can_review_product(request: HttpRequest, product_id: int) -> JsonResponse:
    """
    Проверяет, может ли пользователь оставить отзыв на товар.

    Условия:
    1. Пользователь купил этот товар
    2. Заказ со статусом 'received' (Получен)
    3. Пользователь ещё не оставлял отзыв на этот товар

    Args:
        request: HTTP запрос
        product_id: ID товара

    Returns:
        JsonResponse с полями can_review, has_purchased, has_reviewed
    """
    has_purchased: bool = OrderItem.objects.filter(
        order__user=request.user,
        order__status=Order.Status.RECEIVED,
        product_id=product_id
    ).exists()

    has_reviewed: bool = Review.objects.filter(
        user=request.user,
        product_id=product_id
    ).exists()

    print(f"User: {request.user.email}")
    print(f"Product ID: {product_id}")
    print(f"Has purchased (received): {has_purchased}")
    print(f"Has reviewed: {has_reviewed}")

    return JsonResponse({
        'can_review': has_purchased and not has_reviewed,
        'has_purchased': has_purchased,
        'has_reviewed': has_reviewed
    })


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_product_review(request: HttpRequest) -> JsonResponse:
    """
    Создаёт новый отзыв на товар.

    Args:
        request: HTTP запрос (может быть multipart/form-data или JSON)

    Returns:
        JsonResponse с результатом создания отзыва
    """
    try:
        if request.content_type and 'multipart' in request.content_type:
            product_id: Optional[str] = request.POST.get('product')
            rating: Optional[str] = request.POST.get('rating')
            comment: Optional[str] = request.POST.get('comment')
            image = request.FILES.get('image')
        else:
            data = json.loads(request.body)
            product_id = data.get('product')
            rating = data.get('rating')
            comment = data.get('comment')
            image = None

        if not product_id or not rating or not comment:
            return JsonResponse({'error': 'Заполните все обязательные поля'}, status=400)

        rating_int: int = int(rating)
        if rating_int < 1 or rating_int > 5:
            return JsonResponse({'error': 'Оценка должна быть от 1 до 5'}, status=400)

        has_purchased: bool = OrderItem.objects.filter(
            order__user=request.user,
            order__status=Order.Status.RECEIVED,
            product_id=product_id
        ).exists()

        if not has_purchased:
            return JsonResponse({'error': 'Вы можете оставить отзыв только после получения заказа'}, status=400)

        has_reviewed: bool = Review.objects.filter(
            user=request.user,
            product_id=product_id
        ).exists()

        if has_reviewed:
            return JsonResponse({'error': 'Вы уже оставили отзыв на этот товар'}, status=400)

        review: Review = Review.objects.create(
            user=request.user,
            product_id=product_id,
            rating=rating_int,
            comment=comment,
            image=image,
            moderated=False
        )

        return JsonResponse({
            'id': review.id,
            'message': 'Спасибо за отзыв! Он будет опубликован после проверки модератором.'
        })

    except Exception as e:
        print(f"Error creating review: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


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
            Ответ после успешной регистрации
        """
        self.request.session['signup_first_name'] = form.cleaned_data.get('first_name', '')
        self.request.session['signup_last_name'] = form.cleaned_data.get('last_name', '')
        self.request.session['signup_phone'] = form.cleaned_data.get('phone', '')
        return super().form_valid(form)


def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Детальная страница товара.

    Args:
        request: HTTP запрос
        pk: ID товара

    Returns:
        Рендер страницы товара
    """
    product: Product = get_object_or_404(Product, id=pk, is_active=True)
    variants = product.variants.all()
    context: Dict[str, Any] = {
        'product': product,
        'variants': variants,
        'has_variants': variants.exists()
    }
    return render(request, 'shop/product_detail.html', context)


def index(request: HttpRequest) -> HttpResponse:
    """
    Индексная страница.

    Args:
        request: HTTP запрос

    Returns:
        Приветственное сообщение
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
            Текущий пользователь
        """
        return self.request.user


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для пользователей (только для админов)"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        """Возвращает всех пользователей, отсортированных по дате регистрации."""
        return User.objects.all().order_by('-date_joined')

    @action(detail=True, methods=['post'])
    def add_bonus(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Начисление бонусов пользователю.

        Args:
            request: HTTP запрос с полем bonus_points
            pk: ID пользователя

        Returns:
            Response с новым количеством бонусов
        """
        user: User = self.get_object()
        bonus: int = request.data.get('bonus_points', 0)

        if bonus > 0:
            user.bonus_points += bonus
            user.save()
            return Response({'status': 'ok', 'bonus_points': user.bonus_points})

        return Response({'error': 'Invalid bonus'}, status=status.HTTP_400_BAD_REQUEST)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для категорий (только чтение).
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet для товаров.
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = ProductFilter
    ordering_fields = ['price', 'created_at']
    search_fields = ['name', 'name_lower', 'description']

    def get_queryset(self):
        """
        Возвращает QuerySet товаров с учётом фильтрации по поиску и ids.
        """
        try:
            queryset = Product.objects.filter(is_active=True).select_related(
                'category', 'collection'
            ).annotate( 
                reviews_count=Count('reviews', filter=Q(reviews__moderated=True))
            )

            ids: Optional[str] = self.request.query_params.get('ids', None)
            if ids:
                ids_list: List[str] = ids.split(',')
                queryset = queryset.filter(id__in=ids_list)

            search: Optional[str] = self.request.query_params.get('search', None)
            if search:
                search_lower: str = search.lower()
                queryset = queryset.filter(name_lower__icontains=search_lower)

            return queryset
        except Exception as e:
            print(f"Error in get_queryset: {e}")
            return Product.objects.none()

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Обновление товара (PATCH) - для админ-панели"""
        partial: bool = kwargs.pop('partial', False)
        instance: Product = self.get_object()

        allowed_fields: List[str] = ['price', 'name', 'description', 'old_price', 'is_active']
        data: Dict[str, Any] = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def perform_update(self, serializer) -> None:
        """Выполняет обновление товара."""
        serializer.save()

    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        Возвращает список товаров с пагинацией.
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())

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
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['get'])
    def reviews(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Возвращает отзывы для конкретного товара.
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

    @action(detail=True, methods=['get'])
    def variants(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Возвращает все варианты (размеры) товара.
        """
        product: Product = self.get_object()
        variants = product.variants.all()
        from .serializers import ProductVariantSerializer
        serializer = ProductVariantSerializer(variants, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def bestsellers(self, request: Request) -> Response:
        """
        Возвращает товары, отсортированные по популярности (количество заказов).
        """
        products = Product.objects.filter(is_active=True).annotate(
            order_count=Count('orderitem', filter=Q(orderitem__order__status__in=['delivered', 'received']))
        ).order_by('-order_count')[:4]
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def apply_discount(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Применение скидки к товару (только для админов).
        """
        try:
            product: Product = self.get_object()
            discount = request.data.get('discount_percent', 0)

            if not isinstance(discount, (int, float)) or discount <= 0 or discount > 100:
                return Response({'error': 'Скидка должна быть числом от 1 до 100'}, status=status.HTTP_400_BAD_REQUEST)

            if not product.old_price:
                product.old_price = product.price

            product.price = product.price * (100 - discount) / 100
            product.save()

            return Response({
                'status': 'ok',
                'message': f'Скидка {discount}% применена к товару "{product.name}"',
                'new_price': float(product.price),
                'old_price': float(product.old_price)
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartViewSet(viewsets.GenericViewSet):
    """
    ViewSet для корзины (работает и для авторизованных, и для гостей).
    """
    serializer_class = CartSerializer
    permission_classes = [permissions.AllowAny]

    def get_session_key(self, request: Request) -> Optional[str]:
        """
        Получает или создаёт session_key для гостя.
        """
        if request.user.is_authenticated:
            return None
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key

    def get_object(self) -> Cart:
        """
        Возвращает корзину для авторизованного пользователя или гостя.
        """
        if self.request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=self.request.user)
            return cart
        else:
            session_key = self.get_session_key(self.request)

            try:
                cart = Cart.objects.get(session_key=session_key, user__isnull=True)
            except Cart.DoesNotExist:
                cart = Cart.objects.create(session_key=session_key)
            return cart

    def list(self, request: Request) -> Response:
        """Просмотр корзины"""
        try:
            cart = self.get_object()
            cart.items.all().order_by('-added_at')
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in cart list: {e}")
            return Response({'items': [], 'total_items': 0, 'total_price': 0})

    @action(detail=False, methods=['post'])
    def add_item(self, request: Request) -> Response:
        """Добавление товара в корзину"""
        try:
            print("=== ADD ITEM ===")
            print("User:", request.user)
            print("Data:", request.data)

            cart = self.get_object()
            variant_id = request.data.get('variant_id')
            quantity = int(request.data.get('quantity', 1))

            if not variant_id:
                return Response({'error': 'variant_id обязателен'}, status=400)

            variant = get_object_or_404(ProductVariant, id=variant_id)
            product = variant.product

            if not product.is_active:
                return Response({'error': 'Товар неактивен'}, status=400)

            if quantity > variant.available_quantity:
                return Response(
                    {'error': f'Доступно только {variant.available_quantity} шт. товара "{product.name}" (размер {variant.size})'},
                    status=400
                )

            cart_item = CartItem.objects.filter(cart=cart, variant=variant).first()

            if cart_item:
                new_quantity = cart_item.quantity + quantity
                if new_quantity > variant.available_quantity:
                    return Response(
                        {'error': f'В корзине уже {cart_item.quantity} шт. Доступно всего {variant.available_quantity} шт. Нельзя добавить больше'},
                        status=400
                    )
                cart_item.quantity = new_quantity
                cart_item.save()
            else:
                cart_item = CartItem.objects.create(
                    cart=cart,
                    product=product,
                    variant=variant,
                    quantity=quantity
                )

            serializer = self.get_serializer(cart)
            return Response(serializer.data)

        except Exception as e:
            print(f"Error in add_item: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['post'])
    def update_item(self, request: Request) -> Response:
        """Изменение количества товара в корзине"""
        try:
            cart = self.get_object()
            cart_item_id = request.data.get('cart_item_id')
            quantity = int(request.data.get('quantity'))

            cart_item = get_object_or_404(CartItem, id=cart_item_id, cart=cart)

            if quantity <= 0:
                cart_item.delete()
            else:
                if quantity > cart_item.variant.available_quantity:
                    return Response(
                        {'error': f'Доступно только {cart_item.variant.available_quantity} шт.'},
                        status=400
                    )
                cart_item.quantity = quantity
                cart_item.save()

            serializer = self.get_serializer(cart)
            return Response(serializer.data)

        except Exception as e:
            print(f"Error in update_item: {e}")
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['post'])
    def remove_item(self, request: Request) -> Response:
        """Удаление товара из корзины"""
        try:
            cart = self.get_object()
            cart_item_id = request.data.get('cart_item_id')
            CartItem.objects.filter(id=cart_item_id, cart=cart).delete()
            serializer = self.get_serializer(cart)
            return Response(serializer.data)

        except Exception as e:
            print(f"Error in remove_item: {e}")
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['post'])
    def clear(self, request: Request) -> Response:
        """Очистка корзины"""
        try:
            cart = self.get_object()
            cart.items.all().delete()
            serializer = self.get_serializer(cart)
            return Response(serializer.data)

        except Exception as e:
            print(f"Error in clear: {e}")
            return Response({'error': str(e)}, status=500)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра заказов.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Возвращает заказы текущего пользователя.
        """
        return Order.objects.filter(user=self.request.user).prefetch_related('items').order_by('-created_at') #заказы + позиции заказов

    @action(detail=False, methods=['post'])
    def create_order(self, request: Request) -> Response:
        """
        Создание нового заказа из корзины.

        Args:
            request: HTTP запрос с данными заказа

        Returns:
            Созданный заказ или ошибка
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
            request: HTTP запрос с новым адресом
            pk: ID заказа

        Returns:
            Статус операции
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
            request: HTTP запрос
            pk: ID заказа

        Returns:
            Статус операции
        """
        order: Order = self.get_object()

        if order.status not in [Order.Status.NEW, Order.Status.CONFIRMED]:
            return Response(
                {'error': 'Нельзя отменить заказ в текущем статусе'},
                status=status.HTTP_400_BAD_REQUEST
            )

        bonus_spent = 0

        if order.bonus_earned > 0 and order.user:
            bonus_to_remove = order.bonus_earned
            if order.user.bonus_points >= bonus_to_remove:
                order.user.bonus_points -= bonus_to_remove
                bonus_spent = bonus_to_remove
            else:
                bonus_spent = order.user.bonus_points
                order.user.bonus_points = 0
            order.user.save()
            request.session['bonus_cancelled'] = {
                'amount': bonus_spent,
                'order_number': order.order_number,
                'date': timezone.now().isoformat()
            }
        order.status = Order.Status.CANCELLED
        order.save()

        for item in order.items.all():
            if item.variant:
                item.variant.stock_quantity += item.quantity
                item.variant.save()

        return Response({
            'status': 'ok',
            'bonus_spent': bonus_spent,
            'order_number': order.order_number
        })

    @action(detail=True, methods=['get'])
    def get_pickup_code(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Получает или генерирует код для получения заказа.
        Доступен только для заказов со статусом DELIVERED.
        """
        order: Order = self.get_object()

        if order.status not in [Order.Status.DELIVERED, Order.Status.RECEIVED]:
            return Response(
                {'error': 'Код получения доступен только для доставленных заказов'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.regenerate_pickup_code()

        return Response({
            'pickup_code': order.pickup_code,
            'generated_at': order.code_generated_at,
            'expires_in': 600 - (timezone.now() - order.code_generated_at).total_seconds()
        })

    @action(detail=True, methods=['post'])
    def mark_as_received(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Отмечает заказ как полученный (для пользователя).

        Args:
            request: HTTP запрос
            pk: ID заказа

        Returns:
            Статус операции
        """
        order: Order = self.get_object()

        if order.status != Order.Status.DELIVERED:
            return Response(
                {'error': 'Заказ можно подтвердить как полученный только после доставки'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.mark_as_received()

        return Response({
            'status': 'ok',
            'message': 'Заказ отмечен как полученный',
            'received_at': order.delivered_at
        })


class AdminOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра заказов в админ-панели.
    Доступен только для сотрудников (is_staff=True).
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        """Возвращает ВСЕ заказы для админ-панели"""
        return Order.objects.all().prefetch_related('items', 'user').order_by('-created_at')

    @action(detail=True, methods=['post'])
    def update_status(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Обновление статуса заказа (только для админов).

        Args:
            request: HTTP запрос с полем status
            pk: ID заказа

        Returns:
            Статус операции
        """
        order: Order = self.get_object()
        new_status = request.data.get('status')

        if new_status in dict(Order.Status.choices):
            order.status = new_status
            order.save()
            return Response({'status': 'ok'})

        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet для отзывов.
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self) -> Review:
        user: User = self.request.user
        queryset = Review.objects.all().order_by('-created_at')
        
        public = self.request.query_params.get('public')
        if public is not None and public.lower() == 'true':
            return queryset.filter(moderated=True)
        
        moderated_param = self.request.query_params.get('moderated')
        if moderated_param is not None:
            if moderated_param.lower() == 'true':
                queryset = queryset.filter(moderated=True)
            elif moderated_param.lower() == 'false':
                queryset = queryset.filter(moderated=False)
        
        if user.is_staff:
            return queryset
        my_reviews = self.request.query_params.get('my_reviews')
        if my_reviews is not None and my_reviews.lower() == 'true':
            return queryset.filter(user=user)
        from django.db.models import Q
        return queryset.filter(Q(user=user) | Q(moderated=True))

    def get_serializer_context(self) -> Dict[str, Any]:
        """
        Добавляет request в контекст сериализатора.

        Returns:
            Контекст сериализатора
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def moderate(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Модерация отзыва (только для админов).

        Args:
            request: HTTP запрос с полем moderated
            pk: ID отзыва

        Returns:
            Статус операции
        """
        try:
            review_id = pk
            moderated = request.data.get('moderated', False)

            if isinstance(moderated, str):
                moderated = moderated.lower() == 'true'

            updated_count = Review.objects.filter(id=review_id).update(moderated=moderated)

            if updated_count == 0:
                return Response({'error': 'Отзыв не найден'}, status=status.HTTP_404_NOT_FOUND)

            return Response({
                'status': 'ok',
                'moderated': moderated,
                'message': 'Отзыв одобрен' if moderated else 'Отзыв снят с публикации'
            })
        except Exception as e:
            print(f"Error in moderate: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WishlistViewSet(viewsets.ModelViewSet):
    """
    ViewSet для избранного.
    """
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Возвращает избранное текущего пользователя.

        Returns:
            QuerySet избранного пользователя
        """
        return Wishlist.objects.filter(user=self.request.user).order_by('-added_at')

    def get_serializer_context(self) -> Dict[str, Any]:
        """
        Добавляет request в контекст сериализатора.

        Returns:
            Контекст сериализатора
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


def home(request: HttpRequest) -> HttpResponse:
    """
    Главная страница.

    Args:
        request: HTTP запрос

    Returns:
        Рендер главной страницы
    """
    from django.templatetags.static import static
    context = {'banner_image': static('shop/images/main_banner.jpeg')}
    return render(request, 'shop/home.html', context)


def catalog(request: HttpRequest) -> HttpResponse:
    """
    Страница каталога.

    Args:
        request: HTTP запрос

    Returns:
        Рендер страницы каталога
    """
    return render(request, 'shop/catalog.html')


def cart_page(request: HttpRequest) -> HttpResponse:
    """
    Страница корзины.

    Args:
        request: HTTP запрос

    Returns:
        Рендер страницы корзины
    """
    return render(request, 'shop/cart.html')


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """
    Страница профиля пользователя.

    Args:
        request: HTTP запрос

    Returns:
        Рендер страницы профиля
    """
    return render(request, 'shop/profile.html')


@login_required
def orders(request: HttpRequest) -> HttpResponse:
    """
    Страница заказов пользователя.

    Args:
        request: HTTP запрос

    Returns:
        Рендер страницы заказов
    """
    return render(request, 'shop/orders.html')


@login_required
def favorites(request: HttpRequest) -> HttpResponse:
    """
    Страница избранного пользователя.

    Args:
        request: HTTP запрос

    Returns:
        Рендер страницы избранного
    """
    return render(request, 'shop/favorites.html')


def checkout_page(request: HttpRequest) -> HttpResponse:
    """
    Страница оформления заказа.

    Args:
        request: HTTP запрос

    Returns:
        Рендер страницы оформления заказа
    """
    context = {
        'user': request.user
    }
    return render(request, 'shop/checkout.html', context)


def about(request: HttpRequest) -> HttpResponse:
    """
    Страница "О нас".

    Args:
        request: HTTP запрос

    Returns:
        Рендер страницы о компании
    """
    return render(request, 'shop/about.html')


def faq(request: HttpRequest) -> HttpResponse:
    """
    Страница часто задаваемых вопросов.

    Args:
        request: HTTP запрос

    Returns:
        Рендер страницы FAQ
    """
    return render(request, 'shop/faq.html')


def stores(request: HttpRequest) -> HttpResponse:
    """
    Страница магазинов и пунктов самовывоза.

    Args:
        request: HTTP запрос

    Returns:
        Рендер страницы магазинов
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
            request: HTTP запрос

        Returns:
            Список активных промокодов
        """
        now: datetime = timezone.now()
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
            request: HTTP запрос с кодом промокода и суммой заказа

        Returns:
            Результат применения промокода
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
            request: HTTP запрос

        Returns:
            Статус операции
        """
        request.session.pop('applied_promo', None)
        return Response({'message': 'Промокод удалён'})

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def create_promo(self, request: Request) -> Response:
        """
        Создание нового промокода (только для админов).

        Args:
            request: HTTP запрос с данными промокода

        Returns:
            Результат создания промокода
        """
        try:
            code: str = request.data.get('code', '').upper()
            discount_value = request.data.get('discount_value')
            valid_to = request.data.get('valid_to')
            discount_type: str = request.data.get('discount_type', 'percent')
            min_order_amount = request.data.get('min_order_amount', 0)
            max_discount_amount = request.data.get('max_discount_amount', None)
            only_new_users: bool = request.data.get('only_new_users', False)
            user_limit = request.data.get('user_limit', 1)

            if not code:
                return Response({'error': 'Код промокода обязателен'}, status=400)

            if not discount_value or float(discount_value) <= 0:
                return Response({'error': 'Скидка должна быть больше 0'}, status=400)

            if float(discount_value) > 100 and discount_type == 'percent':
                return Response({'error': 'Процент скидки не может быть больше 100'}, status=400)

            if PromoCode.objects.filter(code=code).exists():
                return Response({'error': 'Промокод с таким кодом уже существует'}, status=400)

            promo_code: PromoCode = PromoCode.objects.create(
                code=code,
                discount_type=discount_type,
                discount_value=float(discount_value),
                valid_from=timezone.now(),
                valid_to=valid_to if valid_to else timezone.now() + timezone.timedelta(days=30),
                min_order_amount=float(min_order_amount) if min_order_amount else 0,
                max_discount_amount=float(max_discount_amount) if max_discount_amount else None,
                only_new_users=only_new_users,
                user_limit=int(user_limit) if user_limit else 1,
                is_active=True
            )

            return Response({
                'status': 'ok',
                'message': f'Промокод "{code}" успешно создан',
                'promo_code': {
                    'id': promo_code.id,
                    'code': promo_code.code,
                    'discount_value': promo_code.discount_value,
                    'valid_to': promo_code.valid_to
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Error creating promo code: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для коллекций (только чтение).
    """
    queryset = Collection.objects.filter(is_active=True).order_by('order', 'name')
    serializer_class = CollectionSerializer
    permission_classes = [permissions.AllowAny]


@staff_member_required
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Админ-панель для управления магазином.
    Доступна только сотрудникам (is_staff=True).

    Args:
        request: HTTP запрос

    Returns:
        Рендер админ-панели
    """
    return render(request, 'shop/admin_dashboard.html')


def trigger_error(request):
    """Тестовая функция для проверки Sentry"""
    division_by_zero = 1 / 0