from rest_framework import serializers
from .models import Ticket, TicketResponse
from apps.authentication.serializers import UserSerializer


class TicketResponseSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    responder_email = serializers.SerializerMethodField()

    class Meta:
        model = TicketResponse
        fields = ['id', 'ticket', 'author', 'author_name', 'responder_email', 'message', 'is_internal', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}"

    def get_responder_email(self, obj):
        return obj.author.email


class TicketSerializer(serializers.ModelSerializer):
    responses = TicketResponseSerializer(many=True, read_only=True)
    user_email = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_email(self, obj):
        return obj.user.email

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}"
        return None


class CreateTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'category']
