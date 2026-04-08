from rest_framework import serializers
from .models import FAQ, ChatSession


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'


class ChatQuerySerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000)
    session_id = serializers.CharField(max_length=100, required=False)


class ChatResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    intent = serializers.CharField()
    suggestions = serializers.ListField(child=serializers.CharField())
    session_id = serializers.CharField()
