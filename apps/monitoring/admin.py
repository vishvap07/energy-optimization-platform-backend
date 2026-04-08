from django.contrib import admin
from .models import Log, SystemHealth

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'level', 'action', 'user_email', 'ip_address')
    list_filter = ('level', 'action', 'created_at')
    search_fields = ('user_email', 'ip_address', 'message')

@admin.register(SystemHealth)
class SystemHealthAdmin(admin.ModelAdmin):
    list_display = ('recorded_at', 'cpu_usage', 'memory_usage', 'disk_usage')
