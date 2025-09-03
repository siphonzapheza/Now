

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils import timezone

class Conversation(models.Model):
    """Model for chat conversations between users"""
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        help_text="Users participating in this conversation"
    )
    related_product = models.ForeignKey(
        'core.Product',  # Adjust this to your product model if necessary
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='conversations',
        help_text="Product this conversation is about"
    )
    title = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'conversations'
        ordering = ['-last_message_at', '-created_at']

    def __str__(self):
        participants_list = ", ".join([user.username for user in self.participants.all()[:2]])
        return f"Conversation with: {participants_list}"

class Message(models.Model):
    """Model for individual messages within conversations"""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    MESSAGE_TYPES = [
        ('text', 'Text Message'),
        ('image', 'Image'),
        ('system', 'System Message'),
        ('product_inquiry', 'Product Inquiry'),
        ('price_offer', 'Price Offer'),
        ('meeting_request', 'Meeting Request'),
    ]
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(max_length=2000)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username}: {self.content[:20]}"