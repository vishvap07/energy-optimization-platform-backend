from django.urls import path
from . import views

urlpatterns = [
    path('data', views.energy_data, name='energy-data'),
    path('analytics', views.analytics_summary, name='energy-analytics'),
    path('peak-demand', views.peak_demand, name='energy-peak-demand'),
    path('upload/', views.upload_csv, name='energy-upload'),
    path('alerts/', views.get_alerts, name='energy-alerts'),
    path('export/', views.export_csv, name='energy-export'),
]
