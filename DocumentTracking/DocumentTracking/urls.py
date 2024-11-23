"""
URL configuration for DocumentTracking project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from tracking.urls import UserLoginView, DashboardView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('accounts/login/', UserLoginView.as_view(), name='login'),  # User login
    path('', DashboardView.as_view(), name='dashboard'),  # Dashboard
    path('admin/', admin.site.urls),
    path('tracking/', include('tracking.urls')),  # Ensure your app's URLs are included
]
# Add this line to serve media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
