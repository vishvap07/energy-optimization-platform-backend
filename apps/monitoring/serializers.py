from rest_framework import serializers
from .models import Log, SystemHealth


class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = '__all__'


class SystemHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemHealth
        fields = '__all__'


class SystemHealthSummarySerializer(serializers.Serializer):
    status = serializers.CharField()
    cpu_usage = serializers.FloatField()
    memory_usage = serializers.FloatField()
    disk_usage = serializers.FloatField()
    total_requests_24h = serializers.IntegerField()
    error_rate = serializers.FloatField()
    avg_response_ms = serializers.FloatField()
    active_users = serializers.IntegerField()
    uptime_hours = serializers.FloatField()
