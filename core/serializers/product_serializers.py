from rest_framework import serializers
from django.db import transaction
from ..models import ProductCategory, Product, ProductImage, ProductFavorite
from .user_serializers import StudentUserListSerializer


class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories"""
    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon',
            'parent', 'children', 'is_active', 'product_count'
        ]

    def get_children(self, obj):
        """Get child categories"""
        if obj.children.exists():
            return ProductCategorySerializer(
                obj.children.filter(is_active=True),
                many=True,
                context=self.context
            ).data
        return []

    def get_product_count(self, obj):
        """Get active product count for category"""
        return obj.products.filter(status='active').count()


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = [
            'id', 'image', 'image_url', 'alt_text',
            'is_primary', 'order'
        ]

    def get_image_url(self, obj):
        """Get full URL for image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product list view"""
    seller_info = StudentUserListSerializer(source='seller', read_only=True)
    category_info = ProductCategorySerializer(source='category', read_only=True)
    main_image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    price_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'price', 'price_display', 'original_price',
            'condition', 'status', 'is_negotiable', 'is_featured',
            'is_urgent', 'main_image', 'seller_info', 'category_info',
            'campus_area', 'view_count', 'favorite_count',
            'created_at', 'updated_at', 'is_favorited'
        ]

    def get_main_image(self, obj):
        """Get main product image"""
        main_image = obj.get_main_image()
        if main_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(main_image.image.url)
            return main_image.image.url
        return None

    def get_is_favorited(self, obj):
        """Check if current user has favorited this product"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ProductFavorite.objects.filter(
                user=request.user,
                product=obj
            ).exists()
        return False

    def get_price_display(self, obj):
        """Format price for display"""
        return f"R{obj.price:,.2f}"


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for product detail view"""
    seller_info = StudentUserListSerializer(source='seller', read_only=True)
    category_info = ProductCategorySerializer(source='category', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    price_display = serializers.SerializerMethodField()
    original_price_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'description', 'price', 'price_display',
            'original_price', 'original_price_display', 'condition',
            'status', 'is_negotiable', 'is_featured', 'is_urgent',
            'pickup_location', 'campus_area', 'pickup_only',
            'delivery_fee', 'delivery_radius', 'expires_at',
            'seller_info', 'category_info', 'images',
            'view_count', 'favorite_count', 'inquiry_count',
            'created_at', 'updated_at', 'is_favorited', 'is_owner'
        ]

    def get_is_favorited(self, obj):
        """Check if current user has favorited this product"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ProductFavorite.objects.filter(
                user=request.user,
                product=obj
            ).exists()
        return False

    def get_is_owner(self, obj):
        """Check if current user is the product owner"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.seller == request.user
        return False

    def get_price_display(self, obj):
        """Format price for display"""
        return f"R{obj.price:,.2f}"

    def get_original_price_display(self, obj):
        """Format original price for display"""
        if obj.original_price:
            return f"R{obj.original_price:,.2f}"
        return None


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating products"""
    images = ProductImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text="Upload multiple images for the product"
    )
    
    class Meta:
        model = Product
        fields = [
            'title', 'description', 'price', 'original_price',
            'condition', 'category', 'is_negotiable',
            'pickup_location', 'campus_area', 'pickup_only',
            'delivery_fee', 'expires_at',
            'is_urgent', 'tags', 'images', 'uploaded_images'  # Added 'tags'
        ]
    
    def validate_price(self, value):
        """Validate price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value
    
    def validate_original_price(self, value):
        """Validate original price if provided"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Original price must be greater than 0")
        return value
    
    def validate_category(self, value):
        """Validate category exists"""
        if not value:
            raise serializers.ValidationError("Category is required")
        
        # Check if category exists and is active
        from .models import ProductCategory  # Import here to avoid circular imports
        try:
            category = ProductCategory.objects.get(id=value.id if hasattr(value, 'id') else value)
            if not category.is_active:
                raise serializers.ValidationError("Selected category is not active")
        except ProductCategory.DoesNotExist:
            raise serializers.ValidationError("Selected category does not exist")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        price = attrs.get('price')
        original_price = attrs.get('original_price')
        
        if original_price and price and price > original_price:
            raise serializers.ValidationError({
                'price': 'Sale price cannot be higher than original price'
            })
        
        # Validate delivery settings
        pickup_only = attrs.get('pickup_only', True)
        delivery_fee = attrs.get('delivery_fee')
        
        if not pickup_only and delivery_fee is None:
            raise serializers.ValidationError({
                'delivery_fee': 'Delivery fee is required when delivery is offered'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create product with images"""
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        # Set seller to current user
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['seller'] = request.user
        
        # Set default status
        validated_data['status'] = 'active'
        
        with transaction.atomic():
            product = Product.objects.create(**validated_data)
            
            # Create images
            for i, image in enumerate(uploaded_images):
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=(i == 0),  # First image is primary
                    order=i
                )
        
        return product
    
    def update(self, instance, validated_data):
        """Update product with images"""
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        with transaction.atomic():
            # Update product fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            # Handle new images if provided
            if uploaded_images:
                # Get current image count to set proper order
                current_count = instance.images.count()
                
                for i, image in enumerate(uploaded_images):
                    ProductImage.objects.create(
                        product=instance,
                        image=image,
                        is_primary=(current_count == 0 and i == 0),
                        order=current_count + i
                    )
        
        return instance

    def update(self, instance, validated_data):
        """Update product with images"""
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        with transaction.atomic():
            # Update product fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            # Handle new images if provided
            if uploaded_images:
                # Get current image count to set proper order
                current_count = instance.images.count()
                
                for i, image in enumerate(uploaded_images):
                    ProductImage.objects.create(
                        product=instance,
                        image=image,
                        is_primary=(current_count == 0 and i == 0),
                        order=current_count + i
                    )
        
        return instance


class ProductFavoriteSerializer(serializers.ModelSerializer):
    """Serializer for product favorites"""
    product_info = ProductListSerializer(source='product', read_only=True)
    
    class Meta:
        model = ProductFavorite
        fields = ['id', 'product', 'product_info', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def create(self, validated_data):
        """Create favorite with current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class ProductSearchSerializer(serializers.Serializer):
    """Serializer for product search parameters"""
    q = serializers.CharField(required=False, help_text="Search query")
    category = serializers.IntegerField(required=False, help_text="Category ID")
    condition = serializers.ChoiceField(
        choices=Product.CONDITION_CHOICES,
        required=False,
        help_text="Product condition"
    )
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False, help_text="Minimum price"
    )
    max_price = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False, help_text="Maximum price"
    )
    campus_area = serializers.CharField(required=False, help_text="Campus area")
    is_negotiable = serializers.BooleanField(required=False, help_text="Negotiable items only")
    ordering = serializers.ChoiceField(
        choices=[
            ('created_at', 'Newest'),
            ('-created_at', 'Oldest'),
            ('price', 'Price: Low to High'),
            ('-price', 'Price: High to Low'),
            ('-view_count', 'Most Viewed'),
            ('-favorite_count', 'Most Favorited'),
        ],
        required=False,
        default='-created_at',
        help_text="Sort order"
    )


class ProductStatsSerializer(serializers.Serializer):
    """Serializer for product statistics"""
    total_products = serializers.IntegerField()
    active_products = serializers.IntegerField()
    sold_products = serializers.IntegerField()
    total_views = serializers.IntegerField()
    total_favorites = serializers.IntegerField()
    total_inquiries = serializers.IntegerField()
    average_price = serializers.DecimalField(max_digits=10, decimal_places=2)