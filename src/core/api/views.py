"""API views for people, spaces, updates, organization, and FCM."""
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.openapi import detail_response, error_responses
from core.api.permissions import IsCentralAdmin, IsCentralOrSpaceAdmin, IsSpaceAdmin
from core.api.serializers import (
    FCMTokenSerializer,
    OrganizationSerializer,
    PeopleCreateSerializer,
    PeopleListSerializer,
    PeopleUpdateSerializer,
    SpaceSerializer,
    SpaceSwitchSerializer,
    SpaceUserAddSerializer,
    UpdateSerializer,
    people_annotated_queryset,
)
from core.models import Space, Update

User = get_user_model()


@extend_schema_view(
    get=extend_schema(tags=['People'], summary='List people', responses={200: PeopleListSerializer(many=True), **error_responses(401, 403)}),
    post=extend_schema(tags=['People'], summary='Create person', request=PeopleCreateSerializer, responses={201: PeopleListSerializer, **error_responses(401, 403)}),
)
class PeopleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsCentralAdmin]
    search_fields = ['first_name', 'last_name', 'email', 'phone_number']
    filterset_fields = ['user_type']
    ordering_fields = ['first_name', 'last_name', 'date_joined']
    ordering = ['first_name', 'last_name']
    lookup_field = 'slug'

    def get_queryset(self):
        return people_annotated_queryset(self.request.user.organization)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PeopleCreateSerializer
        return PeopleListSerializer

    def create(self, request, *args, **kwargs):
        serializer = PeopleCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        qs = people_annotated_queryset(request.user.organization).get(pk=user.pk)
        return Response(PeopleListSerializer(qs).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=['People'], summary='Person detail', responses={200: PeopleListSerializer, **error_responses(401, 403)}),
    patch=extend_schema(tags=['People'], summary='Update person', request=PeopleUpdateSerializer, responses={200: PeopleListSerializer, **error_responses(401, 403)}),
    delete=extend_schema(tags=['People'], summary='Deactivate person', responses={204: None, **error_responses(401, 403)}),
)
class PeopleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsCentralAdmin]
    lookup_field = 'slug'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return people_annotated_queryset(self.request.user.organization)

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return PeopleUpdateSerializer
        return PeopleListSerializer

    def perform_destroy(self, instance):
        if instance.is_superuser:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'Cannot deactivate superuser accounts.'})
        if instance.pk == self.request.user.pk:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'You cannot deactivate your own account.'})
        instance.is_active = False
        instance.save(update_fields=['is_active'], skip_validation=True)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = PeopleUpdateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        qs = people_annotated_queryset(request.user.organization).get(pk=instance.pk)
        return Response(PeopleListSerializer(qs).data)


