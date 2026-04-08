"""
URL configuration for energy_platform project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/energy/', include('apps.analytics.urls')),
    path('api/forecast/', include('apps.forecasting.urls')),
    path('api/optimization/', include('apps.optimization.urls')),
    path('api/tickets/', include('apps.tickets.urls')),
    path('api/chatbot/', include('apps.chatbot.urls')),
    path('api/monitoring/', include('apps.monitoring.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
