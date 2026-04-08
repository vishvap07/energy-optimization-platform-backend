from django.urls import path
from . import views

urlpatterns = [
    path('system-health/', views.system_health, name='monitoring-health'),
    path('logs/', views.logs, name='monitoring-logs'),
]
