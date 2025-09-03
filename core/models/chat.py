from django.db import models
from django.conf import settings
from django.utils import timezone


class Conversation(models.Model):
    """Model for chat conversations between users"""
    
    # Participants in the conversation
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        help_text="Users participating in this conversation"
    )
    
    # Related product (conversations usually start from a product inquiry)
    related_product = models.ForeignKey(
        'core.Product',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='conversations',
        help_text="Product this conversation is about"
    )
    
    # Conversation metadata
    title = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Optional conversation title"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether conversation is active"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of last message"
    )
    
    class Meta:
        db_table = 'conversations'
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['related_product']),
            models.Index(fields=['last_message_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        participants_list = ", ".join([user.username for user in self.participants.all()[:2]])
        if self.related_product:
            return f"Conversation about {self.related_product.title} - {participants_list}"
        return f"Conversation - {participants_list}"
    
    def get_other_participant(self, user):
        """Get the other participant in a 2-person conversation"""
        return self.participants.exclude(id=user.id).first()
    
    def get_last_message(self):
        """Get the most recent message in the conversation"""
        return self.messages.order_by('-created_at').first()
    
    def mark_as_read_for_user(self, user):
        """Mark all messages as read for a specific user"""
        self.messages.filter(
            is_read=False
        ).exclude(sender=user).update(is_read=True, read_at=timezone.now())
    
    def get_unread_count_for_user(self, user):
        """Get count of unread messages for a specific user"""
        return self.messages.filter(
            is_read=False
        ).exclude(sender=user).count()
    
    def update_last_message_time(self):
        """Update the last message timestamp"""
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at'])


class Message(models.Model):
    """Model for individual messages within conversations"""
    
    # Message relationships
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
    
    # Message content
    MESSAGE_TYPES = [
        ('text', 'Text Message'),
        ('image', 'Image'),
        ('system', 'System Message'),
        ('product_inquiry', 'Product Inquiry'),
        ('price_offer', 'Price Offer'),
        ('meeting_request', 'Meeting Request'),
    ]
    
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPES,
        default='text'
    )
    
    content = models.TextField(
        max_length=2000,
        help_text="Message content"
    )
    
    # Optional image attachment
    image = models.ImageField(
        upload_to='chat_images/',
        blank=True,
        null=True,
        help_text="Optional image attachment"
    )
    
    # For structured messages (offers, meeting requests)
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional structured data for special message types"
    )
    
    # Message status
    is_read = models.BooleanField(
        default=False,
        help_text="Whether message has been read by recipient"
    )
    
    is_edited = models.BooleanField(
        default=False,
        help_text="Whether message has been edited"
    )
    
    is_deleted = models.BooleanField(
        default=False,
        help_text="Whether message has been deleted (soft delete)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    read_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When message was read"
    )
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender']),
            models.Index(fields=['is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Message from {self.sender.username}: {content_preview}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update conversation's last message timestamp
        self.conversation.update_last_message_time()
    
    def mark_as_read(self):
        """Mark this message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class MessageAttachment(models.Model):
    """Model for additional file attachments to messages"""
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    file = models.FileField(
        upload_to='chat_attachments/',
        help_text="File attachment"
    )
    
    file_name = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )
    
    file_type = models.CharField(
        max_length=100,
        help_text="MIME type of the file"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'message_attachments'
        verbose_name = 'Message Attachment'
        verbose_name_plural = 'Message Attachments'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Attachment: {self.file_name}"


class ConversationParticipant(models.Model):
    """Model to track participant-specific conversation settings"""
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participant_settings'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_settings'
    )
    
    # Participant settings
    is_muted = models.BooleanField(
        default=False,
        help_text="Whether user has muted this conversation"
    )
    
    is_archived = models.BooleanField(
        default=False,
        help_text="Whether user has archived this conversation"
    )
    
    is_blocked = models.BooleanField(
        default=False,
        help_text="Whether user has blocked the other participant"
    )
    
    # Tracking
    last_read_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When user last read messages in this conversation"
    )
    
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'conversation_participants'
        verbose_name = 'Conversation Participant'
        verbose_name_plural = 'Conversation Participants'
        unique_together = ['conversation', 'user']
        ordering = ['joined_at']
    
    def __str__(self):
        return f"{self.user.username} in conversation {self.conversation.id}"


# Helper function to create or get conversation between two users
def get_or_create_conversation(user1, user2, product=None):
    """
    Get existing conversation between two users for a specific product,
    or create a new one if it doesn't exist.
    """
    # First try to find existing conversation with the same participants and product
    existing_conversations = Conversation.objects.filter(
        participants=user1,
        related_product=product
    ).filter(participants=user2)
    
    if existing_conversations.exists():
        return existing_conversations.first(), False
    
    # Create new conversation
    conversation = Conversation.objects.create(related_product=product)
    conversation.participants.add(user1, user2)
    
    # Create participant settings
    ConversationParticipant.objects.create(
        conversation=conversation,
        user=user1
    )
    ConversationParticipant.objects.create(
        conversation=conversation,
        user=user2
    )
    
    return conversation, True