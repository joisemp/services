from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import landing_view

urlpatterns = [
    path('', landing_view, name='landing'),
    path('admin/', admin.site.urls),
    path('issue-management/', include('issue_management.urls', namespace='issue_management')),
    path('core/', include('core.urls', namespace='core')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('services/', include('service_management.urls', namespace='service_management')),
    path('transport/', include('transportation.urls', namespace='transportation')),
    path('marketplace/', include('marketplace.urls', namespace='marketplace')),
    path('finance/', include('finance.urls', namespace='finance')),
    path('assets/', include('asset_management.urls', namespace='asset_management')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)