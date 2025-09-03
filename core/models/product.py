from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from PIL import Image
import os


class ProductCategory(models.Model):
    """Categories for products"""
    name = models.CharField(max_length=100, unique=True, help_text="Category name")
    slug = models.SlugField(unique=True, help_text="URL-friendly category name")
    description = models.TextField(max_length=300, blank=True, null=True, help_text="Category description")
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="Icon class name for frontend")

    # Hierarchy support
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='subcategories'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_categories'
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
        ordering = ['name']

    def __str__(self):
        return self.name



class Product(models.Model):
    """Main product model for marketplace listings"""
    
    # Basic product information
    title = models.CharField(
        max_length=200,
        help_text="Product title/name"
    )
    
    description = models.TextField(
        max_length=2000,
        help_text="Detailed product description"
    )
    
    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Price in local currency (ZAR)"
    )
    
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0.01)],
        help_text="Original price (optional, for showing discounts)"
    )
    
    # Product details
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.CASCADE,
        related_name='products'
    )
    
    CONDITION_CHOICES = [
        ('new', 'Brand New'),
        ('like_new', 'Like New'),
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ]
    
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default='good'
    )
    
    # Seller information
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products'
    )
    
    # Location and pickup
    pickup_location = models.CharField(
        max_length=200,
        help_text="Preferred pickup/meeting location"
    )
    
    campus_area = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Specific campus area for pickup"
    )
    
    is_negotiable = models.BooleanField(
        default=True,
        help_text="Whether price is negotiable"
    )
    
    # Delivery options
    pickup_only = models.BooleanField(
        default=True,
        help_text="Pickup only or delivery available"
    )
    
    delivery_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0.01)],
        help_text="Delivery fee if applicable"
    )
    
    # Product status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('sold', 'Sold'),
        ('reserved', 'Reserved'),
        ('inactive', 'Inactive'),
        ('flagged', 'Flagged'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    # Engagement metrics
    view_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times viewed"
    )
    
    favorite_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of users who favorited"
    )
    
    inquiry_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of inquiries received"
    )
    
    # Additional features
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured product (shown prominently)"
    )
    
    is_urgent = models.BooleanField(
        default=False,
        help_text="Urgent sale (seller needs to sell quickly)"
    )
    
    # Expiry
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the listing expires"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional metadata
    tags = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Comma-separated tags for better searchability"
    )
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['price']),
        ]
    
    def __str__(self):
        return f"{self.title} - R{self.price}"
    
    @property
    def is_available(self):
        """Check if product is available for purchase"""
        return self.status == 'active'
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage if original price is set"""
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100, 1)
        return 0
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def mark_as_sold(self):
        """Mark product as sold"""
        self.status = 'sold'
        self.save(update_fields=['status'])
    
    def get_main_image(self):
        """Get the main product image"""
        return self.images.filter(is_primary=True).first()
    
    def get_all_images(self):
        """Get all product images ordered by primary first"""
        return self.images.order_by('-is_primary', 'order')


class ProductImage(models.Model):
    """Model for product images"""
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    
    image = models.ImageField(
        upload_to='product_images/',
        help_text="Product image"
    )
    
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Alternative text for accessibility"
    )
    
    is_primary = models.BooleanField(
        default=False,
        help_text="Main product image"
    )
    
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['-is_primary', 'order']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
        ]
    
    def __str__(self):
        primary_text = " (Primary)" if self.is_primary else ""
        return f"{self.product.title} - Image {self.order}{primary_text}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True
            ).update(is_primary=False)
        
        super().save(*args, **kwargs)
        
        # Resize image to save storage
        self.resize_image()
    
    def resize_image(self):
        """Resize image to reasonable dimensions"""
        if self.image:
            img = Image.open(self.image.path)
            
            # Resize if too large
            if img.height > 800 or img.width > 800:
                output_size = (800, 800)
                img.thumbnail(output_size, Image.LANCZOS)
                img.save(self.image.path, optimize=True, quality=85)


class ProductFavorite(models.Model):
    """Model for users' favorite products"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_favorites'
        verbose_name = 'Product Favorite'
        verbose_name_plural = 'Product Favorites'
        unique_together = ['user', 'product']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} favorited {self.product.title}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update product favorite count
        self.product.favorite_count = self.product.favorited_by.count()
        self.product.save(update_fields=['favorite_count'])
    
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # Update product favorite count
        self.product.favorite_count = self.product.favorited_by.count()
        self.product.save(update_fields=['favorite_count'])