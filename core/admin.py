from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import (
    StudentUser, UserRating,
    ProductCategory, Product, ProductImage, ProductFavorite,
    Conversation, Message, MessageAttachment, ConversationParticipant
)


# User Administration
@admin.register(StudentUser)
class StudentUserAdmin(UserAdmin):
    """Custom admin for StudentUser"""
    list_display = ('email', 'first_name', 'last_name', 'university', 'verification_status', 'average_rating', 'is_active')
    list_filter = ('verification_status', 'university', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'student_id')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'university', 'student_id', 'phone_number', 'bio', 'campus_location')}),
        ('Verification', {'fields': ('verification_status', 'email_verified')}),
        ('Profile', {'fields': ('profile_picture', 'profile_picture_preview')}),
        ('Ratings & Activity', {
            'fields': ('average_rating', 'total_ratings', 'total_sales', 'total_purchases'),
            'classes': ('collapse',)
        }),
        ('Account Status', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_banned', 'ban_reason', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'university', 'password1', 'password2'),
        }),
    )

    readonly_fields = ('profile_picture_preview', 'average_rating', 'total_ratings', 'total_sales', 'total_purchases')

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="100" height="100" style="border-radius: 50%;" />', obj.profile_picture.url)
        return "No image"
    profile_picture_preview.short_description = "Profile Picture Preview"



@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    """Admin for user ratings"""
    list_display = ('rated_user', 'rater', 'rating', 'transaction_type', 'created_at')
    list_filter = ('rating', 'transaction_type', 'created_at')
    search_fields = ('rated_user__username', 'rater__username')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


# Product Administration
@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    """Admin for product categories"""
    list_display = ('name', 'slug', 'parent', 'is_active', 'product_count')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Products"


class ProductImageInline(admin.TabularInline):
    """Inline for product images"""
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'order', 'image_preview')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" />', obj.image.url)
        return "No image"
    image_preview.short_description = "Preview"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin for products"""
    list_display = ('title', 'seller', 'category', 'price', 'condition', 'status', 'view_count', 'created_at')
    list_filter = ('status', 'condition', 'category', 'is_featured', 'is_urgent', 'created_at')
    search_fields = ('title', 'description', 'seller__username')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'seller')
        }),
        ('Pricing & Condition', {
            'fields': ('price', 'original_price', 'condition', 'is_negotiable')
        }),
        ('Location & Delivery', {
            'fields': ('pickup_location', 'campus_area', 'pickup_only', 'delivery_fee')
        }),
        ('Status & Features', {
            'fields': ('status', 'is_featured', 'is_urgent', 'expires_at')
        }),
        ('Engagement', {
            'fields': ('view_count', 'favorite_count', 'inquiry_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('view_count', 'favorite_count', 'inquiry_count', 'created_at', 'updated_at')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """Admin for product images"""
    list_display = ('product', 'alt_text', 'is_primary', 'order', 'image_preview')
    list_filter = ('is_primary',)
    search_fields = ('product__title', 'alt_text')
    ordering = ('product', 'order')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" />', obj.image.url)
        return "No image"
    image_preview.short_description = "Preview"


@admin.register(ProductFavorite)
class ProductFavoriteAdmin(admin.ModelAdmin):
    """Admin for product favorites"""
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'product__title')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


# Chat Administration
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Admin for conversations"""
    list_display = ('conversation_info', 'is_active', 'last_message_at', 'message_count', 'created_at')
    list_filter = ('is_active', 'created_at', 'last_message_at')
    search_fields = ('related_product__title', 'title', 'participants__username')
    date_hierarchy = 'created_at'
    ordering = ('-last_message_at', '-created_at')
    filter_horizontal = ('participants',)
    
    def conversation_info(self, obj):
        participants = obj.participants.all()[:2]
        participant_names = ", ".join([user.username for user in participants])
        if obj.related_product:
            return f"{obj.related_product.title}: {participant_names}"
        return f"Chat: {participant_names}"
    conversation_info.short_description = "Conversation"
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "Messages"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin for messages"""
    list_display = ('conversation_info', 'sender', 'message_type', 'content_preview', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read', 'is_edited', 'is_deleted', 'created_at')
    search_fields = ('content', 'sender__username', 'conversation__related_product__title')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    def conversation_info(self, obj):
        participants = obj.conversation.participants.all()[:2]
        participant_names = " & ".join([user.username for user in participants])
        return participant_names
    conversation_info.short_description = "Conversation"
    
    def content_preview(self, obj):
        if obj.is_deleted:
            return "[Deleted message]"
        if len(obj.content) <= 30:
            return obj.content
        return f"{obj.content[:30]}..."
    content_preview.short_description = "Preview"


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    """Admin for message attachments"""
    list_display = ('message_info', 'file_name', 'file_type', 'file_size', 'created_at')
    list_filter = ('file_type', 'created_at')
    search_fields = ('file_name', 'message__content')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    def message_info(self, obj):
        return f"Message from {obj.message.sender.username}"
    message_info.short_description = "Message"


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    """Admin for conversation participants"""
    list_display = ('conversation_info', 'user', 'is_muted', 'is_archived', 'is_blocked', 'last_read_at', 'joined_at')
    list_filter = ('is_muted', 'is_archived', 'is_blocked', 'joined_at')
    search_fields = ('user__username', 'conversation__related_product__title')
    date_hierarchy = 'joined_at'
    ordering = ('-joined_at',)
    
    def conversation_info(self, obj):
        participants = obj.conversation.participants.all()[:2]
        participant_names = " & ".join([user.username for user in participants])
        return participant_names
    conversation_info.short_description = "Conversation"


# Customize admin site
admin.site.site_header = "Student Marketplace Administration"
admin.site.site_title = "Student Marketplace Admin"
admin.site.index_title = "Welcome to Student Marketplace Administration"