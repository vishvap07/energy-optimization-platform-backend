from rest_framework import serializers
from .models import EnergyData


class EnergyDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnergyData
        fields = '__all__'


class AnalyticsSummarySerializer(serializers.Serializer):
    total_consumption_kwh = serializers.FloatField()
    avg_daily_kwh = serializers.FloatField()
    peak_demand_kw = serializers.FloatField()
    peak_hour = serializers.IntegerField()
    min_consumption_kwh = serializers.FloatField()
    max_consumption_kwh = serializers.FloatField()
    anomaly_count = serializers.IntegerField()
    anomalous_records = serializers.ListField(child=serializers.DictField(), required=False)
    cost_estimate = serializers.FloatField()


class PeakDemandSerializer(serializers.Serializer):
    hour = serializers.IntegerField()
    avg_demand_kw = serializers.FloatField()
    is_peak = serializers.BooleanField()
