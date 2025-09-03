from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Max, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from ..models import Conversation, Message, MessageAttachment, ConversationParticipant
from ..serializers.chat_serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    OfferMessageSerializer,
    MeetupRequestSerializer,
    MessageAttachmentSerializer,
)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations - FIXED to match frontend expectations
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ConversationCreateSerializer
        elif self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationListSerializer

    def get_queryset(self):
        """Return conversations where the user is a participant"""
        return Conversation.objects.filter(
            participants=self.request.user
        ).annotate(
            last_message_time=Max('messages__created_at')
        ).order_by('-last_message_time', '-created_at')

    def create(self, request, *args, **kwargs):
        """Create a new conversation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        
        # Return detailed view after creation
        detail_serializer = ConversationDetailSerializer(
            conversation, 
            context={'request': request}
        )
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """Get conversation details with messages"""
        conversation = self.get_object()
        
        # Mark messages as read for current user
        conversation.mark_as_read_for_user(request.user)
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a text message to a conversation"""
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create message data
        message_data = {
            'conversation': conversation.id,
            'content': request.data.get('content', ''),
            'message_type': request.data.get('type', 'text'),
            'image': request.data.get('image'),
            'metadata': request.data.get('metadata')
        }
        
        serializer = MessageCreateSerializer(
            data=message_data, 
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        
        return Response(
            MessageSerializer(message, context={'request': request}).data, 
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def send_price_offer(self, request, pk=None):
        """Send a price offer message"""
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        offer_serializer = OfferMessageSerializer(data=request.data)
        offer_serializer.is_valid(raise_exception=True)
        
        offer_amount = offer_serializer.validated_data['offer_amount']
        message_text = offer_serializer.validated_data.get(
            'message', 
            f"I'd like to offer R{offer_amount} for this item."
        )
        
        # Create offer message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=message_text,
            message_type='price_offer',
            metadata={'offer_amount': float(offer_amount)}
        )
        
        return Response(
            MessageSerializer(message, context={'request': request}).data, 
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def send_meetup_request(self, request, pk=None):
        """Send a meetup request message"""
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        meetup_serializer = MeetupRequestSerializer(data=request.data)
        meetup_serializer.is_valid(raise_exception=True)
        
        location = meetup_serializer.validated_data['location']
        suggested_time = meetup_serializer.validated_data['suggested_time']
        message_text = meetup_serializer.validated_data.get(
            'message', 
            f"Let's meet at {location}"
        )
        
        # Create meetup message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=message_text,
            message_type='meeting_request',
            metadata={
                'location': location,
                'suggested_time': suggested_time.isoformat()
            }
        )
        
        return Response(
            MessageSerializer(message, context={'request': request}).data, 
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark all messages in conversation as read"""
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        conversation.mark_as_read_for_user(request.user)
        
        return Response({'success': 'Messages marked as read'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get total unread message count for user"""
        unread_count = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        
        return Response({'unread_count': unread_count})


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages - FIXED to match frontend expectations
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return messages from conversations where user is participant"""
        return Message.objects.filter(
            conversation__participants=self.request.user,
            is_deleted=False
        ).order_by('-created_at')

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer

    def create(self, request, *args, **kwargs):
        """Create a new message"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if user is participant in the conversation
        conversation_id = request.data.get('conversation')
        if not Conversation.objects.filter(
            id=conversation_id, 
            participants=request.user
        ).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        message = serializer.save()
        
        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Update a message (only sender can edit)"""
        message = self.get_object()
        
        if message.sender != request.user:
            return Response(
                {'error': 'You can only edit your own messages'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow editing content
        allowed_fields = ['content']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(message, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(is_edited=True)
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Soft delete a message (only sender can delete)"""
        message = self.get_object()
        
        if message.sender != request.user:
            return Response(
                {'error': 'You can only delete your own messages'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a message as read"""
        message = self.get_object()
        
        # Check if user is participant in the conversation
        if not message.conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only mark as read if user is not the sender
        if message.sender != request.user:
            message.mark_as_read()
        
        return Response({'success': 'Message marked as read'})


class MessageAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing message attachments
    """
    serializer_class = MessageAttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return attachments from messages in conversations where user is participant"""
        return MessageAttachment.objects.filter(
            message__conversation__participants=self.request.user
        )

    def create(self, request, *args, **kwargs):
        """Create a new attachment"""
        message_id = request.data.get('message')
        
        # Verify user can add attachments to this message
        try:
            message = Message.objects.get(
                id=message_id,
                conversation__participants=request.user
            )
        except Message.DoesNotExist:
            return Response(
                {'error': 'Message not found or you do not have permission'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)