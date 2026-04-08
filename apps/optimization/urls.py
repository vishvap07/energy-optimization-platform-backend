from django.urls import path
from . import views

urlpatterns = [
    path('recommendations', views.recommendations, name='opt-recommendations'),
    path('peak-shaving', views.peak_shaving, name='opt-peak-shaving'),
]
