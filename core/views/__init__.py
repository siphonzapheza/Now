# Import all views to make them accessible
from .auth_views import (
    StudentUserViewSet,
    UserRegistrationView,
    UserProfileView,
    EmailVerificationView,
    ResendVerificationView,
    UserStatsView
)

from .product_views import (
    ProductViewSet,
    ProductCategoryViewSet,
    ProductImageViewSet,
    ProductFavoriteViewSet,
    ProductSearchView
)

from .chat_views import (
    ConversationViewSet,
    MessageViewSet,
    MessageAttachmentViewSet,
    ConversationSearchView
)

__all__ = [
    # Auth views
    'StudentUserViewSet',
    'UserRegistrationView',
    'UserProfileView',
    'EmailVerificationView',
    'ResendVerificationView',
    'UserStatsView',
    
    # Product views
    'ProductViewSet',
    'ProductCategoryViewSet',
    'ProductImageViewSet',
    'ProductFavoriteViewSet',
    'ProductSearchView',
    
    # Chat views
    'ConversationViewSet',
    'MessageViewSet',
    'MessageAttachmentViewSet',
    'ConversationSearchView',
]