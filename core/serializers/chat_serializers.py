from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from ..models import Conversation, Message, MessageAttachment, ConversationParticipant
from .user_serializers import StudentUserListSerializer
from .product_serializers import ProductListSerializer


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer for conversation list view - FIXED to match frontend expectations"""
    other_participant = serializers.SerializerMethodField()
    related_product_info = ProductListSerializer(source='related_product', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'other_participant', 'related_product_info',
            'is_active', 'created_at', 'updated_at', 'last_message_at',
            'last_message', 'unread_count'
        ]

    def get_other_participant(self, obj):
        """Get the other participant info for frontend"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            other = obj.get_other_participant(request.user)
            if other:
                return {
                    'id': other.id,
                    'first_name': other.first_name,
                    'last_name': other.last_name,
                    'username': other.username,
                    'avatar': other.avatar.url if hasattr(other, 'avatar') and other.avatar else None,
                }
        return None

    def get_last_message(self, obj):
        """Get the last message in conversation"""
        last_msg = obj.get_last_message()
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content[:100] + '...' if len(last_msg.content) > 100 else last_msg.content,
                'message_type': last_msg.message_type,
                'sender': last_msg.sender.username,
                'created_at': last_msg.created_at.isoformat(),
                'is_read': last_msg.is_read
            }
        return None

    def get_unread_count(self, obj):
        """Get unread message count for current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count_for_user(request.user)
        return 0


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages - FIXED to match frontend expectations"""
    sender_info = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    is_own_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_info',
            'message_type', 'content', 'image', 'image_url',
            'metadata', 'is_read', 'is_edited', 'is_deleted',
            'created_at', 'updated_at', 'read_at',
            'is_own_message'
        ]
        read_only_fields = [
            'id', 'sender', 'sender_info', 'created_at', 'updated_at',
            'is_own_message'
        ]

    def get_sender_info(self, obj):
        """Get sender info for frontend"""
        if obj.sender:
            return {
                'id': obj.sender.id,
                'first_name': obj.sender.first_name,
                'last_name': obj.sender.last_name,
                'username': obj.sender.username,
                'avatar': obj.sender.avatar.url if hasattr(obj.sender, 'avatar') and obj.sender.avatar else None,
            }
        return None

    def get_image_url(self, obj):
        """Get full URL for message image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_is_own_message(self, obj):
        """Check if message belongs to current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender == request.user
        return False


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed conversation serializer with messages - FIXED to match frontend"""
    other_participant = serializers.SerializerMethodField()
    related_product_info = ProductListSerializer(source='related_product', read_only=True)
    messages = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'other_participant', 'related_product_info',
            'is_active', 'created_at', 'updated_at', 'last_message_at',
            'messages', 'unread_count'
        ]

    def get_other_participant(self, obj):
        """Get the other participant info"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            other = obj.get_other_participant(request.user)
            if other:
                return {
                    'id': other.id,
                    'first_name': other.first_name,
                    'last_name': other.last_name,
                    'username': other.username,
                    'avatar': other.avatar.url if hasattr(other, 'avatar') and other.avatar else None,
                }
        return None

    def get_messages(self, obj):
        """Get conversation messages (limited for performance)"""
        messages = obj.messages.filter(
            is_deleted=False
        ).order_by('-created_at')[:50]
        
        return MessageSerializer(
            reversed(list(messages)),
            many=True,
            context=self.context
        ).data

    def get_unread_count(self, obj):
        """Get unread message count for current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count_for_user(request.user)
        return 0


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""
    
    class Meta:
        model = Message
        fields = [
            'conversation', 'message_type', 'content',
            'image', 'metadata'
        ]

    def validate_content(self, value):
        """Validate message content"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        return value.strip()

    def validate(self, attrs):
        """Validate message creation"""
        conversation = attrs.get('conversation')
        request = self.context.get('request')
        
        if request and request.user.is_authenticated:
            # Check if user is participant in conversation
            if not conversation.participants.filter(id=request.user.id).exists():
                raise serializers.ValidationError({
                    'conversation': 'You are not a participant in this conversation'
                })
            
            # Check if conversation is active
            if not conversation.is_active:
                raise serializers.ValidationError({
                    'conversation': 'This conversation is no longer active'
                })
        
        return attrs

    def create(self, validated_data):
        """Create message with sender"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['sender'] = request.user
        return super().create(validated_data)


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating conversations"""
    other_user_id = serializers.IntegerField(write_only=True, required=False)
    initial_message = serializers.CharField(
        write_only=True,
        required=False,
        help_text="Optional initial message"
    )
    
    class Meta:
        model = Conversation
        fields = [
            'related_product', 'title', 'other_user_id', 'initial_message'
        ]

    def validate_related_product(self, value):
        """Validate product access"""
        if value and hasattr(value, 'status') and value.status != 'active':
            raise serializers.ValidationError(
                "Cannot create conversation for inactive product"
            )
        return value

    def create(self, validated_data):
        """Create conversation with participants"""
        other_user_id = validated_data.pop('other_user_id', None)
        initial_message = validated_data.pop('initial_message', None)
        request = self.context.get('request')
        
        if not (request and request.user.is_authenticated):
            raise serializers.ValidationError("Authentication required")
        
        current_user = request.user
        related_product = validated_data.get('related_product')
        
        # If there's a related product, get the product owner as other participant
        other_user = None
        if related_product and hasattr(related_product, 'seller'):
            if related_product.seller == current_user:
                raise serializers.ValidationError({
                    'related_product': 'You cannot create a conversation about your own product'
                })
            other_user = related_product.seller
        elif other_user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                other_user = User.objects.get(id=other_user_id)
            except User.DoesNotExist:
                raise serializers.ValidationError({'other_user_id': 'User not found'})
        
        if not other_user:
            raise serializers.ValidationError("Either related_product or other_user_id is required")
        
        # Check if conversation already exists
        existing_conversation = Conversation.objects.filter(
            participants=current_user,
            related_product=related_product
        ).filter(participants=other_user).first()
        
        if existing_conversation:
            return existing_conversation
        
        with transaction.atomic():
            # Create conversation
            conversation = Conversation.objects.create(**validated_data)
            
            # Add participants
            conversation.participants.add(current_user, other_user)
            
            # Create participant settings
            for participant in conversation.participants.all():
                ConversationParticipant.objects.create(
                    conversation=conversation,
                    user=participant
                )
            
            # Create initial message if provided
            if initial_message:
                Message.objects.create(
                    conversation=conversation,
                    sender=current_user,
                    content=initial_message,
                    message_type='product_inquiry' if related_product else 'text'
                )
        
        return conversation


class OfferMessageSerializer(serializers.Serializer):
    """Serializer for price offer messages - FIXED"""
    offer_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    message = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_offer_amount(self, value):
        """Validate offer amount"""
        if value <= 0:
            raise serializers.ValidationError("Offer amount must be greater than 0")
        return value


class MeetupRequestSerializer(serializers.Serializer):
    """Serializer for meetup request messages - FIXED"""
    location = serializers.CharField(max_length=200)
    suggested_time = serializers.DateTimeField()
    message = serializers.CharField(max_length=500, required=False, allow_blank=True)


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for message attachments"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageAttachment
        fields = [
            'id', 'file', 'file_url', 'file_name',
            'file_size', 'file_type', 'created_at'
        ]

    def get_file_url(self, obj):
        """Get full URL for attachment"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None