from rest_framework import serializers
from .models import OptimizationResult


class OptimizationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationResult
        fields = '__all__'


class RecommendationSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    impact = serializers.CharField()
    priority = serializers.CharField()
    estimated_savings_kwh = serializers.FloatField()
    estimated_cost_savings = serializers.FloatField()
