from django.db import models


class Log(models.Model):
    LEVEL_CHOICES = [('info','INFO'),('warning','WARNING'),('error','ERROR'),('critical','CRITICAL')]
    ACTION_CHOICES = [
        ('login','Login'),('logout','Logout'),('failed_login','Failed Login'),
        ('api_request','API Request'),('ticket_created','Ticket Created'),
        ('ticket_updated','Ticket Updated'),('model_trained','Model Trained'),
        ('admin_action','Admin Action'),('system','System'),
        ('profile_update','Profile Update'),('password_change','Password Change'),
    ]
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, default='system')
    user_email = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    endpoint = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=10, blank=True)
    response_code = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    extra_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level}] {self.action} - {self.created_at}"


class SystemHealth(models.Model):
    cpu_usage = models.FloatField()
    memory_usage = models.FloatField()
    disk_usage = models.FloatField()
    api_avg_response_ms = models.FloatField(default=0)
    active_users = models.IntegerField(default=0)
    error_count_24h = models.IntegerField(default=0)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_health'
        ordering = ['-recorded_at']
