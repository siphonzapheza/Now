from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, F
from django.shortcuts import get_object_or_404

from ..models import Product, ProductCategory, ProductImage, ProductFavorite
from ..serializers.product_serializers import (
    ProductCategorySerializer,
    ProductImageSerializer,
    ProductFavoriteSerializer,
    ProductDetailSerializer,
    ProductStatsSerializer,
    ProductSearchSerializer,
    ProductFavoriteSerializer,
    ProductCreateUpdateSerializer,
)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product categories.
    """
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Return active categories ordered by name"""
        return ProductCategory.objects.filter(is_active=True).order_by('name')

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get products in this category"""
        category = self.get_object()
        products = Product.objects.filter(category=category, status='active')
        
        # Apply filters
        condition = request.query_params.get('condition')
        if condition:
            products = products.filter(condition=condition)
        
        min_price = request.query_params.get('min_price')
        if min_price:
            products = products.filter(price__gte=min_price)
        
        max_price = request.query_params.get('max_price')
        if max_price:
            products = products.filter(price__lte=max_price)
        
        location = request.query_params.get('location')
        if location:
            products = products.filter(location__icontains=location)
        
        products = products.order_by('-created_at')
        
        # Pagination
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductCategorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductCategorySerializer(products, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products.
    """
    queryset = Product.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'create':
            return ProductCreateUpdateSerializer
        elif self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductDetailSerializer

    def get_queryset(self):
        """Return products based on user and filters"""
        queryset = Product.objects.all()
        
        # FIXED: Remove the UNION that was causing the ORDER BY error
        if self.request.user.is_authenticated:
            # Show user's own products and active public products
            queryset = queryset.filter(
                Q(seller=self.request.user) | Q(status='active')
            )
        else:
            # For anonymous users, only show active products
            # FIXED: Changed from 'available' to 'active' to match your model
            queryset = queryset.filter(status='active')
        
        # Apply filters
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        condition = self.request.query_params.get('condition')
        if condition:
            queryset = queryset.filter(condition=condition)
        
        min_price = self.request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        
        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # FIXED: Changed from 'location' to 'pickup_location' to match your model
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(pickup_location__icontains=location)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search)
            )
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Set the seller to the current user"""
        serializer.save(seller=self.request.user)

    def perform_update(self, serializer):
        """Only allow seller to update their own products"""
        if serializer.instance.seller != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit your own products")
        serializer.save()

    def perform_destroy(self, instance):
        """Only allow seller to delete their own products"""
        if instance.seller != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own products")
        instance.delete()

    def retrieve(self, request, *args, **kwargs):
        """Get product detail and increment view count"""
        instance = self.get_object()

        if request.user != instance.seller:
            Product.objects.filter(id=instance.id).update(view_count=F('view_count') + 1)
            instance.refresh_from_db()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


    @action(detail=True, methods=['post'])
    def add_favorite(self, request, pk=None):
        """Add product to favorites"""
        product = self.get_object()
        
        if product.seller == request.user:
            return Response(
                {'error': 'You cannot favorite your own product'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        favorite, created = ProductFavorite.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if created:
            return Response({'message': 'Product added to favorites'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Product already in favorites'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def remove_favorite(self, request, pk=None):
        """Remove product from favorites"""
        product = self.get_object()
        
        try:
            favorite = ProductFavorite.objects.get(user=request.user, product=product)
            favorite.delete()
            return Response({'message': 'Product removed from favorites'}, status=status.HTTP_200_OK)
        except ProductFavorite.DoesNotExist:
            return Response(
                {'error': 'Product not in favorites'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def mark_sold(self, request, pk=None):
        """Mark product as sold"""
        product = self.get_object()
        
        if product.seller != request.user:
            return Response(
                {'error': 'You can only mark your own products as sold'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # FIXED: Use status field instead of is_available
        product.status = 'sold'  # or whatever status value you use for sold items
        product.save
        
        return Response({'message': 'Product marked as sold'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_available(self, request, pk=None):
        """Mark product as available again"""
        product = self.get_object()
        
        if product.seller != request.user:
            return Response(
                {'error': 'You can only manage your own products'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # FIXED: Use status field instead of is_available
        product.status = 'active'  # or whatever status value you use for active items
        product.save()
        
        return Response({'message': 'Product marked as available'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def my_products(self, request):
        """Get current user's products"""
        products = Product.objects.filter(seller=request.user).order_by('-created_at')
        
        # Apply status filter
        status_filter = request.query_params.get('status')
        if status_filter == 'available':
            products = products.filter(status='active')
        elif status_filter == 'sold':
            products = products.filter(is_available=False)
        
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductCategorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductCategorySerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_favorites(self, request):
        """Get current user's favorite products"""
        favorites = ProductFavorite.objects.filter(user=request.user).select_related('product')
        
         # FIXED: Use status instead of is_available
        products = [fav.product for fav in favorites if fav.product.status == 'active']
        
        serializer = ProductCategorySerializer(products, many=True)
        return Response(serializer.data)


class ProductImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product images.
    """
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """Return images for products owned by the user or public images"""
        return ProductImage.objects.filter(
            Q(product__seller=self.request.user) |
            Q(product__status='active')
        )

    def perform_create(self, serializer):
        """Only allow adding images to own products"""
        product = serializer.validated_data['product']
        if product.seller != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only add images to your own products")
        
        # Check image limit
        existing_images = ProductImage.objects.filter(product=product).count()
        max_images = getattr(settings, 'MARKETPLACE_SETTINGS', {}).get('MAX_PRODUCT_IMAGES', 5)
        
        if existing_images >= max_images:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(f"Maximum {max_images} images allowed per product")
        
        serializer.save()

    def perform_destroy(self, instance):
        """Only allow deleting images from own products"""
        if instance.product.seller != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete images from your own products")
        instance.delete()


class ProductFavoriteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product favorites.
    """
    serializer_class = ProductFavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return favorites for the current user"""
        return ProductFavorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Set the user to current user"""
        product = serializer.validated_data['product']
        
        if product.seller == self.request.user:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You cannot favorite your own product")
        
        serializer.save(user=self.request.user)


class ProductSearchView(viewsets.ViewSet):
    """
    Advanced product search functionality.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request):
        """Advanced search with multiple filters"""
        queryset = Product.objects.filter(status='active')
        
        # Text search
        q = request.query_params.get('q', '')
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(location__icontains=q) |
                Q(category__name__icontains=q)
            )
        
        # Category filter
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Condition filter
        condition = request.query_params.get('condition')
        if condition:
            conditions = condition.split(',')
            queryset = queryset.filter(condition__in=conditions)
        
        # Price range
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Location filter
        location = request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        # Seller filter
        seller = request.query_params.get('seller')
        if seller:
            queryset = queryset.filter(seller_id=seller)
        
        # Date filters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        # Sorting
        ordering = request.query_params.get('ordering', '-created_at')
        valid_orderings = ['created_at', '-created_at', 'price', '-price', 'title', '-title', 'views_count', '-views_count']
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProductCategorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductCategorySerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular products (most viewed)"""
        products = Product.objects.filter(status='active').order_by('-views_count')[:20]
        serializer = ProductCategorySerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently added products"""
        products = Product.objects.filter(status='active').order_by('-created_at')[:20]
        serializer = ProductCategorySerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products (you can implement your own logic)"""
        # For now, return products with high view counts and recent
        products = Product.objects.filter(
            status='active',
            views_count__gt=10
        ).order_by('-created_at')[:10]
        
        serializer = ProductCategorySerializer(products, many=True)
        return Response(serializer.data)