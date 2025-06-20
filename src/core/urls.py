from django.urls import path
from .views import account_creation_view, organisation_creation_view, account_creation_success

app_name = 'core'

urlpatterns = [
    path('account/create/', account_creation_view, name='account_creation'),
    path('organisation/create/', organisation_creation_view, name='organisation_creation'),
    path('account/success/', account_creation_success, name='account_creation_success'),
]
# This file is intentionally left empty for now.