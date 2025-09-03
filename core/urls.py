from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.chat_views import ConversationViewSet, MessageViewSet, MessageAttachmentViewSet

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Import all viewsets
from .views.auth_views import (
    StudentUserViewSet, 
    UserRegistrationView, 
    UserProfileView,
    EmailVerificationView,
    CustomTokenObtainPairView
)
from .views.product_views import (
    ProductViewSet,
    ProductCategoryViewSet,
    ProductImageViewSet,
    ProductFavoriteViewSet,
    ProductSearchView
)
from .views.chat_views import (
    ConversationViewSet,
    MessageViewSet,
    MessageAttachmentViewSet,
    ConversationSearchView
)

# Create router and register viewsets
router = DefaultRouter()

# User management
router.register(r'users', StudentUserViewSet)

# Product management
router.register(r'products', ProductViewSet)
router.register(r'categories', ProductCategoryViewSet)
router.register(r'product-images', ProductImageViewSet)
router.register(r'favorites', ProductFavoriteViewSet, basename='favorites')
router.register(r'product-search', ProductSearchView, basename='product-search')

# Chat system
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'attachments', MessageAttachmentViewSet, basename='attachment')
router.register(r'conversation-search', ConversationSearchView, basename='conversation-search')
router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'attachments', MessageAttachmentViewSet, basename='attachment')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/register/', UserRegistrationView.as_view(), name='user_register'),
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    path('auth/verify-email/', EmailVerificationView.as_view(), name='verify_email'),
    path('api/chat/', include(router.urls)),
    path('api/', include('chat.urls')),
    
    # Include router URLs
    path('', include(router.urls)),
    
    # Additional custom endpoints can be added here
]

# Optional: Add API versioning
app_name = 'core'