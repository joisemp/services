"""Issue management API views."""
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
    IsIssueCreatorRole,
    IsIssueStaff,
    RoleAnyOf,
)
from issue_management.api.querysets import issues_for_user, site_visits_for_user, work_tasks_for_user
from issue_management.api.serializers import (
    AssignIssueSerializer,
    ChangeWorkshopSerializer,
    GenerateShoppingListSerializer,
    IssueCommentSerializer,
    IssueCreateUpdateSerializer,
    IssueDetailSerializer,
    IssueListSerializer,
    IssueReviewCommentSerializer,
    PurchaseRequestCreateSerializer,
    PurchaseRequestSerializer,
    PurchaseReviewSerializer,
    ResolveIssueSerializer,
    SelectReviewersSerializer,
    ShoppingListSerializer,
    SiteVisitCompleteSerializer,
    SiteVisitSerializer,
    WorkTaskCompleteSerializer,
    WorkTaskSerializer,
)
from issue_management.models import (
    Issue,
    IssueActivity,
    IssueComment,
    IssueImage,
    PurchaseRequest,
    ShoppingList,
    ShoppingListItem,
    SiteVisit,
    SiteVisitImage,
    WorkTask,
    WorkTaskResolutionImage,
)
from issue_management.utils.issue_filters import annotate_and_order, apply_issue_list_filters

User = get_user_model()


def _can_manage_issue_actions(user):
    return user.is_central_admin or user.is_space_admin


def _can_supervisor_progress(user):
    return user.is_supervisor


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------


