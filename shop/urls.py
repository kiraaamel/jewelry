from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views

# Создаём роутер для ViewSet'ов
router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'cart', views.CartViewSet, basename='cart')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'reviews', views.ReviewViewSet, basename='review')
router.register(r'favorites', views.WishlistViewSet, basename='favorite')

urlpatterns = [
    # ========== HTML СТРАНИЦЫ ==========
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),          # ← ЭТО ДОЛЖНО БЫТЬ ПЕРВЫМ
    path('cart/', views.cart_page, name='cart'),
    path('profile/', views.profile, name='profile'),
    path('orders/', views.orders, name='orders'),
    path('favorites/', views.favorites, name='favorites'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),  # ← РАСКОММЕНТИРУЙТЕ
    
    # ========== АУТЕНТИФИКАЦИЯ (HTML страницы) ==========
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterPageView.as_view(), name='register'),
    
    # ========== API ==========
    path('api/', include(router.urls)),
    
    # Аутентификация API
    path('api/auth/register/', views.RegisterView.as_view(), name='api_register'),
    path('api/auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/me/', views.UserProfileView.as_view(), name='user_profile'),
]