@extend_schema(
    tags=['People'],
    summary='Send password reset email',
    responses={200: detail_response('Sent', 'ok', {'detail': 'Password reset email sent.'}), **error_responses(401, 403)},
)
class PeopleRegeneratePasswordView(APIView):
    permission_classes = [IsCentralAdmin]

    def post(self, request, slug):
        user = get_object_or_404(
            User,
            slug=slug,
            organization=request.user.organization,
            is_active=True,
        )
        if user.auth_method != 'email' or user.user_type == 'general_user':
            return Response(
                {'detail': 'Password regeneration is only available for email authentication users.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = request.build_absolute_uri(
            reverse('core:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        send_mail(
            subject='Password reset',
            message=f'Reset your password:\n{reset_url}',
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True,
        )
        return Response({'detail': 'Password reset email sent.'})


@extend_schema(
    tags=['People'],
    summary='Toggle phone login',
    responses={200: PeopleListSerializer, **error_responses(401, 403)},
)
class PeopleTogglePhoneLoginView(APIView):
    permission_classes = [IsCentralAdmin]

    def post(self, request, slug):
        user = get_object_or_404(
            User,
            slug=slug,
            organization=request.user.organization,
            is_active=True,
        )
        if user.user_type == 'central_admin':
            return Response(
                {'detail': 'Phone login toggle is not available for central admin users.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.phone_number:
            return Response(
                {'detail': 'Phone login toggle requires a phone number.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.allow_phone_login = not user.allow_phone_login
        user.save(update_fields=['allow_phone_login'])
        qs = people_annotated_queryset(request.user.organization).get(pk=user.pk)
        return Response(PeopleListSerializer(qs).data)


@extend_schema_view(
    get=extend_schema(tags=['Spaces'], summary='List spaces', responses={200: SpaceSerializer(many=True), **error_responses(401, 403)}),
    post=extend_schema(tags=['Spaces'], summary='Create space', request=SpaceSerializer, responses={201: SpaceSerializer, **error_responses(401, 403)}),
)
class SpaceListCreateView(generics.ListCreateAPIView):
    serializer_class = SpaceSerializer
    search_fields = ['name', 'label']
    ordering = ['name']
    lookup_field = 'slug'

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsCentralAdmin()]
        return [IsCentralOrSpaceAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = Space.objects.select_related('org').prefetch_related('users')
        if user.is_central_admin:
            return qs.filter(org=user.organization)
        return user.spaces.all()


@extend_schema_view(
    get=extend_schema(tags=['Spaces'], summary='Space detail', responses={200: SpaceSerializer, **error_responses(401, 403)}),
    patch=extend_schema(tags=['Spaces'], summary='Update space', request=SpaceSerializer, responses={200: SpaceSerializer, **error_responses(401, 403)}),
    delete=extend_schema(tags=['Spaces'], summary='Delete space', responses={204: None, **error_responses(401, 403)}),
)
class SpaceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SpaceSerializer
    lookup_field = 'slug'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.request.method in ('PATCH', 'DELETE'):
            return [IsCentralAdmin()]
        return [IsCentralOrSpaceAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = Space.objects.select_related('org').prefetch_related('users')
        if user.is_central_admin:
            return qs.filter(org=user.organization)
        return user.spaces.all()


@extend_schema(
    tags=['Spaces'],
    summary='Add users to space',
    request=SpaceUserAddSerializer,
    responses={200: SpaceSerializer, **error_responses(401, 403)},
)
class SpaceAddUsersView(APIView):
    permission_classes = [IsCentralAdmin]

    def post(self, request, slug):
        space = get_object_or_404(Space, slug=slug, org=request.user.organization)
        serializer = SpaceUserAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        users = User.objects.filter(
            slug__in=serializer.validated_data['user_slugs'],
            organization=request.user.organization,
            is_active=True,
        )
        space.users.add(*users)
        return Response(SpaceSerializer(space).data)


@extend_schema(
    tags=['Spaces'],
    summary='Remove user from space',
    responses={200: SpaceSerializer, **error_responses(401, 403)},
)
class SpaceRemoveUserView(APIView):
    permission_classes = [IsCentralAdmin]

    def delete(self, request, slug, user_slug):
        space = get_object_or_404(Space, slug=slug, org=request.user.organization)
        user = get_object_or_404(User, slug=user_slug, organization=request.user.organization)
        space.users.remove(user)
        if user.active_space_id == space.id:
            user.active_space = None
            user.save(update_fields=['active_space'], skip_validation=True)
        return Response(SpaceSerializer(space).data)


@extend_schema(
    tags=['Spaces'],
    summary='Switch active space',
    request=SpaceSwitchSerializer,
    responses={200: SpaceSerializer, **error_responses(401, 403)},
)
class SpaceSwitchView(APIView):
    permission_classes = [IsSpaceAdmin]

    def post(self, request):
        serializer = SpaceSwitchSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        space = serializer.save()
        return Response(SpaceSerializer(space).data)


@extend_schema(
    tags=['Updates'],
    summary='List updates',
    responses={200: UpdateSerializer(many=True), **error_responses(401)},
)
class UpdateListView(generics.ListAPIView):
    serializer_class = UpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = Update.objects.filter(org=user.organization)
        if user.is_space_admin and user.active_space:
            qs = qs.filter(Q(space=user.active_space) | Q(space__isnull=True))
        return qs


@extend_schema(
    tags=['Organization'],
    summary='Current organization',
    responses={200: OrganizationSerializer, **error_responses(401)},
)
class OrganizationMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        org = request.user.organization
        if not org:
            return Response({'detail': 'No organization.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrganizationSerializer(org).data)


@extend_schema(
    tags=['Devices'],
    summary='Register FCM token',
    request=FCMTokenSerializer,
    responses={200: detail_response('Registered', 'ok', {'detail': 'FCM token registered.'}), **error_responses(401)},
)
class RegisterFCMTokenAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FCMTokenSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'FCM token registered.'})
