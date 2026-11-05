from django.urls import path

from ..views import transport_incharge

app_name = 'transport_incharge'

urlpatterns = [
	path('create/', transport_incharge.TicketCreateView.as_view(), name='ticket_create'),
	path('vehicles/<slug:vehicle_slug>/tickets/', transport_incharge.VehicleTicketListView.as_view(), name='vehicle_ticket_list'),
	path('<slug:ticket_slug>/change-workshop/', transport_incharge.TicketWorkshopTransferView.as_view(), name='ticket_change_workshop'),
	path('<slug:ticket_slug>/delete/', transport_incharge.TicketDeleteView.as_view(), name='ticket_delete'),
	path('<slug:ticket_slug>/', transport_incharge.TicketDetailView.as_view(), name='ticket_detail'),
]