"""Auth URL patterns mounted at /api/auth/."""
from django.urls import path

from core.api.auth.views import (
    ChangePasswordView,
    CookieTokenRefreshView,
    LogoutView,
    MeView,
    PasswordLoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PhoneLoginView,
    PinLoginView,
    SetPinView,
    TokenVerifyView,
)

app_name = 'api_auth'

urlpatterns = [
    path('login/', PasswordLoginView.as_view(), name='login'),
    path('login/pin/', PinLoginView.as_view(), name='login-pin'),
    path('login/phone/', PhoneLoginView.as_view(), name='login-phone'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token-refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('me/', MeView.as_view(), name='me'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password/change/', ChangePasswordView.as_view(), name='password-change'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('pin/', SetPinView.as_view(), name='set-pin'),
]
