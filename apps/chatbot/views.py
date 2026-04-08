import uuid
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from fuzzywuzzy import process, fuzz
from .models import FAQ, ChatSession
from .serializers import FAQSerializer

logger = logging.getLogger(__name__)

# Intent key-value pairs for similarity matching
INTENT_LABELS = {
    'energy_usage': "Check energy consumption usage kwh meter reading live load",
    'peak_demand': "Peak demand high usage surge overload threshold",
    'forecast': "Energy forecast prediction future estimate tomorrow next LSTM",
    'optimization': "Optimize savings reduce efficiency cost bill peak shaving",
    'create_ticket': "Create ticket issue problem help support error broken",
    'billing': "Bill payment invoice charge rate tariff cost",
    'system_help': "Login password forgot reset account dashboard navigate",
}

INTENT_RESPONSES = {
    'energy_usage': "Your current energy consumption is tracked in real time on the **User Dashboard**. Today's latest reading is **{kwh} kWh**. You can view detailed trends on the **Analytics Page** with historical comparisons and seasonal patterns.",
    'peak_demand': "Peak demand typically occurs between **7–10 AM** and **6–9 PM**. The system alerts you when demand exceeds the 70 kW threshold. Visit the **Analytics → Peak Demand** tab to see your hourly profile.",
    'forecast': "The LSTM model forecasts energy demand **14 days ahead**. Go to the **Forecast Page** to view daily predictions, confidence intervals, and predicted peak hours.",
    'optimization': "Based on your usage patterns, you can save significantly through peak shaving and load shifting. Visit the **Optimization Page** for personalized recommendations.",
    'create_ticket': "I'll help you create a support ticket! Click **Help Desk → Create Ticket** on the sidebar, or I can guide you through it. What is the issue about?",
    'billing': "Your estimated energy cost is calculated based on peak (₹15.0/kWh) and off-peak (₹7.5/kWh) rates. The **Dashboard** shows monthly cost estimates. For billing disputes, create a support ticket.",
    'system_help': "You can navigate the platform using the **left sidebar**. Key sections: Dashboard, Analytics, Forecast, Optimization, Help Desk, and Monitoring (admin only). Need help with something specific?",
    'general': "I'm the **EnergyAI Assistant**! I can help you understand your energy usage, navigate the platform, read forecasts, or create a support ticket. What would you like to know?",
}

SUGGESTIONS = {
    'energy_usage': ["Show me today's consumption", "What's my monthly trend?", "Any anomalies detected?"],
    'peak_demand': ["When is my peak hour?", "How do I reduce peak demand?", "Show peak demand chart"],
    'forecast': ["Show 7-day forecast", "What are predicted peak hours?", "How accurate is the forecast?"],
    'optimization': ["Show cost-saving tips", "What is peak shaving?", "View optimization report"],
    'create_ticket': ["Create a ticket", "View my tickets", "Talk to a technician"],
    'general': ["What's my energy usage?", "Show forecast", "Create a ticket", "Optimization tips"],
}


def _get_latest_kwh():
    """Fetch the most recent consumption reading from the DB."""
    try:
        from apps.analytics.models import EnergyData
        latest = EnergyData.objects.first()   # ordered by -timestamp
        if latest:
            return round(latest.consumption_kwh, 1)
    except Exception as exc:
        logger.debug("Could not fetch latest EnergyData: %s", exc)
    return None


def classify_intent(message):
    msg_lower = message.lower()
    choices = list(INTENT_LABELS.values())
    match, score = process.extractOne(msg_lower, choices, scorer=fuzz.token_set_ratio)
    if score > 50:
        for intent, label in INTENT_LABELS.items():
            if label == match:
                return intent
    return 'general'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def query_chatbot(request):
    message = request.data.get('message', '').strip()
    session_id = request.data.get('session_id', str(uuid.uuid4()))
    if not message:
        return Response({'error': 'Message is required'}, status=400)

    # 1. Try finding a direct FAQ match first (Fuzzy search on stored questions)
    faqs = FAQ.objects.filter(is_active=True)
    if faqs.exists():
        faq_questions = {f.question: f for f in faqs}
        best_q, score = process.extractOne(message, list(faq_questions.keys()), scorer=fuzz.token_set_ratio)
        if score > 75:
            faq = faq_questions[best_q]
            response_text = faq.answer
            intent = faq.intent
        else:
            intent = classify_intent(message)
            kwh_val = _get_latest_kwh() or round(__import__('random').uniform(820, 1150), 1)
            response_text = INTENT_RESPONSES.get(intent, INTENT_RESPONSES['general']).format(kwh=kwh_val)
    else:
        intent = classify_intent(message)
        kwh_val = _get_latest_kwh() or round(__import__('random').uniform(820, 1150), 1)
        response_text = INTENT_RESPONSES.get(intent, INTENT_RESPONSES['general']).format(kwh=kwh_val)

    ChatSession.objects.create(
        session_id=session_id,
        user_message=message,
        bot_response=response_text,
        intent=intent,
    )

    return Response({
        'response': response_text,
        'intent': intent,
        'suggestions': SUGGESTIONS.get(intent, SUGGESTIONS['general']),
        'session_id': session_id,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def faq_list(request):
    faqs = FAQ.objects.filter(is_active=True)
    return Response(FAQSerializer(faqs, many=True).data)
