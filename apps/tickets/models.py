from django.db import models
from apps.authentication.models import User


class Ticket(models.Model):
    PRIORITY_CHOICES = [('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')]
    STATUS_CHOICES = [('open','Open'),('in_progress','In Progress'),('resolved','Resolved'),('closed','Closed')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    category = models.CharField(max_length=100, default='General')
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tickets'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket #{self.pk}: {self.title} [{self.status}]"


class TicketResponse(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='responses')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ticket_responses'
        ordering = ['created_at']

    def __str__(self):
        return f"Response to #{self.ticket.pk} by {self.author.email}"
