from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.conf import settings
from django.utils import timezone
import random
import string

from ..models import StudentUser, UserRating
from ..serializers.user_serializers import (
    StudentUserPublicSerializer, 
    StudentUserRegistrationSerializer,
    UserRatingSerializer,
    StudentUserProfileSerializer,
    StudentUserListSerializer,
    PasswordChangeSerializer,
    LoginSerializer,
    UserRatingCreateSerializer
)


class StudentUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing student users.
    """
    queryset = StudentUser.objects.all()
    serializer_class = StudentUserListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter users based on permissions"""
        if self.request.user.is_staff:
            return StudentUser.objects.all()
        else:
            # Regular users can only see verified users
            return StudentUser.objects.filter(is_verified=True)

    @action(detail=True, methods=['get'])
    def ratings(self, request, pk=None):
        """Get ratings for a specific user"""
        user = self.get_object()
        ratings = UserRating.objects.filter(rated_user=user)
        serializer = UserRatingSerializer(ratings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def rate_user(self, request, pk=None):
        """Rate a user"""
        rated_user = self.get_object()
        
        if rated_user == request.user:
            return Response(
                {'error': 'You cannot rate yourself'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already rated this user
        existing_rating = UserRating.objects.filter(
            rater=request.user, 
            rated_user=rated_user
        ).first()
        
        if existing_rating:
            return Response(
                {'error': 'You have already rated this user'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = UserRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(rater=request.user, rated_user=rated_user)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserRegistrationView(APIView):
    """
    Handle user registration with email verification
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = StudentUserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            # Check if email domain is allowed
            email = serializer.validated_data['email']
            email_domain = email.split('@')[-1].lower()
            
            allowed_domains = getattr(settings, 'STUDENT_EMAIL_DOMAINS', ['.edu', '.ac.za'])
            
            is_valid_domain = any(
                email_domain.endswith(domain.lstrip('.')) if domain.startswith('.') else email_domain == domain
                for domain in allowed_domains
            )
            
            if not is_valid_domain:
                return Response(
                    {'email': ['Please use a valid student email address']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create user
            user = serializer.save()
            
            # Generate verification code
            verification_code = ''.join(random.choices(string.digits, k=6))
            user.verification_code = verification_code
            user.verification_code_created = timezone.now()
            user.save()
            
            # TODO: Send verification email here
            # send_verification_email(user, verification_code)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Registration successful. Please check your email for verification code.',
                'user': StudentUserListSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'verification_required': True
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """
    Handle user profile operations
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user profile"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        """Update user profile"""
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Partially update user profile"""
        return self.put(request)


class EmailVerificationView(APIView):
    """
    Handle email verification
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        verification_code = request.data.get('verification_code')
        
        if not verification_code:
            return Response(
                {'verification_code': ['This field is required']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is already verified
        if user.is_verified:
            return Response(
                {'message': 'User is already verified'},
                status=status.HTTP_200_OK
            )
        
        # Check verification code
        if user.verification_code != verification_code:
            return Response(
                {'verification_code': ['Invalid verification code']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if code has expired (15 minutes)
        if user.verification_code_created:
            time_diff = timezone.now() - user.verification_code_created
            if time_diff.total_seconds() > 900:  # 15 minutes
                return Response(
                    {'verification_code': ['Verification code has expired']},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Verify user
        user.is_verified = True
        user.verification_code = None
        user.verification_code_created = None
        user.save()
        
        return Response(
            {'message': 'Email verified successfully'},
            status=status.HTTP_200_OK
        )


class ResendVerificationView(APIView):
    """
    Resend verification code
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.is_verified:
            return Response(
                {'message': 'User is already verified'},
                status=status.HTTP_200_OK
            )
        
        # Generate new verification code
        verification_code = ''.join(random.choices(string.digits, k=6))
        user.verification_code = verification_code
        user.verification_code_created = timezone.now()
        user.save()
        
        # TODO: Send verification email here
        # send_verification_email(user, verification_code)
        
        return Response(
            {'message': 'Verification code sent successfully'},
            status=status.HTTP_200_OK
        )


# Additional utility views
class UserStatsView(APIView):
    """
    Get user statistics
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get user statistics
        from ..models import Product, Conversation
        
        stats = {
            'products_listed': Product.objects.filter(seller=user).count(),
            'products_sold': Product.objects.filter(seller=user, is_available=False).count(),
            'conversations': Conversation.objects.filter(participants__user=user).count(),
            'average_rating': user.average_rating,
            'total_ratings': user.ratings_received.count(),
            'profile_completion': self._calculate_profile_completion(user),
        }
        
        return Response(stats)
    
    def _calculate_profile_completion(self, user):
        """Calculate profile completion percentage"""
        fields_to_check = [
            'first_name', 'last_name', 'phone_number', 
            'campus_location', 'bio', 'profile_picture'
        ]
        
        completed_fields = 0
        for field in fields_to_check:
            if getattr(user, field):
                completed_fields += 1
        
        # Add verification bonus
        if user.is_verified:
            completed_fields += 1
            fields_to_check.append('verification')
        
        return int((completed_fields / len(fields_to_check)) * 100)
    
    
    # Add these imports to the TOP of your auth_views.py file (with your existing imports)
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# Add these classes to the END of your auth_views.py file

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer to include user data in login response"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user data to the response
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'university': getattr(self.user, 'university', ''),
            'is_verified': self.user.is_verified,
            'campus_location': getattr(self.user, 'campus_location', ''),
        }
        
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view that includes user data in response"""
    serializer_class = CustomTokenObtainPairSerializer