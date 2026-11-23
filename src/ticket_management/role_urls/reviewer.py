from django.urls import path
from ..views import reviewer

app_name = "reviewer"

urlpatterns = [
    # Reviewer-specific URLs for ticket review and approval
    path('', reviewer.ReviewerTicketListView.as_view(), name='ticket_list'),
    path('tickets/<slug:ticket_slug>/', reviewer.TicketDetailView.as_view(), name='ticket_detail'),
]
