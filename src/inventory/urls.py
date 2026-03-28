from django.urls import include, path

app_name = 'inventory'

urlpatterns = [
    path('central-admin/', include('inventory.role_urls.central_admin')),
    path('maintainer/', include('inventory.role_urls.maintainer')),
    path('reviewer/', include('inventory.role_urls.reviewer')),
    path('space-admin/', include('inventory.role_urls.space_admin')),
    path('supervisor/', include('inventory.role_urls.supervisor')),
]
