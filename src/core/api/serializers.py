"""Serializers for people, spaces, updates, organization, and devices."""
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import serializers

from core.models import Organization, Space, Update

User = get_user_model()

ROLE_USER_TYPES = [
    ('central_admin', 'Central Admin'),
    ('space_admin', 'Space Admin'),
    ('maintainer', 'Maintainer'),
    ('supervisor', 'Supervisor'),
    ('reviewer', 'Reviewer'),
    ('driver', 'Driver'),
    ('transport_incharge', 'Transport Incharge'),
]


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = (
            'id',
            'name',
            'description',
            'address_line_one',
            'address_line_two',
            'slug',
        )
        read_only_fields = fields


class PeopleListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    total_reported_issues = serializers.IntegerField(read_only=True)
    total_assigned_issues = serializers.IntegerField(read_only=True)
    open_issues_count = serializers.IntegerField(read_only=True)
    in_progress_issues_count = serializers.IntegerField(read_only=True)
    resolved_issues_count = serializers.IntegerField(read_only=True)
    closed_issues_count = serializers.IntegerField(read_only=True)

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
            'allow_phone_login',
            'is_active',
            'date_joined',
            'total_reported_issues',
            'total_assigned_issues',
            'open_issues_count',
            'in_progress_issues_count',
            'resolved_issues_count',
            'closed_issues_count',
        )
        read_only_fields = fields


class PeopleCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    phone_number = serializers.CharField(max_length=17)
    email = serializers.EmailField(required=False, allow_null=True)
    user_type = serializers.ChoiceField(
        choices=[('general_user', 'General User')] + ROLE_USER_TYPES,
    )

    def validate(self, attrs):
        user_type = attrs['user_type']
        email = attrs.get('email')
        if user_type == 'general_user':
            attrs['email'] = None
        else:
            if not email:
                raise serializers.ValidationError({'email': 'Email is required for this role.'})
            if User.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError({'email': 'A user with this email already exists.'})
        if User.objects.filter(phone_number=attrs['phone_number']).exists():
            raise serializers.ValidationError({'phone_number': 'A user with this phone number already exists.'})
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        org = request.user.organization
        user_type = validated_data['user_type']
        if user_type == 'general_user':
            user = User.objects.create_user(
                phone_number=validated_data['phone_number'],
                user_type='general_user',
                organization=org,
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
            )
        else:
            user = User(
                phone_number=validated_data['phone_number'],
                email=validated_data['email'],
                user_type=user_type,
                auth_method='email',
                organization=org,
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
            )
            user.set_password('dummy_password_for_validation')
            user.save()
            user.set_unusable_password()
            user.save(skip_validation=True)
            self._send_password_reset_email(user, request)
        return user

    def _send_password_reset_email(self, user, request):
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        password_reset_url = request.build_absolute_uri(
            reverse('core:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        site_name = get_current_site(request).name
        send_mail(
            subject=f'Welcome to {site_name} - Set Your Password',
            message=(
                f'Welcome to {site_name}!\n\n'
                f'Your account ({user.email}) has been created. '
                f'Set your password here:\n{password_reset_url}\n'
            ),
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True,
        )


class PeopleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'email')


class SpaceSerializer(serializers.ModelSerializer):
    org_slug = serializers.CharField(source='org.slug', read_only=True)
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Space
        fields = (
            'id',
            'slug',
            'name',
            'label',
            'description',
            'org_slug',
            'user_count',
        )
        read_only_fields = ('id', 'slug', 'org_slug', 'user_count')

    def get_user_count(self, obj):
        return obj.users.count()

    def create(self, validated_data):
        validated_data['org'] = self.context['request'].user.organization
        return super().create(validated_data)


class SpaceUserAddSerializer(serializers.Serializer):
    user_slugs = serializers.ListField(
        child=serializers.SlugField(),
        allow_empty=False,
    )


class SpaceSwitchSerializer(serializers.Serializer):
    space = serializers.SlugField()

    def validate_space(self, value):
        try:
            space = Space.objects.get(slug=value)
        except Space.DoesNotExist as exc:
            raise serializers.ValidationError('Space not found.') from exc
        user = self.context['request'].user
        if not user.can_access_space(space):
            raise serializers.ValidationError('You do not have access to this space.')
        return space

    def save(self, **kwargs):
        user = self.context['request'].user
        space = self.validated_data['space']
        user.set_active_space(space)
        return space


class UpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Update
        fields = (
            'id',
            'slug',
            'title',
            'content',
            'created_at',
            'updated_at',
            'related_issue',
            'space',
        )
        read_only_fields = fields


class FCMTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField()

    def save(self, **kwargs):
        user = self.context['request'].user
        user.fcm_token = self.validated_data['fcm_token']
        user.save(update_fields=['fcm_token'])
        return user


def people_annotated_queryset(organization):
    """People list queryset with the same issue counts as the HTML page."""
    return User.objects.filter(
        organization=organization,
        is_active=True,
    ).select_related('organization').prefetch_related('spaces').annotate(
        total_reported_issues=Count('reported_issues', distinct=True),
        total_assigned_issues=Count('assigned_issues', distinct=True),
        open_issues_count=Count(
            'assigned_issues',
            filter=Q(assigned_issues__status='open'),
            distinct=True,
        ),
        in_progress_issues_count=Count(
            'assigned_issues',
            filter=Q(assigned_issues__status='in_progress'),
            distinct=True,
        ),
        resolved_issues_count=Count(
            'assigned_issues',
            filter=Q(assigned_issues__status='resolved'),
            distinct=True,
        ),
        closed_issues_count=Count(
            'assigned_issues',
            filter=Q(assigned_issues__status='closed'),
            distinct=True,
        ),
    )
