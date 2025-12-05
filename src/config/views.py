from django.views.generic import TemplateView
from django.views import View
from django.http import HttpResponse
from django.conf import settings
import os

class HomePageView(TemplateView):
    template_name = "index.html"

class ServiceWorkerView(View):
    """
    Serve the Firebase messaging service worker from the root path.
    Service workers need to be served from the root to have proper scope.
    """
    def get(self, request):
        # Path to the service worker file
        sw_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'firebase-messaging-sw.js')
        
        try:
            with open(sw_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Return with proper MIME type for service workers
            response = HttpResponse(content, content_type='application/javascript')
            response['Service-Worker-Allowed'] = '/'
            return response
        except FileNotFoundError:
            return HttpResponse('Service worker not found', status=404)