@extend_schema_view(
    get=extend_schema(tags=['Issues'], summary='List issues', responses={200: IssueListSerializer(many=True), **error_responses(401)}),
    post=extend_schema(tags=['Issues'], summary='Create issue', request=IssueCreateUpdateSerializer, responses={201: IssueDetailSerializer, **error_responses(401, 403)}),
)
class IssueListCreateView(generics.ListCreateAPIView):
    search_fields = ['title', 'description', 'issue_id']
    filterset_fields = ['status', 'priority']
    ordering_fields = ['created_at', 'priority', 'status']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsIssueCreatorRole()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = issues_for_user(self.request.user)
        qs = apply_issue_list_filters(
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
            return IssueCreateUpdateSerializer
        return IssueListSerializer

    def create(self, request, *args, **kwargs):
        serializer = IssueCreateUpdateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        issue = serializer.save()
        return Response(IssueDetailSerializer(issue).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=['Issues'], summary='Issue detail', responses={200: IssueDetailSerializer, **error_responses(401)}),
    patch=extend_schema(tags=['Issues'], summary='Update issue', request=IssueCreateUpdateSerializer, responses={200: IssueDetailSerializer, **error_responses(401, 403)}),
    delete=extend_schema(tags=['Issues'], summary='Delete issue', responses={204: None, **error_responses(401, 403)}),
)
class IssueDetailView(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return issues_for_user(self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return IssueCreateUpdateSerializer
        return IssueDetailSerializer

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
        issue = self.get_object()
        serializer = IssueCreateUpdateSerializer(
            issue, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(IssueDetailSerializer(issue).data)


class IssueActionMixin:
    def get_issue(self):
        return get_object_or_404(issues_for_user(self.request.user), slug=self.kwargs['slug'])


@extend_schema(tags=['Issues'], summary='Assign issue', request=AssignIssueSerializer, responses={200: IssueDetailSerializer, **error_responses(401, 403)})
class IssueAssignView(IssueActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]

    def post(self, request, slug):
        issue = self.get_issue()
        serializer = AssignIssueSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        issue.assigned_to = serializer.validated_data['assigned_to']
        issue.assigned_by = request.user
        issue.assigned_at = timezone.now()
        issue.requires_review = serializer.validated_data.get('requires_review', False)
        issue.status = 'assigned'
        issue.save()
        return Response(IssueDetailSerializer(issue).data)


@extend_schema(tags=['Issues'], summary='Select reviewers', request=SelectReviewersSerializer, responses={200: IssueDetailSerializer, **error_responses(401, 403)})
class IssueSelectReviewersView(IssueActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]

    def post(self, request, slug):
        issue = self.get_issue()
        serializer = SelectReviewersSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        issue.requires_review = True
        issue.save(update_fields=['requires_review'])
        issue.reviewers.set(serializer.validated_data['reviewers'])
        return Response(IssueDetailSerializer(issue).data)


@extend_schema(tags=['Issues'], summary='Start work on issue', responses={200: IssueDetailSerializer, **error_responses(401, 403)})
class IssueStartWorkView(IssueActionMixin, APIView):
    def get_permissions(self):
        return [RoleAnyOf()]

    allowed_role_properties = ('is_central_admin', 'is_space_admin', 'is_supervisor')

    def post(self, request, slug):
        issue = self.get_issue()
        if request.user.is_supervisor and issue.assigned_to_id != request.user.id:
            raise PermissionDenied('You can only start work on issues assigned to you.')
        if issue.status == 'in_progress':
            raise ValidationError({'detail': 'Issue is already in progress.'})
        issue.status = 'in_progress'
        issue.save(update_fields=['status', 'updated_at'])
        return Response(IssueDetailSerializer(issue).data)


@extend_schema(tags=['Issues'], summary='Resolve issue', request=ResolveIssueSerializer, responses={200: IssueDetailSerializer, **error_responses(401, 403)})
class IssueResolveView(IssueActionMixin, APIView):
    allowed_role_properties = ('is_central_admin', 'is_space_admin', 'is_supervisor')

    def get_permissions(self):
        return [RoleAnyOf()]

    def post(self, request, slug):
        issue = self.get_issue()
        if request.user.is_supervisor and issue.assigned_to_id != request.user.id:
            raise PermissionDenied('You can only resolve issues assigned to you.')
        serializer = ResolveIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get('resolution_notes')
        if notes is not None:
            issue.resolution_notes = notes
        issue.status = 'resolved'
        issue.save()
        return Response(IssueDetailSerializer(issue).data)


@extend_schema(tags=['Issues'], summary='Reopen issue', responses={200: IssueDetailSerializer, **error_responses(401, 403)})
class IssueReopenView(IssueActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]

    def post(self, request, slug):
        issue = self.get_issue()
        issue.status = 'assigned' if issue.assigned_to else 'open'
        issue.save(update_fields=['status', 'updated_at'])
        return Response(IssueDetailSerializer(issue).data)


@extend_schema(tags=['Issues'], summary='Change workshop', request=ChangeWorkshopSerializer, responses={200: IssueDetailSerializer, **error_responses(401, 403)})
class IssueChangeWorkshopView(IssueActionMixin, APIView):
    permission_classes = [IsIssueStaff]

    def post(self, request, slug):
        issue = self.get_issue()
        serializer = ChangeWorkshopSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        old = issue.workshop
        issue.workshop = serializer.validated_data.get('workshop')
        issue.save()
        IssueActivity.objects.create(
            issue=issue,
            user=request.user,
            activity_type='updated',
            description='Workshop changed',
            old_value=str(old) if old else '',
            new_value=str(issue.workshop) if issue.workshop else '',
        )
        return Response(IssueDetailSerializer(issue).data)


@extend_schema(tags=['Issues'], summary='Upload issue image', responses={201: IssueDetailSerializer, **error_responses(401, 403)})
class IssueImageUploadView(IssueActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        issue = self.get_issue()
        image = request.FILES.get('image')
        if not image:
            raise ValidationError({'image': 'This field is required.'})
        IssueImage.objects.create(issue=issue, image=image)
        return Response(IssueDetailSerializer(issue).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Issues'], summary='Delete issue image', responses={204: None, **error_responses(401, 403)})
class IssueImageDeleteView(IssueActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]

    def delete(self, request, slug, image_slug):
        issue = self.get_issue()
        image = get_object_or_404(IssueImage, slug=image_slug, issue=issue)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Issues'], summary='Upload issue voice', responses={200: IssueDetailSerializer, **error_responses(401, 403)})
class IssueVoiceUploadView(IssueActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        issue = self.get_issue()
        voice = request.FILES.get('voice')
        if not voice:
            raise ValidationError({'voice': 'This field is required.'})
        issue.voice = voice
        issue.save(update_fields=['voice', 'updated_at'])
        return Response(IssueDetailSerializer(issue).data)


@extend_schema(tags=['Issues'], summary='Delete issue voice', responses={200: IssueDetailSerializer, **error_responses(401, 403)})
class IssueVoiceDeleteView(IssueActionMixin, APIView):
    permission_classes = [IsCentralOrSpaceAdmin]

    def delete(self, request, slug):
        issue = self.get_issue()
        if issue.voice:
            issue.voice.delete(save=False)
            issue.voice = None
            issue.save(update_fields=['voice', 'updated_at'])
        return Response(IssueDetailSerializer(issue).data)


@extend_schema_view(
    get=extend_schema(tags=['Issues'], summary='List comments', responses={200: IssueCommentSerializer(many=True), **error_responses(401)}),
    post=extend_schema(tags=['Issues'], summary='Add comment', request=IssueCommentSerializer, responses={201: IssueCommentSerializer, **error_responses(401)}),
)
class IssueCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = IssueCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_issue(self):
        return get_object_or_404(issues_for_user(self.request.user), slug=self.kwargs['slug'])

    def get_queryset(self):
        return IssueComment.objects.filter(issue=self.get_issue()).select_related('user')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['issue'] = self.get_issue()
        return ctx


@extend_schema(tags=['Issues'], summary='Add review comment', request=IssueReviewCommentSerializer, responses={201: IssueReviewCommentSerializer, **error_responses(401)})
class IssueReviewCommentCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        issue = get_object_or_404(issues_for_user(request.user), slug=slug)
        serializer = IssueReviewCommentSerializer(
            data=request.data, context={'request': request, 'issue': issue}
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
        issue = get_object_or_404(issues_for_user(request.user), slug=slug)
        serializer = WorkTaskSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        task = serializer.save(issue=issue)
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
        issue = get_object_or_404(issues_for_user(request.user), slug=slug)
        serializer = SiteVisitSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        visit = serializer.save(issue=issue, created_by=request.user)
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
        ).select_related('issue', 'requested_by')


@extend_schema(tags=['Purchases'], summary='Create purchase request', request=PurchaseRequestCreateSerializer, responses={201: PurchaseRequestSerializer, **error_responses(401, 403)})
class PurchaseRequestCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        if not request.user.is_space_admin:
            raise PermissionDenied('Only space admins can create purchase requests.')
        issue = get_object_or_404(issues_for_user(request.user), slug=slug)
        serializer = PurchaseRequestCreateSerializer(
            data=request.data, context={'request': request, 'issue': issue}
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
                issue_title=pr.issue.title,
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


@extend_schema(tags=['Reports'], summary='Issue list report', responses={200: dict, **error_responses(401, 403)})
class IssueListReportAPIView(APIView):
    permission_classes = [IsCentralAdmin]

    def get(self, request):
        from issue_management.utils.issue_list_report import _build_summary

        qs = issues_for_user(request.user)
        qs = apply_issue_list_filters(
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
                'issues': IssueListSerializer(annotate_and_order(qs)[:200], many=True).data,
            }
        )


@extend_schema(tags=['Reports'], summary='Performance report', responses={200: dict, **error_responses(401, 403)})
class PerformanceReportAPIView(APIView):
    permission_classes = [IsCentralAdmin]

    def get(self, request):
        qs = issues_for_user(request.user)
        by_status = {
            status_key: qs.filter(status=status_key).count()
            for status_key, _ in Issue.STATUS_CHOICES
        }
        by_priority = {
            priority: qs.filter(priority=priority).count()
            for priority, _ in Issue.PRIORITY_CHOICES
        }
        return Response(
            {
                'total': qs.count(),
                'by_status': by_status,
                'by_priority': by_priority,
            }
        )
