from django.urls import path
from . import views

urlpatterns = [
    path('query', views.query_chatbot, name='chatbot-query'),
    path('faq', views.faq_list, name='chatbot-faq'),
]
