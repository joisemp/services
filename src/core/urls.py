from django.urls import path
from .views import account_creation_view, organisation_creation_view, account_creation_success, user_login_view, general_user_login_view
from . import views

app_name = 'core'

urlpatterns = [
    path('account/create/', account_creation_view, name='account_creation'),
    path('organisation/create/', organisation_creation_view, name='organisation_creation'),
    path('account/success/', account_creation_success, name='account_creation_success'),
    path('login/', user_login_view, name='user_login'),
    path('general-user/login/', general_user_login_view, name='general_user_login'),
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
# This file is intentionally left empty for now.