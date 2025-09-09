from django.urls import path, include

app_name = "issue_management"

urlpatterns = [
    # Role-based URL patterns for issue management
    path('central-admin/', include('issue_management.role_urls.central_admin')),
    path('maintainer/', include('issue_management.role_urls.maintainer')),
    path('reviewer/', include('issue_management.role_urls.reviewer')),
    path('space-admin/', include('issue_management.role_urls.space_admin')),
    path('supervisor/', include('issue_management.role_urls.supervisor')),
]
