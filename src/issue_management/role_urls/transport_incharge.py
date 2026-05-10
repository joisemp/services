from django.urls import path

from ..views import transport_incharge

app_name = 'transport_incharge'

urlpatterns = [
	path('create/', transport_incharge.IssueCreateView.as_view(), name='issue_create'),
	path('vehicles/<slug:vehicle_slug>/issues/', transport_incharge.VehicleIssueListView.as_view(), name='vehicle_issue_list'),
	path('<slug:issue_slug>/change-workshop/', transport_incharge.IssueWorkshopTransferView.as_view(), name='issue_change_workshop'),
	path('<slug:issue_slug>/delete/', transport_incharge.IssueDeleteView.as_view(), name='issue_delete'),
	path('<slug:issue_slug>/', transport_incharge.IssueDetailView.as_view(), name='issue_detail'),
]