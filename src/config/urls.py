from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
    path('admin/', admin.site.urls),
    path('issue-management/', include('issue_management.urls', namespace='issue_management')),
    path('core/', include('core.urls', namespace='core')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('services/', include('service_management.urls', namespace='service_management')),
    path('transport/', include('transportation.urls', namespace='transportation')),
    path('marketplace/', include('marketplace.urls', namespace='marketplace')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)