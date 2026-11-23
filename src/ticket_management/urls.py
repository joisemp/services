from django.urls import path, include
from .views import common

app_name = "ticket_management"

urlpatterns = [
    # Common URLs - accessible to all authenticated users
    path('tickets/<slug:ticket_slug>/comments/', common.TicketCommentListView.as_view(), name='comment_list'),
    path('tickets/<slug:ticket_slug>/comments/create/', common.TicketCommentCreateView.as_view(), name='comment_create'),
    path('tickets/<slug:ticket_slug>/review-comments/create/', common.TicketReviewCommentCreateView.as_view(), name='review_comment_create'),
    
    # Role-based URL patterns for ticket management
    path('central-admin/', include('ticket_management.role_urls.central_admin')),
    path('maintainer/', include('ticket_management.role_urls.maintainer')),
    path('reviewer/', include('ticket_management.role_urls.reviewer')),
    path('space-admin/', include('ticket_management.role_urls.space_admin')),
    path('supervisor/', include('ticket_management.role_urls.supervisor')),
    path('transport-incharge/', include('ticket_management.role_urls.transport_incharge')),
]
