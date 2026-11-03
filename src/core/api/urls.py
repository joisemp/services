"""Core resource API URLs mounted under /api/."""
from django.urls import path

from core.api.views import (
    OrganizationMeView,
    PeopleDetailView,
    PeopleListCreateView,
    PeopleRegeneratePasswordView,
    PeopleTogglePhoneLoginView,
    RegisterFCMTokenAPIView,
    SpaceAddUsersView,
    SpaceDetailView,
    SpaceListCreateView,
    SpaceRemoveUserView,
    SpaceSwitchView,
    UpdateListView,
)

app_name = 'api_core'

urlpatterns = [
    path('organization/', OrganizationMeView.as_view(), name='organization'),
    path('people/', PeopleListCreateView.as_view(), name='people-list'),
    path('people/<slug:slug>/', PeopleDetailView.as_view(), name='people-detail'),
    path('people/<slug:slug>/regenerate-password/', PeopleRegeneratePasswordView.as_view(), name='people-regenerate-password'),
    path('people/<slug:slug>/toggle-phone-login/', PeopleTogglePhoneLoginView.as_view(), name='people-toggle-phone-login'),
    path('spaces/', SpaceListCreateView.as_view(), name='space-list'),
    path('spaces/switch/', SpaceSwitchView.as_view(), name='space-switch'),
    path('spaces/<slug:slug>/', SpaceDetailView.as_view(), name='space-detail'),
    path('spaces/<slug:slug>/users/', SpaceAddUsersView.as_view(), name='space-add-users'),
    path('spaces/<slug:slug>/users/<slug:user_slug>/', SpaceRemoveUserView.as_view(), name='space-remove-user'),
    path('updates/', UpdateListView.as_view(), name='update-list'),
    path('devices/fcm-token/', RegisterFCMTokenAPIView.as_view(), name='fcm-token'),
]
