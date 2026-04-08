from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='auth-register'),
    path('login/', views.login, name='auth-login'),
    path('profile/', views.profile, name='auth-profile'),
    path('users/', views.list_users, name='auth-users'),
]
