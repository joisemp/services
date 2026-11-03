"""
Serializers for JWT auth: login variants, profile, password, and PIN.
"""
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Add user_type and organization_id claims to access tokens."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['user_type'] = user.user_type
        token['organization_id'] = user.organization_id
        return token


def tokens_for_user(user) -> dict:
    """Issue a refresh/access pair with custom claims for ``user``."""
    refresh = CustomTokenObtainPairSerializer.get_token(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class PasswordLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        request = self.context.get('request')
        user = authenticate(
            request,
            username=attrs['email'],
            password=attrs['password'],
        )
        if user is None:
            raise serializers.ValidationError(
                {'detail': 'No active account found with the given credentials.'}
            )
        if not user.is_active:
            raise serializers.ValidationError({'detail': 'User account is disabled.'})
        attrs['user'] = user
        return attrs


class PinLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    pin = serializers.CharField(min_length=4, max_length=4, write_only=True)

    def validate(self, attrs):
        request = self.context.get('request')
        user = authenticate(
            request,
            username=attrs['email'],
            pin=attrs['pin'],
        )
        if user is None:
            raise serializers.ValidationError(
                {'detail': 'No active account found with the given credentials.'}
            )
        if not user.is_active:
            raise serializers.ValidationError({'detail': 'User account is disabled.'})
        attrs['user'] = user
        return attrs


class PhoneLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate(self, attrs):
        request = self.context.get('request')
        user = authenticate(
            request,
            phone_number=attrs['phone_number'],
        )
        if user is None:
            raise serializers.ValidationError(
                {'detail': 'No active account found with the given credentials.'}
            )
        if not user.is_active:
            raise serializers.ValidationError({'detail': 'User account is disabled.'})
        attrs['user'] = user
        return attrs


class MeSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(source='organization.id', read_only=True, allow_null=True)
    active_space_id = serializers.IntegerField(source='active_space.id', read_only=True, allow_null=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'slug',
            'email',
            'phone_number',
            'first_name',
            'last_name',
            'full_name',
            'user_type',
            'auth_method',
            'organization_id',
            'active_space_id',
            'allow_phone_login',
            'date_joined',
        )
        read_only_fields = (
            'id',
            'slug',
            'email',
            'phone_number',
            'user_type',
            'auth_method',
            'organization_id',
            'active_space_id',
            'allow_phone_login',
            'date_joined',
            'full_name',
        )


class MeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        if user.auth_method != 'email':
            raise serializers.ValidationError(
                {'detail': 'Password change is only available for email authentication users.'}
            )
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
        validate_password(attrs['new_password'], user)
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(skip_validation=True)
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Always succeed to avoid account enumeration; view decides whether to email.
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as exc:
            raise serializers.ValidationError({'uid': 'Invalid user id.'}) from exc

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({'token': 'Invalid or expired token.'})
        if user.auth_method != 'email':
            raise serializers.ValidationError(
                {'detail': 'Password reset is only available for email authentication users.'}
            )
        validate_password(attrs['new_password'], user)
        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save(skip_validation=True)
        return user


class SetPinSerializer(serializers.Serializer):
    pin = serializers.CharField(min_length=4, max_length=4, write_only=True)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('PIN must be exactly 4 digits.')
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        if user.user_type == 'general_user':
            raise serializers.ValidationError({'detail': 'General users cannot set a PIN.'})
        if user.is_superuser and not user.is_central_admin:
            raise serializers.ValidationError(
                {'detail': 'Superusers without a role cannot set a PIN.'}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_pin(self.validated_data['pin'])
        user.save(skip_validation=True)
        return user


class CookieTokenRefreshSerializer(serializers.Serializer):
    """Read refresh token from the httpOnly cookie instead of the request body."""

    def validate(self, attrs):
        request = self.context['request']
        from django.conf import settings

        raw = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if not raw:
            raise serializers.ValidationError({'detail': 'Refresh token cookie missing.'})
        try:
            refresh = RefreshToken(raw)
        except Exception as exc:
            raise serializers.ValidationError({'detail': 'Invalid or expired refresh token.'}) from exc
        attrs['refresh'] = refresh
        return attrs
