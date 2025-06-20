from django.urls import path
from .views import account_creation_view, organisation_creation_view, account_creation_success, user_login_view, general_user_login_view

app_name = 'core'

urlpatterns = [
    path('account/create/', account_creation_view, name='account_creation'),
    path('organisation/create/', organisation_creation_view, name='organisation_creation'),
    path('account/success/', account_creation_success, name='account_creation_success'),
    path('login/', user_login_view, name='user_login'),
    path('general-user/login/', general_user_login_view, name='general_user_login'),
]
# This file is intentionally left empty for now.