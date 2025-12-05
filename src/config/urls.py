"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import HomePageView, ServiceWorkerView

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Authentication URLs (includes password reset)
    path('auth/', include('django.contrib.auth.urls')),
    
    # Home page
    path('', HomePageView.as_view(), name='home'),
    
    # Firebase service worker (must be at root for proper scope)
    path('firebase-messaging-sw.js', ServiceWorkerView.as_view(), name='firebase-sw'),
    
    # Core application URLs
    path('core/', include('core.urls')),
    
    # Issue management application URLs
    path('issues/', include('issue_management.urls')),
    
    # Dashboard application URLs
    path('dashboard/', include('dashboard.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
