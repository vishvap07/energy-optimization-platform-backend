from django.urls import path
from . import views

urlpatterns = [
    path('train-model', views.train_model, name='forecast-train'),
    path('predict', views.predict, name='forecast-predict'),
    path('results', views.forecast_results, name='forecast-results'),
]
