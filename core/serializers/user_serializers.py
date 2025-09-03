from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from ..models import StudentUser, UserRating


class StudentUserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Password must be at least 8 characters long"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        help_text="Confirm your password"
    )

    class Meta:
        model = StudentUser
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'university'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'university': {'required': True},
        }

    def validate_email(self, value):
        """Validate student email domain"""
        user = StudentUser(email=value)
        if not user.is_valid_student_email():
            raise serializers.ValidationError(
                "Please use a valid university email address (.edu, .ac.za, etc.)"
            )
        return value

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match'
            })
        
        # Validate password strength
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
        
        return attrs

    def create(self, validated_data):
        """Create new student user"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = StudentUser.objects.create_user(
            password=password,
            **validated_data
        )
        return user



class StudentUserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile (read/update)"""
    profile_picture_url = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    can_post_products = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'university', 'student_id', 'phone_number', 'campus_location',
            'bio', 'profile_picture', 'profile_picture_url', 'verification_status',
            'average_rating', 'total_ratings', 'total_sales', 'total_purchases',
            'date_joined', 'last_login', 'can_post_products'
        ]
        read_only_fields = [
            'id', 'username', 'email', 'verification_status', 'average_rating',
            'total_ratings', 'total_sales', 'total_purchases', 'date_joined',
            'last_login', 'can_post_products', 'full_name', 'profile_picture_url'
        ]

    def get_profile_picture_url(self, obj):
        """Get full URL for profile picture"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

    def get_full_name(self, obj):
        """Get user's full name"""
        return obj.get_full_name()

    def get_can_post_products(self, obj):
        """Check if user can post products"""
        return obj.can_post_product()


class StudentUserPublicSerializer(serializers.ModelSerializer):
    """Public serializer for displaying user info to others"""
    profile_picture_url = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentUser
        fields = [
            'id', 'username', 'full_name', 'university', 'campus_location',
            'profile_picture_url', 'average_rating', 'total_ratings',
            'total_sales', 'date_joined'
        ]

    def get_profile_picture_url(self, obj):
        """Get full URL for profile picture"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

    def get_full_name(self, obj):
        """Get user's full name"""
        return obj.get_full_name()


class StudentUserListSerializer(serializers.ModelSerializer):
    """Minimal serializer for user lists"""
    profile_picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentUser
        fields = [
            'id', 'username', 'first_name', 'last_name',
            'university', 'profile_picture_url', 'average_rating'
        ]

    def get_profile_picture_url(self, obj):
        """Get full URL for profile picture"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None


class UserRatingSerializer(serializers.ModelSerializer):
    """Serializer for user ratings"""
    rater_info = StudentUserListSerializer(source='rater', read_only=True)
    rated_user_info = StudentUserListSerializer(source='rated_user', read_only=True)
    
    class Meta:
        model = UserRating
        fields = [
            'id', 'rating', 'comment', 'transaction_type',
            'rater', 'rated_user', 'rater_info', 'rated_user_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'rater', 'created_at', 'updated_at']

    def validate_rating(self, value):
        """Validate rating is between 1-5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

    def create(self, validated_data):
        """Create new rating"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['rater'] = request.user
        return super().create(validated_data)


class UserRatingCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating ratings"""
    
    class Meta:
        model = UserRating
        fields = ['rated_user', 'rating', 'comment', 'transaction_type']

    def validate_rating(self, value):
        """Validate rating is between 1-5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

    def validate(self, attrs):
        """Validate rating constraints"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            rater = request.user
            rated_user = attrs['rated_user']
            
            # Can't rate yourself
            if rater == rated_user:
                raise serializers.ValidationError({
                    'rated_user': 'You cannot rate yourself'
                })
            
            # Check for existing rating (if needed to prevent duplicates)
            # existing_rating = UserRating.objects.filter(
            #     rater=rater,
            #     rated_user=rated_user,
            #     transaction_type=attrs.get('transaction_type')
            # ).exists()
            # 
            # if existing_rating:
            #     raise serializers.ValidationError({
            #         'rated_user': 'You have already rated this user for this transaction type'
            #     })
        
        return attrs

    def create(self, validated_data):
        """Create new rating with automatic rater assignment"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['rater'] = request.user
        return super().create(validated_data)


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate login credentials"""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError({
                    'non_field_errors': 'Invalid username or password'
                })
            
            if not user.is_active:
                raise serializers.ValidationError({
                    'non_field_errors': 'User account is disabled'
                })
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError({
                'non_field_errors': 'Must include username and password'
            })


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect')
        return value
    
    def validate(self, attrs):
        """Validate new password confirmation"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'New passwords do not match'
            })
        
        # Validate password strength
        try:
            validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})
        
        return attrs
    
    def save(self):
        """Change user password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user