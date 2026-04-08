from rest_framework import serializers
from .models import ForecastResult, ModelTrainingJob


class ForecastResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForecastResult
        fields = '__all__'


class ModelTrainingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelTrainingJob
        fields = '__all__'


class PredictionRequestSerializer(serializers.Serializer):
    days_ahead = serializers.IntegerField(default=7, min_value=1, max_value=30)
