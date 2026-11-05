"""Serializers for issues, tasks, site visits, purchases, and shopping lists."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.models import Space
from fleet_management.models import Vehicle, Workshop
from ticket_management.models import (
    Ticket,
    TicketComment,
    TicketImage,
    TicketReviewComment,
    PurchaseRequest,
    ShoppingList,
    ShoppingListItem,
    SiteVisit,
    SiteVisitImage,
    WorkTask,
    WorkTaskResolutionImage,
)

User = get_user_model()


class TicketImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketImage
        fields = ('id', 'slug', 'image')
        read_only_fields = fields


class TicketListSerializer(serializers.ModelSerializer):
    reporter_name = serializers.SerializerMethodField()
    assigned_to_slug = serializers.SlugRelatedField(source='assigned_to', slug_field='slug', read_only=True)
    space_slug = serializers.SlugRelatedField(source='space', slug_field='slug', read_only=True)
    vehicle_slug = serializers.SlugRelatedField(source='vehicle', slug_field='slug', read_only=True)
    workshop_slug = serializers.SlugRelatedField(source='workshop', slug_field='slug', read_only=True)

    class Meta:
        model = Ticket
        fields = (
            'id',
            'slug',
            'ticket_id',
            'title',
            'status',
            'priority',
            'created_at',
            'updated_at',
            'reporter_name',
            'assigned_to_slug',
            'space_slug',
            'vehicle_slug',
            'workshop_slug',
            'requires_review',
        )
        read_only_fields = fields

    def get_reporter_name(self, obj):
        if not obj.reporter:
            return None
        return obj.reporter.get_full_name() or obj.reporter.email or obj.reporter.phone_number


class TicketDetailSerializer(TicketListSerializer):
    images = TicketImageSerializer(many=True, read_only=True)
    reviewer_slugs = serializers.SlugRelatedField(
        source='reviewers', slug_field='slug', many=True, read_only=True
    )
    description = serializers.CharField()
    resolution_notes = serializers.CharField(allow_null=True)
    voice = serializers.FileField(allow_null=True)

    class Meta(TicketListSerializer.Meta):
        fields = TicketListSerializer.Meta.fields + (
            'description',
            'resolution_notes',
            'voice',
            'images',
            'reviewer_slugs',
            'assigned_at',
            'reviewed_at',
            'review_notes',
        )


class TicketCreateUpdateSerializer(serializers.ModelSerializer):
    space = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Space.objects.none(),
        required=False,
        allow_null=True,
    )
    vehicle = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Vehicle.objects.none(),
        required=False,
        allow_null=True,
    )
    workshop = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Workshop.objects.none(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Ticket
        fields = (
            'title',
            'description',
            'priority',
            'space',
            'vehicle',
            'workshop',
            'voice',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import Space as SpaceModel

        request = self.context.get('request')
        org = getattr(request.user, 'organization', None) if request else None
        if org:
            self.fields['space'].queryset = SpaceModel.objects.filter(org=org)
            self.fields['vehicle'].queryset = Vehicle.objects.filter(org=org)
            self.fields['workshop'].queryset = Workshop.objects.filter(org=org)

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        if user.is_space_admin and user.active_space and 'space' not in validated_data:
            validated_data['space'] = user.active_space
        validated_data['reporter'] = user
        validated_data['org'] = user.organization
        return super().create(validated_data)


class AssignTicketSerializer(serializers.Serializer):
    assigned_to = serializers.SlugField()
    requires_review = serializers.BooleanField(required=False, default=False)

    def validate_assigned_to(self, value):
        request = self.context['request']
        try:
            user = User.objects.get(
                slug=value,
                organization=request.user.organization,
                user_type='supervisor',
                is_active=True,
            )
        except User.DoesNotExist as exc:
            raise serializers.ValidationError('Supervisor not found.') from exc
        return user


class SelectReviewersSerializer(serializers.Serializer):
    reviewers = serializers.ListField(child=serializers.SlugField(), allow_empty=False)

    def validate_reviewers(self, value):
        request = self.context['request']
        users = list(
            User.objects.filter(
                slug__in=value,
                organization=request.user.organization,
                user_type='reviewer',
                is_active=True,
            )
        )
        if len(users) != len(set(value)):
            raise serializers.ValidationError('One or more reviewers were not found.')
        return users


class ResolveTicketSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField(required=False, allow_blank=True)


class ChangeWorkshopSerializer(serializers.Serializer):
    workshop = serializers.SlugField(allow_null=True, required=False)

    def validate_workshop(self, value):
        if value is None:
            return None
        request = self.context['request']
        try:
            return Workshop.objects.get(slug=value, org=request.user.organization)
        except Workshop.DoesNotExist as exc:
            raise serializers.ValidationError('Workshop not found.') from exc


class TicketCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = TicketComment
        fields = ('id', 'slug', 'comment', 'created_at', 'user_name')
        read_only_fields = ('id', 'slug', 'created_at', 'user_name')

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email or obj.user.phone_number

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['ticket'] = self.context['ticket']
        return super().create(validated_data)


class TicketReviewCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketReviewComment
        fields = ('id', 'slug', 'comment', 'created_at')
        read_only_fields = ('id', 'slug', 'created_at')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['ticket'] = self.context['ticket']
        return super().create(validated_data)


class WorkTaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.SlugRelatedField(slug_field='slug', queryset=User.objects.all())
    ticket_slug = serializers.CharField(source='ticket.slug', read_only=True)

    class Meta:
        model = WorkTask
        fields = (
            'id',
            'slug',
            'title',
            'description',
            'resolution_notes',
            'assigned_to',
            'due_date',
            'completed',
            'created_at',
            'updated_at',
            'ticket_slug',
        )
        read_only_fields = ('id', 'slug', 'created_at', 'updated_at', 'ticket_slug', 'completed')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        org = getattr(request.user, 'organization', None) if request else None
        self.fields['assigned_to'].queryset = User.objects.filter(
            organization=org,
            user_type__in=['maintainer', 'supervisor'],
            is_active=True,
        ) if org else User.objects.none()


class WorkTaskCompleteSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    completed = serializers.BooleanField(required=False)


class SiteVisitSerializer(serializers.ModelSerializer):
    assigned_to = serializers.SlugRelatedField(slug_field='slug', queryset=User.objects.all())
    ticket_slug = serializers.CharField(source='ticket.slug', read_only=True)

    class Meta:
        model = SiteVisit
        fields = (
            'id',
            'slug',
            'title',
            'description',
            'location',
            'assigned_to',
            'scheduled_date',
            'estimated_duration',
            'status',
            'findings',
            'actions_taken',
            'recommendations',
            'started_at',
            'completed_at',
            'created_at',
            'ticket_slug',
        )
        read_only_fields = (
            'id',
            'slug',
            'status',
            'started_at',
            'completed_at',
            'created_at',
            'ticket_slug',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        org = getattr(request.user, 'organization', None) if request else None
        self.fields['assigned_to'].queryset = User.objects.filter(
            organization=org,
            user_type__in=['maintainer', 'supervisor'],
            is_active=True,
        ) if org else User.objects.none()


class SiteVisitCompleteSerializer(serializers.Serializer):
    findings = serializers.CharField(required=False, allow_blank=True)
    actions_taken = serializers.CharField(required=False, allow_blank=True)
    recommendations = serializers.CharField(required=False, allow_blank=True)


class PurchaseRequestSerializer(serializers.ModelSerializer):
    ticket_slug = serializers.CharField(source='ticket.slug', read_only=True)
    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseRequest
        fields = (
            'id',
            'slug',
            'item',
            'quantity',
            'description',
            'estimated_amount',
            'status',
            'requested_at',
            'reviewed_at',
            'review_notes',
            'ticket_slug',
            'requested_by_name',
        )
        read_only_fields = (
            'id',
            'slug',
            'status',
            'requested_at',
            'reviewed_at',
            'review_notes',
            'ticket_slug',
            'requested_by_name',
        )

    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() or obj.requested_by.email


class PurchaseRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseRequest
        fields = ('item', 'quantity', 'description', 'estimated_amount')

    def create(self, validated_data):
        ticket= self.context['ticket']
        user = self.context['request'].user
        validated_data.update(
            {
                'ticket': ticket,
                'org': ticket.org,
                'space': ticket.space,
                'requested_by': user,
            }
        )
        return super().create(validated_data)


class PurchaseReviewSerializer(serializers.Serializer):
    review_notes = serializers.CharField(required=False, allow_blank=True)


class ShoppingListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingListItem
        fields = (
            'id',
            'item_snapshot',
            'quantity_snapshot',
            'amount_snapshot',
            'space_name',
            'ticket_title',
            'purchase_request',
        )
        read_only_fields = fields


class ShoppingListSerializer(serializers.ModelSerializer):
    items = ShoppingListItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = (
            'id',
            'slug',
            'title',
            'generated_at',
            'total_amount',
            'item_count',
            'items',
        )
        read_only_fields = fields


class GenerateShoppingListSerializer(serializers.Serializer):
    purchase_request_slugs = serializers.ListField(
        child=serializers.SlugField(),
        allow_empty=False,
    )
    title = serializers.CharField(max_length=200)
