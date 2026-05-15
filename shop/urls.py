"""
URL-маршруты для интернет-магазина Argentic Jewelry.

Содержит маршруты для:
- HTML страниц (главная, каталог, корзина, оформление заказа, профиль и т.д.)
- Аутентификации (allauth)
- REST API (товары, категории, корзина, заказы, отзывы, избранное, промокоды, коллекции)
"""

from typing import List, Union
from django.urls import path, include
from rest_framework.routers import DefaultRouter, APIRootView
from . import views
from allauth.account import views as allauth_views
from .views import PromoCodeViewSet, CollectionViewSet, can_review_product, create_product_review

# Создаём роутер для API
router: DefaultRouter = DefaultRouter()
router.register(r'promo', PromoCodeViewSet, basename='promo')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'cart', views.CartViewSet, basename='cart')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'reviews', views.ReviewViewSet, basename='review')
router.register(r'favorites', views.WishlistViewSet, basename='favorite')
router.register(r'collections', CollectionViewSet, basename='collection')

# Список URL-маршрутов
urlpatterns: List[Union[path, include]] = [
    # ========== HTML СТРАНИЦЫ ==========
    # Главная страница и каталог
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),

    # Корзина и оформление заказа
    path('cart/', views.cart_page, name='cart'),
    path('checkout/', views.checkout_page, name='checkout'),

    # Личный кабинет пользователя
    path('profile/', views.profile, name='profile'),
    path('orders/', views.orders, name='orders'),
    path('favorites/', views.favorites, name='favorites'),

    # Товары и информационные страницы
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('about/', views.about, name='about'),
    path('stores/', views.stores, name='stores'),
    path('faq/', views.faq, name='faq'),


    # Все остальные маршруты allauth (сброс пароля и т.д.)
    path('accounts/', include('allauth.urls')),

    # ========== REST API ==========
    # Основные API маршруты (сгенерированы роутером)
    path('api/orders/can_review/<int:product_id>/', views.can_review_product, name='can_review_product'),
    path('api/reviews/create/', views.create_product_review, name='create_product_review'),
    path('api/', include(router.urls)),

    # Аутентификация API
    path('api/auth/register/', views.RegisterView.as_view(), name='api_register'),
    path('api/auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/me/', views.UserProfileView.as_view(), name='user_profile'),

    # Тестовый маршрут для Sentry (закомментирован)
    # path('sentry-debug/', views.trigger_error, name='sentry-debug'),
]