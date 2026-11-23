"""Ticket management API views."""
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.openapi import error_responses
from core.api.permissions import (
    IsCentralAdmin,
    IsCentralOrSpaceAdmin,
    IsTicketCreatorRole,
    IsTicketStaff,
    RoleAnyOf,
)
from ticket_management.api.querysets import issues_for_user, site_visits_for_user, work_tasks_for_user
from ticket_management.api.serializers import (
    AssignTicketSerializer,
    ChangeWorkshopSerializer,
    GenerateShoppingListSerializer,
    TicketCommentSerializer,
    TicketCreateUpdateSerializer,
    TicketDetailSerializer,
    TicketListSerializer,
    TicketReviewCommentSerializer,
    PurchaseRequestCreateSerializer,
    PurchaseRequestSerializer,
    PurchaseReviewSerializer,
    ResolveTicketSerializer,
    SelectReviewersSerializer,
    ShoppingListSerializer,
    SiteVisitCompleteSerializer,
    SiteVisitSerializer,
    WorkTaskCompleteSerializer,
    WorkTaskSerializer,
)
from ticket_management.models import (
    Ticket,
    TicketActivity,
    TicketComment,
    TicketImage,
    PurchaseRequest,
    ShoppingList,
    ShoppingListItem,
    SiteVisit,
    SiteVisitImage,
    WorkTask,
    WorkTaskResolutionImage,
)
from ticket_management.utils.ticket_filters import annotate_and_order, apply_ticket_list_filters

User = get_user_model()


def _can_manage_issue_actions(user):
    return user.is_central_admin or user.is_space_admin


def _can_supervisor_progress(user):
    return user.is_supervisor


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------


