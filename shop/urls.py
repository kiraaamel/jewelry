from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views
from allauth.account import views as allauth_views  # ← добавить

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
    path('catalog/', views.catalog, name='catalog'),
    path('cart/', views.cart_page, name='cart'),
    path('checkout/', views.checkout_page, name='checkout'),
    path('profile/', views.profile, name='profile'),
    path('orders/', views.orders, name='orders'),
    path('favorites/', views.favorites, name='favorites'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    
    # ========== АУТЕНТИФИКАЦИЯ (allauth) ==========
    path('accounts/login/', allauth_views.LoginView.as_view(), name='account_login'),
    path('accounts/logout/', allauth_views.LogoutView.as_view(), name='account_logout'),
    path('accounts/signup/', allauth_views.SignupView.as_view(), name='account_signup'),
    path('accounts/confirm-email/<str:key>/', allauth_views.ConfirmEmailView.as_view(), name='account_confirm_email'),
    path('accounts/verification-sent/', allauth_views.EmailVerificationSentView.as_view(), name='account_email_verification_sent'),
    
    # ========== API ==========
    path('api/', include(router.urls)),
    path('api/auth/register/', views.RegisterView.as_view(), name='api_register'),
    path('api/auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/me/', views.UserProfileView.as_view(), name='user_profile'),
]