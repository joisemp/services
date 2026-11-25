import os

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.generic import TemplateView


class HomePageView(TemplateView):
    template_name = "index.html"


class OfflineView(TemplateView):
    """Minimal offline fallback page for the PWA service worker."""

    template_name = "offline.html"


class WebManifestView(View):
    """
    Serve the web app manifest from the app origin with resolved static icon URLs.
    Required so icons work in production where STATIC_URL points at the CDN.
    """

    def get(self, request):
        icons = [
            ("images/icon-192.png", "192x192", "any"),
            ("images/icon-512.png", "512x512", "any"),
            ("images/icon-192-maskable.png", "192x192", "maskable"),
            ("images/icon-512-maskable.png", "512x512", "maskable"),
        ]
        data = {
            "name": "Services",
            "short_name": "Services",
            "description": "Services — tickets, fleet, inventory, and space operations.",
            "start_url": "/core/login/",
            "scope": "/",
            "display": "standalone",
            "orientation": "any",
            "background_color": "#2563EB",
            "theme_color": "#2563EB",
            "icons": [
                {
                    "src": staticfiles_storage.url(path),
                    "sizes": sizes,
                    "type": "image/png",
                    "purpose": purpose,
                }
                for path, sizes, purpose in icons
            ],
        }
        response = JsonResponse(data)
        # Browsers expect application/manifest+json; JsonResponse defaults to application/json.
        response["Content-Type"] = "application/manifest+json"
        response["Cache-Control"] = "public, max-age=3600"
        return response


class ServiceWorkerView(View):
    """
    Serve the combined PWA + FCM service worker from the root path.
    Service workers need to be served from the app origin with full scope.
    """

    def get(self, request):
        sw_path = os.path.join(settings.BASE_DIR, "static", "js", "firebase-messaging-sw.js")

        try:
            with open(sw_path, "r", encoding="utf-8") as f:
                content = f.read()

            response = HttpResponse(content, content_type="application/javascript")
            response["Service-Worker-Allowed"] = "/"
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response
        except FileNotFoundError:
            return HttpResponse("Service worker not found", status=404)