@extend_schema_view(
    get=extend_schema(tags=['Tickets'], summary='List issues', responses={200: TicketListSerializer(many=True), **error_responses(401)}),
    post=extend_schema(tags=['Tickets'], summary='Create ticket', request=TicketCreateUpdateSerializer, responses={201: TicketDetailSerializer, **error_responses(401, 403)}),
)
class TicketListCreateView(generics.ListCreateAPIView):
    search_fields = ['title', 'description', 'ticket_id']
    filterset_fields = ['status', 'priority']
    ordering_fields = ['created_at', 'priority', 'status']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsTicketCreatorRole()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = issues_for_user(self.request.user)
        qs = apply_ticket_list_filters(
            qs,
            status_filter=self.request.query_params.get('status'),
            space_filter=self.request.query_params.get('space'),
            reporter_filter=self.request.query_params.get('reporter'),
            assignee_filter=self.request.query_params.get('assignee'),
        )
        vehicle = self.request.query_params.get('vehicle')
        workshop = self.request.query_params.get('workshop')
        if vehicle:
            qs = qs.filter(vehicle__slug=vehicle)
        if workshop:
            qs = qs.filter(workshop__slug=workshop)
        return annotate_and_order(qs)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TicketCreateUpdateSerializer
        return TicketListSerializer

    def create(self, request, *args, **kwargs):
        serializer = TicketCreateUpdateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        ticket= serializer.save()
        return Response(TicketDetailSerializer(ticket).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=['Tickets'], summary='Ticket detail', responses={200: TicketDetailSerializer, **error_responses(401)}),
    patch=extend_schema(tags=['Tickets'], summary='Update ticket', request=TicketCreateUpdateSerializer, responses={200: TicketDetailSerializer, **error_responses(401, 403)}),
    delete=extend_schema(tags=['Tickets'], summary='Delete ticket', responses={204: None, **error_responses(401, 403)}),
)
class TicketDetailView(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return issues_for_user(self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return TicketCreateUpdateSerializer
        return TicketDetailSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [RoleAnyOf()]
        if self.request.method == 'PATCH':
            return [IsCentralOrSpaceAdmin()]
        return [permissions.IsAuthenticated()]

    @property
    def allowed_role_properties(self):
        if self.request.method == 'DELETE':
            return ('is_central_admin', 'is_space_admin', 'is_transport_incharge')
        return ()

    def update(self, request, *args, **kwargs):
        ticket= self.get_object()
        serializer = TicketCreateUpdateSerializer(
            ticket, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TicketDetailSerializer(ticket).data)


class TicketActionMixin:
    def get_issue(self):
        return get_object_or_404(issues_for_user(self.request.user), slug=self.kwargs['slug'])


@extend_schema(tags=['Tickets'], summary='Assign ticket', request=AssignTicketSerializer, responses={200: TicketDetailSerializer, **error_responses(401, 403)})
class TicketAssignView(TicketActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]

    def post(self, request, slug):
        ticket= self.get_issue()
        serializer = AssignTicketSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        ticket.assigned_to = serializer.validated_data['assigned_to']
        ticket.assigned_by = request.user
        ticket.assigned_at = timezone.now()
        ticket.requires_review = serializer.validated_data.get('requires_review', False)
        ticket.status = 'assigned'
        ticket.save()
        return Response(TicketDetailSerializer(ticket).data)


@extend_schema(tags=['Tickets'], summary='Select reviewers', request=SelectReviewersSerializer, responses={200: TicketDetailSerializer, **error_responses(401, 403)})
class TicketSelectReviewersView(TicketActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]

    def post(self, request, slug):
        ticket= self.get_issue()
        serializer = SelectReviewersSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        ticket.requires_review = True
        ticket.save(update_fields=['requires_review'])
        ticket.reviewers.set(serializer.validated_data['reviewers'])
        return Response(TicketDetailSerializer(ticket).data)


@extend_schema(tags=['Tickets'], summary='Start work on ticket', responses={200: TicketDetailSerializer, **error_responses(401, 403)})
class TicketStartWorkView(TicketActionMixin, APIView):
    def get_permissions(self):
        return [RoleAnyOf()]

    allowed_role_properties = ('is_central_admin', 'is_space_admin', 'is_supervisor')

    def post(self, request, slug):
        ticket= self.get_issue()
        if request.user.is_supervisor and ticket.assigned_to_id != request.user.id:
            raise PermissionDenied('You can only start work on issues assigned to you.')
        if ticket.status == 'in_progress':
            raise ValidationError({'detail': 'Ticket is already in progress.'})
        ticket.status = 'in_progress'
        ticket.save(update_fields=['status', 'updated_at'])
        return Response(TicketDetailSerializer(ticket).data)


@extend_schema(tags=['Tickets'], summary='Resolve ticket', request=ResolveTicketSerializer, responses={200: TicketDetailSerializer, **error_responses(401, 403)})
class TicketResolveView(TicketActionMixin, APIView):
    allowed_role_properties = ('is_central_admin', 'is_space_admin', 'is_supervisor')

    def get_permissions(self):
        return [RoleAnyOf()]

    def post(self, request, slug):
        ticket= self.get_issue()
        if request.user.is_supervisor and ticket.assigned_to_id != request.user.id:
            raise PermissionDenied('You can only resolve issues assigned to you.')
        serializer = ResolveTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get('resolution_notes')
        if notes is not None:
            ticket.resolution_notes = notes
        ticket.status = 'resolved'
        ticket.save()
        return Response(TicketDetailSerializer(ticket).data)


@extend_schema(tags=['Tickets'], summary='Reopen ticket', responses={200: TicketDetailSerializer, **error_responses(401, 403)})
class TicketReopenView(TicketActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]

    def post(self, request, slug):
        ticket= self.get_issue()
        ticket.status = 'assigned' if ticket.assigned_to else 'open'
        ticket.save(update_fields=['status', 'updated_at'])
        return Response(TicketDetailSerializer(ticket).data)


@extend_schema(tags=['Tickets'], summary='Change workshop', request=ChangeWorkshopSerializer, responses={200: TicketDetailSerializer, **error_responses(401, 403)})
class TicketChangeWorkshopView(TicketActionMixin, APIView):
    permission_classes = [IsTicketStaff]

    def post(self, request, slug):
        ticket= self.get_issue()
        serializer = ChangeWorkshopSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        old = ticket.workshop
        ticket.workshop = serializer.validated_data.get('workshop')
        ticket.save()
        TicketActivity.objects.create(
            ticket=ticket,
            user=request.user,
            activity_type='updated',
            description='Workshop changed',
            old_value=str(old) if old else '',
            new_value=str(ticket.workshop) if ticket.workshop else '',
        )
        return Response(TicketDetailSerializer(ticket).data)


@extend_schema(tags=['Tickets'], summary='Upload ticket image', responses={201: TicketDetailSerializer, **error_responses(401, 403)})
class TicketImageUploadView(TicketActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        ticket= self.get_issue()
        image = request.FILES.get('image')
        if not image:
            raise ValidationError({'image': 'This field is required.'})
        TicketImage.objects.create(ticket=ticket, image=image)
        return Response(TicketDetailSerializer(ticket).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Tickets'], summary='Delete ticket image', responses={204: None, **error_responses(401, 403)})
class TicketImageDeleteView(TicketActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]

    def delete(self, request, slug, image_slug):
        ticket= self.get_issue()
        image = get_object_or_404(TicketImage, slug=image_slug, ticket=ticket)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Tickets'], summary='Upload ticket voice', responses={200: TicketDetailSerializer, **error_responses(401, 403)})
class TicketVoiceUploadView(TicketActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        ticket= self.get_issue()
        voice = request.FILES.get('voice')
        if not voice:
            raise ValidationError({'voice': 'This field is required.'})
        ticket.voice = voice
        ticket.save(update_fields=['voice', 'updated_at'])
        return Response(TicketDetailSerializer(ticket).data)


@extend_schema(tags=['Tickets'], summary='Delete ticket voice', responses={200: TicketDetailSerializer, **error_responses(401, 403)})
class TicketVoiceDeleteView(TicketActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]

    def delete(self, request, slug):
        ticket= self.get_issue()
        if ticket.voice:
            ticket.voice.delete(save=False)
            ticket.voice = None
            ticket.save(update_fields=['voice', 'updated_at'])
        return Response(TicketDetailSerializer(ticket).data)


@extend_schema_view(
    get=extend_schema(tags=['Tickets'], summary='List comments', responses={200: TicketCommentSerializer(many=True), **error_responses(401)}),
    post=extend_schema(tags=['Tickets'], summary='Add comment', request=TicketCommentSerializer, responses={201: TicketCommentSerializer, **error_responses(401)}),
)
class TicketCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = TicketCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_issue(self):
        return get_object_or_404(issues_for_user(self.request.user), slug=self.kwargs['slug'])

    def get_queryset(self):
        return TicketComment.objects.filter(ticket=self.get_issue()).select_related('user')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['ticket'] = self.get_issue()
        return ctx


@extend_schema(tags=['Tickets'], summary='Add review comment', request=TicketReviewCommentSerializer, responses={201: TicketReviewCommentSerializer, **error_responses(401)})
class TicketReviewCommentCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        ticket= get_object_or_404(issues_for_user(request.user), slug=slug)
        serializer = TicketReviewCommentSerializer(
            data=request.data, context={'request': request, 'ticket': ticket}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Work tasks
# ---------------------------------------------------------------------------


@extend_schema_view(
    get=extend_schema(tags=['Work Tasks'], summary='List work tasks', responses={200: WorkTaskSerializer(many=True), **error_responses(401)}),
)
class WorkTaskListView(generics.ListAPIView):
    serializer_class = WorkTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['completed']

    def get_queryset(self):
        return work_tasks_for_user(self.request.user)


@extend_schema(tags=['Work Tasks'], summary='Create work task', request=WorkTaskSerializer, responses={201: WorkTaskSerializer, **error_responses(401, 403)})
class WorkTaskCreateView(APIView):
    allowed_role_properties = ('is_central_admin', 'is_space_admin', 'is_supervisor')

    def get_permissions(self):
        return [RoleAnyOf()]

    def post(self, request, slug):
        ticket= get_object_or_404(issues_for_user(request.user), slug=slug)
        serializer = WorkTaskSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        task = serializer.save(ticket=ticket)
        return Response(WorkTaskSerializer(task, context={'request': request}).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=['Work Tasks'], summary='Work task detail', responses={200: WorkTaskSerializer, **error_responses(401)}),
    patch=extend_schema(tags=['Work Tasks'], summary='Update work task', request=WorkTaskSerializer, responses={200: WorkTaskSerializer, **error_responses(401, 403)}),
    delete=extend_schema(tags=['Work Tasks'], summary='Delete work task', responses={204: None, **error_responses(401, 403)}),
)
class WorkTaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WorkTaskSerializer
    lookup_field = 'slug'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return work_tasks_for_user(self.request.user)

    def get_permissions(self):
        if self.request.method in ('PATCH', 'DELETE'):
            return [RoleAnyOf()]
        return [permissions.IsAuthenticated()]

    allowed_role_properties = ('is_central_admin', 'is_space_admin', 'is_supervisor')


@extend_schema(tags=['Work Tasks'], summary='Complete work task', request=WorkTaskCompleteSerializer, responses={200: WorkTaskSerializer, **error_responses(401, 403)})
class WorkTaskCompleteView(APIView):
    allowed_role_properties = ('is_central_admin', 'is_space_admin', 'is_supervisor')

    def get_permissions(self):
        return [RoleAnyOf()]

    def post(self, request, slug):
        task = get_object_or_404(work_tasks_for_user(request.user), slug=slug)
        serializer = WorkTaskCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get('resolution_notes')
        if notes is not None:
            task.resolution_notes = notes
        task.completed = True
        task.save()
        return Response(WorkTaskSerializer(task, context={'request': request}).data)


@extend_schema(tags=['Work Tasks'], summary='Toggle work task complete', responses={200: WorkTaskSerializer, **error_responses(401, 403)})
class WorkTaskToggleCompleteView(APIView):
    allowed_role_properties = (
        'is_central_admin',
        'is_space_admin',
        'is_supervisor',
        'is_maintainer',
    )

    def get_permissions(self):
        return [RoleAnyOf()]

    def post(self, request, slug):
        task = get_object_or_404(work_tasks_for_user(request.user), slug=slug)
        if request.user.is_maintainer and task.assigned_to_id != request.user.id:
            raise PermissionDenied('You can only toggle tasks assigned to you.')
        task.completed = not task.completed
        task.save(update_fields=['completed', 'updated_at'])
        return Response(WorkTaskSerializer(task, context={'request': request}).data)


@extend_schema(tags=['Work Tasks'], summary='Upload resolution image', responses={201: WorkTaskSerializer, **error_responses(401, 403)})
class WorkTaskResolutionImageUploadView(APIView):
    allowed_role_properties = ('is_central_admin', 'is_space_admin', 'is_supervisor', 'is_maintainer')
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        return [RoleAnyOf()]

    def post(self, request, slug):
        task = get_object_or_404(work_tasks_for_user(request.user), slug=slug)
        image = request.FILES.get('image')
        if not image:
            raise ValidationError({'image': 'This field is required.'})
        WorkTaskResolutionImage.objects.create(work_task=task, image=image)
        return Response(WorkTaskSerializer(task, context={'request': request}).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Work Tasks'], summary='Delete resolution image', responses={204: None, **error_responses(401, 403)})
class WorkTaskResolutionImageDeleteView(APIView):
    allowed_role_properties = ('is_central_admin', 'is_space_admin', 'is_supervisor')

    def get_permissions(self):
        return [RoleAnyOf()]

    def delete(self, request, slug, image_slug):
        task = get_object_or_404(work_tasks_for_user(request.user), slug=slug)
        image = get_object_or_404(WorkTaskResolutionImage, slug=image_slug, work_task=task)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Site visits
# ---------------------------------------------------------------------------


@extend_schema_view(
    get=extend_schema(tags=['Site Visits'], summary='List site visits', responses={200: SiteVisitSerializer(many=True), **error_responses(401)}),
)
class SiteVisitListView(generics.ListAPIView):
    serializer_class = SiteVisitSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status']

    def get_queryset(self):
        return site_visits_for_user(self.request.user)


@extend_schema(tags=['Site Visits'], summary='Create site visit', request=SiteVisitSerializer, responses={201: SiteVisitSerializer, **error_responses(401, 403)})
class SiteVisitCreateView(APIView):
    allowed_role_properties = ('is_central_admin', 'is_space_admin', 'is_supervisor')

    def get_permissions(self):
        return [RoleAnyOf()]

    def post(self, request, slug):
        ticket= get_object_or_404(issues_for_user(request.user), slug=slug)
        serializer = SiteVisitSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        visit = serializer.save(ticket=ticket, created_by=request.user)
        return Response(SiteVisitSerializer(visit, context={'request': request}).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=['Site Visits'], summary='Site visit detail', responses={200: SiteVisitSerializer, **error_responses(401)}),
    patch=extend_schema(tags=['Site Visits'], summary='Update site visit', request=SiteVisitSerializer, responses={200: SiteVisitSerializer, **error_responses(401, 403)}),
    delete=extend_schema(tags=['Site Visits'], summary='Delete site visit', responses={204: None, **error_responses(401, 403)}),
)
class SiteVisitDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SiteVisitSerializer
    lookup_field = 'slug'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return site_visits_for_user(self.request.user)

    def get_permissions(self):
        if self.request.method in ('PATCH', 'DELETE'):
            return [IsCentralOrSpaceAdmin()]
        return [permissions.IsAuthenticated()]


class SiteVisitLifecycleView(APIView):
    allowed_role_properties = (
        'is_central_admin',
        'is_space_admin',
        'is_supervisor',
        'is_maintainer',
    )

    def get_permissions(self):
        return [RoleAnyOf()]

    def get_visit(self):
        return get_object_or_404(site_visits_for_user(self.request.user), slug=self.kwargs['slug'])


@extend_schema(tags=['Site Visits'], summary='Start site visit', responses={200: SiteVisitSerializer, **error_responses(401, 403)})
class SiteVisitStartView(SiteVisitLifecycleView):
    def post(self, request, slug):
        visit = self.get_visit()
        visit.mark_in_progress()
        return Response(SiteVisitSerializer(visit, context={'request': request}).data)


@extend_schema(tags=['Site Visits'], summary='Complete site visit', request=SiteVisitCompleteSerializer, responses={200: SiteVisitSerializer, **error_responses(401, 403)})
class SiteVisitCompleteView(SiteVisitLifecycleView):
    def post(self, request, slug):
        visit = self.get_visit()
        serializer = SiteVisitCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(visit, field, value)
        visit.mark_completed()
        return Response(SiteVisitSerializer(visit, context={'request': request}).data)


@extend_schema(tags=['Site Visits'], summary='Cancel site visit', responses={200: SiteVisitSerializer, **error_responses(401, 403)})
class SiteVisitCancelView(SiteVisitLifecycleView):
    def post(self, request, slug):
        visit = self.get_visit()
        visit.cancel()
        return Response(SiteVisitSerializer(visit, context={'request': request}).data)


@extend_schema(tags=['Site Visits'], summary='Upload site visit image', responses={201: SiteVisitSerializer, **error_responses(401, 403)})
class SiteVisitImageUploadView(SiteVisitLifecycleView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        visit = self.get_visit()
        image = request.FILES.get('image')
        if not image:
            raise ValidationError({'image': 'This field is required.'})
        SiteVisitImage.objects.create(site_visit=visit, image=image)
        return Response(SiteVisitSerializer(visit, context={'request': request}).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Purchase requests & shopping lists
# ---------------------------------------------------------------------------


@extend_schema_view(
    get=extend_schema(tags=['Purchases'], summary='List purchase requests', responses={200: PurchaseRequestSerializer(many=True), **error_responses(401, 403)}),
)
class PurchaseRequestListView(generics.ListAPIView):
    serializer_class = PurchaseRequestSerializer
    permission_classes = [IsCentralAdmin]
    filterset_fields = ['status']

    def get_queryset(self):
        return PurchaseRequest.objects.filter(
            org=self.request.user.organization
        ).select_related('ticket', 'requested_by')


@extend_schema(tags=['Purchases'], summary='Create purchase request', request=PurchaseRequestCreateSerializer, responses={201: PurchaseRequestSerializer, **error_responses(401, 403)})
class PurchaseRequestCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        if not request.user.is_space_admin:
            raise PermissionDenied('Only space admins can create purchase requests.')
        ticket= get_object_or_404(issues_for_user(request.user), slug=slug)
        serializer = PurchaseRequestCreateSerializer(
            data=request.data, context={'request': request, 'ticket': ticket}
        )
        serializer.is_valid(raise_exception=True)
        pr = serializer.save()
        return Response(PurchaseRequestSerializer(pr).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=['Purchases'], summary='Purchase request detail', responses={200: PurchaseRequestSerializer, **error_responses(401, 403)}),
    delete=extend_schema(tags=['Purchases'], summary='Delete purchase request', responses={204: None, **error_responses(401, 403)}),
)
class PurchaseRequestDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = PurchaseRequestSerializer
    lookup_field = 'slug'
    http_method_names = ['get', 'delete', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = PurchaseRequest.objects.filter(org=user.organization)
        if user.is_space_admin and user.active_space:
            qs = qs.filter(space=user.active_space)
        elif not user.is_central_admin and not user.is_space_admin:
            return PurchaseRequest.objects.none()
        return qs

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [RoleAnyOf()]
        return [RoleAnyOf()]

    allowed_role_properties = ('is_central_admin', 'is_space_admin')


class PurchaseReviewView(APIView):
    permission_classes = [IsCentralAdmin]
    action_status = None

    def post(self, request, slug):
        pr = get_object_or_404(
            PurchaseRequest, slug=slug, org=request.user.organization, status='pending'
        )
        serializer = PurchaseReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pr.status = self.action_status
        pr.reviewed_by = request.user
        pr.reviewed_at = timezone.now()
        pr.review_notes = serializer.validated_data.get('review_notes', '')
        pr.save()
        return Response(PurchaseRequestSerializer(pr).data)


@extend_schema(tags=['Purchases'], summary='Approve purchase request', request=PurchaseReviewSerializer, responses={200: PurchaseRequestSerializer, **error_responses(401, 403)})
class PurchaseRequestApproveView(PurchaseReviewView):
    action_status = 'approved'


@extend_schema(tags=['Purchases'], summary='Reject purchase request', request=PurchaseReviewSerializer, responses={200: PurchaseRequestSerializer, **error_responses(401, 403)})
class PurchaseRequestRejectView(PurchaseReviewView):
    action_status = 'rejected'


@extend_schema_view(
    get=extend_schema(tags=['Purchases'], summary='List shopping lists', responses={200: ShoppingListSerializer(many=True), **error_responses(401, 403)}),
)
class ShoppingListListView(generics.ListAPIView):
    serializer_class = ShoppingListSerializer
    permission_classes = [IsCentralAdmin]

    def get_queryset(self):
        return ShoppingList.objects.filter(org=self.request.user.organization).prefetch_related('items')


@extend_schema(tags=['Purchases'], summary='Generate shopping list', request=GenerateShoppingListSerializer, responses={201: ShoppingListSerializer, **error_responses(401, 403)})
class ShoppingListGenerateView(APIView):
    permission_classes = [IsCentralAdmin]

    def post(self, request):
        serializer = GenerateShoppingListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prs = list(
            PurchaseRequest.objects.filter(
                slug__in=serializer.validated_data['purchase_request_slugs'],
                org=request.user.organization,
                status='approved',
            )
        )
        if not prs:
            raise ValidationError({'purchase_request_slugs': 'No approved purchase requests found.'})
        total = sum((p.estimated_amount or 0) for p in prs)
        shopping = ShoppingList.objects.create(
            title=serializer.validated_data['title'],
            org=request.user.organization,
            generated_by=request.user,
            total_amount=total,
            item_count=len(prs),
        )
        for pr in prs:
            ShoppingListItem.objects.create(
                shopping_list=shopping,
                purchase_request=pr,
                item_snapshot=pr.item,
                quantity_snapshot=pr.quantity,
                amount_snapshot=pr.estimated_amount,
                space_name=pr.space.name if pr.space else '',
                ticket_title=pr.ticket.title,
            )
        return Response(
            ShoppingListSerializer(shopping).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(tags=['Purchases'], summary='Shopping list detail', responses={200: ShoppingListSerializer, **error_responses(401, 403)}),
    delete=extend_schema(tags=['Purchases'], summary='Delete shopping list', responses={204: None, **error_responses(401, 403)}),
)
class ShoppingListDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ShoppingListSerializer
    permission_classes = [IsCentralAdmin]
    lookup_field = 'slug'

    def get_queryset(self):
        return ShoppingList.objects.filter(
            org=self.request.user.organization
        ).prefetch_related('items')


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@extend_schema(tags=['Reports'], summary='Ticket list report', responses={200: dict, **error_responses(401, 403)})
class TicketListReportAPIView(APIView):
    permission_classes = [IsCentralAdmin]

    def get(self, request):
        from ticket_management.utils.ticket_list_report import _build_summary

        qs = issues_for_user(request.user)
        qs = apply_ticket_list_filters(
            qs,
            status_filter=request.query_params.get('status'),
            space_filter=request.query_params.get('space'),
            reporter_filter=request.query_params.get('reporter'),
            assignee_filter=request.query_params.get('assignee'),
        )
        summary = _build_summary(qs)
        return Response(
            {
                'summary': summary,
                'issues': TicketListSerializer(annotate_and_order(qs)[:200], many=True).data,
            }
        )


@extend_schema(tags=['Reports'], summary='Performance report', responses={200: dict, **error_responses(401, 403)})
class PerformanceReportAPIView(APIView):
    permission_classes = [IsCentralAdmin]

    def get(self, request):
        qs = issues_for_user(request.user)
        by_status = {
            status_key: qs.filter(status=status_key).count()
            for status_key, _ in Ticket.STATUS_CHOICES
        }
        by_priority = {
            priority: qs.filter(priority=priority).count()
            for priority, _ in Ticket.PRIORITY_CHOICES
        }
        return Response(
            {
                'total': qs.count(),
                'by_status': by_status,
                'by_priority': by_priority,
            }
        )
