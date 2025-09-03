from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings
from PIL import Image
import os


class StudentUser(AbstractUser):
    """Custom user model for students with additional fields"""
    
    # University and student information
    university = models.CharField(
        max_length=200,
        help_text="Name of the university/institution"
    )
    
    student_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Student ID number"
    )
    
    # Contact information
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    
    # Profile information
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        help_text="Profile picture"
    )
    
    bio = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Brief description about yourself"
    )
    
    # Verification status
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    verification_status = models.CharField(
        max_length=10,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending',
        help_text="Email verification status"
    )
    
    email_verified = models.BooleanField(
        default=False,
        help_text="Whether email has been verified"
    )
    
    # Location preferences
    campus_location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Campus or preferred meeting location"
    )
    
    # Rating system
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Average rating from buyers/sellers"
    )
    
    total_ratings = models.PositiveIntegerField(
        default=0,
        help_text="Total number of ratings received"
    )
    
    # Activity tracking
    total_sales = models.PositiveIntegerField(
        default=0,
        help_text="Total number of successful sales"
    )
    
    total_purchases = models.PositiveIntegerField(
        default=0,
        help_text="Total number of purchases made"
    )
    
    # Account status
    is_banned = models.BooleanField(
        default=False,
        help_text="Whether user is banned from the platform"
    )
    
    ban_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for ban if applicable"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_users'
        verbose_name = 'Student User'
        verbose_name_plural = 'Student Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    def save(self, *args, **kwargs):
        # Resize profile picture if it's too large
        super().save(*args, **kwargs)
        if self.profile_picture:
            self.resize_profile_picture()
    
    def resize_profile_picture(self):
        """Resize profile picture to save storage"""
        if self.profile_picture:
            img = Image.open(self.profile_picture.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.profile_picture.path)
    
    @property
    def full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_verified(self):
        """Check if user is verified"""
        return self.verification_status == 'verified' and self.email_verified
    
    def update_rating(self, new_rating):
        """Update average rating with new rating"""
        total_score = self.average_rating * self.total_ratings
        self.total_ratings += 1
        self.average_rating = (total_score + new_rating) / self.total_ratings
        self.save()
    
    def can_post_product(self):
        """Check if user can post products"""
        return self.is_verified and not self.is_banned
    
    def get_student_email_domain(self):
        """Extract domain from email"""
        if self.email:
            return self.email.split('@')[1].lower()
        return None
    
    def is_valid_student_email(self):
        """Check if email domain is in allowed student domains"""
        domain = self.get_student_email_domain()
        if domain:
            return any(domain.endswith(allowed_domain) 
                      for allowed_domain in settings.STUDENT_EMAIL_DOMAINS)
        return False


class UserRating(models.Model):
    """Model for tracking individual ratings between users"""
    
    # Who rated whom
    rated_user = models.ForeignKey(
        StudentUser,
        on_delete=models.CASCADE,
        related_name='received_ratings',
        help_text="User being rated"
    )
    
    rater = models.ForeignKey(
        StudentUser,
        on_delete=models.CASCADE,
        related_name='given_ratings',
        help_text="User giving the rating"
    )
    
    # Rating details
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)],  # 1-5 stars
        help_text="Rating from 1 to 5 stars"
    )
    
    comment = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Optional comment about the transaction"
    )
    
    # Transaction context
    TRANSACTION_TYPES = [
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
        ('general', 'General Interaction'),
    ]
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        default='general'
    )
    
    # Related product (optional)
    related_product = models.ForeignKey(
        'Product',  # Forward reference since Product model comes next
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Product related to this rating"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_ratings'
        verbose_name = 'User Rating'
        verbose_name_plural = 'User Ratings'
        unique_together = ['rated_user', 'rater', 'related_product']  # Prevent duplicate ratings for same transaction
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.rater.username} rated {self.rated_user.username}: {self.rating} stars"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the rated user's average rating
        self.rated_user.update_rating(self.rating)