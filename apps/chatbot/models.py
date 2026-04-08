from django.db import models


class FAQ(models.Model):
    INTENT_CHOICES = [
        ('energy_usage', 'Energy Usage'),
        ('peak_demand', 'Peak Demand'),
        ('create_ticket', 'Create Ticket'),
        ('system_help', 'System Help'),
        ('billing', 'Billing'),
        ('forecast', 'Forecast'),
        ('optimization', 'Optimization'),
        ('general', 'General'),
    ]
    intent = models.CharField(max_length=50, choices=INTENT_CHOICES, default='general')
    keywords = models.JSONField(default=list, help_text="List of trigger keywords")
    question = models.CharField(max_length=500)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'faqs'

    def __str__(self):
        return f"FAQ [{self.intent}]: {self.question[:60]}"


class ChatSession(models.Model):
    session_id = models.CharField(max_length=100)
    user_message = models.TextField()
    bot_response = models.TextField()
    intent = models.CharField(max_length=50, default='general')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-created_at']
