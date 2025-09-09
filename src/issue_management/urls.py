from django.urls import path, include

app_name = "issue_management"

urlpatterns = [
    path('central_admin/', include(('issue_management.urls.central_admin', 'central_admin'), namespace='central_admin')),
    path('maintainer/', include(('issue_management.urls.maintainer', 'maintainer'), namespace='maintainer')),
    path('reviewer/', include(('issue_management.urls.reviewer', 'reviewer'), namespace='reviewer')),
    path('space_admin/', include(('issue_management.urls.space_admin', 'space_admin'), namespace='space_admin')),
    path('supervisor/', include(('issue_management.urls.supervisor', 'supervisor'), namespace='supervisor')),
]
