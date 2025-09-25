from django.views.generic import TemplateView


class CentralAdminDashboardView(TemplateView):
    template_name = 'central_admin/dashboard.html'
    
    
class SpaceAdminDashboardView(TemplateView):
    template_name = 'space_admin/dashboard.html'
