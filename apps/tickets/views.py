from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import Ticket, TicketResponse
from .serializers import TicketSerializer, CreateTicketSerializer, TicketResponseSerializer
from apps.monitoring.utils import log_action


from .utils import auto_assign_priority


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_ticket(request):
    serializer = CreateTicketSerializer(data=request.data)
    if serializer.is_valid():
        # Auto-calculate priority based on content
        title = serializer.validated_data.get('title', '')
        description = serializer.validated_data.get('description', '')
        category = serializer.validated_data.get('category', 'General')
        
        auto_priority = auto_assign_priority(title, description, category)
        
        ticket = serializer.save(user=request.user, priority=auto_priority)
        log_action('ticket_created', request.user.email, f'Ticket #{ticket.pk} created (Auto-Priority: {auto_priority})', request)
        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_tickets(request):
    if request.user.role == 'admin' or request.user.role == 'technician':
        qs = Ticket.objects.all()
    else:
        qs = Ticket.objects.filter(user=request.user)

    ticket_status = request.query_params.get('status')
    priority = request.query_params.get('priority')
    if ticket_status:
        qs = qs.filter(status=ticket_status)
    if priority:
        qs = qs.filter(priority=priority)

    return Response(TicketSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ticket_detail(request, ticket_id):
    try:
        if request.user.role in ['admin', 'technician']:
            ticket = Ticket.objects.get(pk=ticket_id)
        else:
            ticket = Ticket.objects.get(pk=ticket_id, user=request.user)
        return Response(TicketSerializer(ticket).data)
    except Ticket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=404)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_ticket_status(request, ticket_id):
    try:
        ticket = Ticket.objects.get(pk=ticket_id)
        if request.user.role not in ['admin', 'technician'] and ticket.user != request.user:
            return Response({'error': 'Not authorized'}, status=403)
        new_status = request.data.get('status')
        if new_status not in ['open', 'in_progress', 'resolved', 'closed']:
            return Response({'error': 'Invalid status'}, status=400)
        ticket.status = new_status
        if new_status == 'resolved':
            ticket.resolved_at = timezone.now()
            ticket.resolution_notes = request.data.get('resolution_notes', '')
        ticket.save()
        log_action('ticket_updated', request.user.email, f'Ticket #{ticket.pk} status → {new_status}', request)
        return Response(TicketSerializer(ticket).data)
    except Ticket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_to_ticket(request, ticket_id):
    try:
        if request.user.role in ['admin', 'technician']:
            ticket = Ticket.objects.get(pk=ticket_id)
        else:
            ticket = Ticket.objects.get(pk=ticket_id, user=request.user)
    except Ticket.DoesNotExist:
        return Response({'error': 'Ticket not found or access denied'}, status=404)

    message = request.data.get('message', '').strip()
    if not message:
        return Response({'error': 'Message is required'}, status=400)

    response = TicketResponse.objects.create(
        ticket=ticket,
        author=request.user,
        message=message,
        is_internal=request.data.get('is_internal', False),
    )
    log_action('ticket_updated', request.user.email, f'Response added to ticket #{ticket.pk}', request)
    return Response(TicketResponseSerializer(response).data, status=status.HTTP_201_CREATED)
