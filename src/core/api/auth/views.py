"""
JWT auth views: password/PIN/phone login, refresh, logout, me, password, PIN.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenVerifyView as SimpleJWTTokenVerifyView

from core.api.cookies import (
    blacklist_user_refresh_tokens,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from core.api.openapi import (
    DetailSerializer,
    EmptySerializer,
    LoginPasswordRequestSerializer,
    LoginPhoneRequestSerializer,
    LoginPinRequestSerializer,
    TokenAccessSerializer,
    TokenVerifyRequestSerializer,
    detail_response,
    error_responses,
)
from core.api.auth.serializers import (
    ChangePasswordSerializer,
    CookieTokenRefreshSerializer,
    MeSerializer,
    MeUpdateSerializer,
    PasswordLoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PhoneLoginSerializer,
    PinLoginSerializer,
    SetPinSerializer,
    tokens_for_user,
)

User = get_user_model()


class AuthRateThrottle(AnonRateThrottle):
    scope = 'auth'


def _login_response(user):
    data = tokens_for_user(user)
    response = Response({'access': data['access']}, status=status.HTTP_200_OK)
    set_refresh_cookie(response, data['refresh'])
    return response


@extend_schema(
    tags=['Auth'],
    summary='Login with email and password',
    request=LoginPasswordRequestSerializer,
    responses={
        200: TokenAccessSerializer,
        400: DetailSerializer,
        **error_responses(429),
    },
)
class PasswordLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return _login_response(serializer.validated_data['user'])


@extend_schema(
    tags=['Auth'],
    summary='Login with email and PIN',
    request=LoginPinRequestSerializer,
    responses={
        200: TokenAccessSerializer,
        400: DetailSerializer,
        **error_responses(429),
    },
)
class PinLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = PinLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return _login_response(serializer.validated_data['user'])


@extend_schema(
    tags=['Auth'],
    summary='Login with phone number',
    request=LoginPhoneRequestSerializer,
    responses={
        200: TokenAccessSerializer,
        400: DetailSerializer,
        **error_responses(429),
    },
)
class PhoneLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return _login_response(serializer.validated_data['user'])


@extend_schema(
    tags=['Auth'],
    summary='Refresh access token',
    request=None,
    responses={
        200: TokenAccessSerializer,
        400: DetailSerializer,
        **error_responses(401, 429),
    },
)
class CookieTokenRefreshView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = CookieTokenRefreshSerializer(data={}, context={'request': request})
        serializer.is_valid(raise_exception=True)
        refresh = serializer.validated_data['refresh']
        try:
            user = User.objects.get(pk=refresh['user_id'], is_active=True)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found or inactive.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Rotate: blacklist old refresh, issue new pair
        try:
            refresh.blacklist()
        except AttributeError:
            pass
        except TokenError:
            return Response(
                {'detail': 'Token is blacklisted or invalid.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = tokens_for_user(user)
        response = Response({'access': data['access']}, status=status.HTTP_200_OK)
        set_refresh_cookie(response, data['refresh'])
        return response


@extend_schema(
    tags=['Auth'],
    summary='Verify access token',
    request=TokenVerifyRequestSerializer,
    responses={
        200: EmptySerializer,
        401: DetailSerializer,
    },
)
class TokenVerifyView(SimpleJWTTokenVerifyView):
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=['Auth'],
    summary='Logout and blacklist refresh tokens',
    request=None,
    responses={
        200: detail_response('Logged out', 'ok', {'detail': 'Successfully logged out.'}),
        **error_responses(401),
    },
)
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        blacklist_user_refresh_tokens(request.user)
        response = Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)
        return response


@extend_schema_view(
    get=extend_schema(
        tags=['Auth'],
        summary='Current user profile',
        responses={200: MeSerializer, **error_responses(401)},
    ),
    patch=extend_schema(
        tags=['Auth'],
        summary='Update current user name fields',
        request=MeUpdateSerializer,
        responses={200: MeSerializer, **error_responses(401)},
    ),
)
class MeView(generics.RetrieveUpdateAPIView):
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return MeUpdateSerializer
        return MeSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = MeUpdateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MeSerializer(instance).data)


@extend_schema(
    tags=['Auth'],
    summary='Change password',
    request=ChangePasswordSerializer,
    responses={
        200: detail_response('Password changed', 'ok', {'detail': 'Password updated.'}),
        400: DetailSerializer,
        **error_responses(401),
    },
)
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        blacklist_user_refresh_tokens(request.user)
        response = Response({'detail': 'Password updated.'}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)
        return response


@extend_schema(
    tags=['Auth'],
    summary='Request password reset email',
    request=PasswordResetRequestSerializer,
    responses={
        200: detail_response(
            'If the account exists, an email was sent',
            'ok',
            {'detail': 'If an account exists for that email, a reset link has been sent.'},
        ),
        **error_responses(429),
    },
)
class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.filter(email__iexact=email, auth_method='email', is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            reset_url = f'{frontend}/reset-password?uid={uid}&token={token}'
            send_mail(
                subject='Password reset',
                message=f'Use this link to reset your password:\n{reset_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        return Response(
            {'detail': 'If an account exists for that email, a reset link has been sent.'},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=['Auth'],
    summary='Confirm password reset',
    request=PasswordResetConfirmSerializer,
    responses={
        200: detail_response('Password reset', 'ok', {'detail': 'Password has been reset.'}),
        400: DetailSerializer,
    },
)
class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        blacklist_user_refresh_tokens(user)
        response = Response({'detail': 'Password has been reset.'}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)
        return response


@extend_schema(
    tags=['Auth'],
    summary='Set or change PIN',
    request=SetPinSerializer,
    responses={
        200: detail_response('PIN set', 'ok', {'detail': 'PIN has been set.'}),
        400: DetailSerializer,
        **error_responses(401),
    },
)
class SetPinView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SetPinSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'PIN has been set.'}, status=status.HTTP_200_OK)
