from django.urls import path
from . import views

urlpatterns = [
    path('create', views.create_ticket, name='ticket-create'),
    path('list', views.list_tickets, name='ticket-list'),
    path('<int:ticket_id>', views.ticket_detail, name='ticket-detail'),
    path('<int:ticket_id>/update-status', views.update_ticket_status, name='ticket-update-status'),
    path('<int:ticket_id>/respond', views.respond_to_ticket, name='ticket-respond'),
]
