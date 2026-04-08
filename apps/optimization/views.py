import logging
import math
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import OptimizationResult
from .serializers import OptimizationResultSerializer

logger = logging.getLogger(__name__)

PEAK_THRESHOLD_KW = 70.0
ENERGY_RATE_PEAK = 15.0       # ₹/kWh peak rate
ENERGY_RATE_OFFPEAK = 7.5     # ₹/kWh off-peak rate


# ---------------------------------------------------------------------------
# Static recommendation library — filtered based on real data
# ---------------------------------------------------------------------------

ALL_RECOMMENDATIONS = [
    {
        'id': 'hvac_shift',
        'title': 'Shift HVAC Load to Off-Peak Hours',
        'description': 'Pre-cool or pre-heat building between 11 PM – 6 AM to reduce peak demand.',
        'impact': 'High',
        'priority': 'critical',
        'estimated_savings_kwh': 180.0,
        'estimated_cost_savings': 2700.0,
        'category': 'load_shifting',
        'trigger': 'high_peak',       # shown when peak demand is high
    },
    {
        'id': 'demand_response',
        'title': 'Install Smart Demand Response Controls',
        'description': 'Automate non-critical loads to shed during peak hours (7–10 AM, 6–9 PM).',
        'impact': 'High',
        'priority': 'high',
        'estimated_savings_kwh': 220.0,
        'estimated_cost_savings': 3300.0,
        'category': 'demand_response',
        'trigger': 'high_peak',
    },
    {
        'id': 'led_upgrade',
        'title': 'LED Lighting Upgrade',
        'description': 'Replace fluorescent fixtures with LED to reduce base load by ~15%.',
        'impact': 'Medium',
        'priority': 'medium',
        'estimated_savings_kwh': 95.0,
        'estimated_cost_savings': 1425.0,
        'category': 'efficiency',
        'trigger': 'always',
    },
    {
        'id': 'stagger_startup',
        'title': 'Stagger Equipment Startup Times',
        'description': 'Avoid simultaneous startup of motors and compressors at 8 AM and 6 PM.',
        'impact': 'Medium',
        'priority': 'medium',
        'estimated_savings_kwh': 60.0,
        'estimated_cost_savings': 900.0,
        'category': 'peak_shaving',
        'trigger': 'always',
    },
    {
        'id': 'battery_storage',
        'title': 'Battery Energy Storage System',
        'description': 'Charge storage during off-peak hours and discharge during peak to cut demand charges.',
        'impact': 'Very High',
        'priority': 'high',
        'estimated_savings_kwh': 350.0,
        'estimated_cost_savings': 5250.0,
        'category': 'storage',
        'trigger': 'high_consumption',
    },
    {
        'id': 'power_factor',
        'title': 'Improve Power Factor',
        'description': 'Install capacitor banks to bring power factor above 0.95 and reduce reactive demand charges.',
        'impact': 'Medium',
        'priority': 'medium',
        'estimated_savings_kwh': 40.0,
        'estimated_cost_savings': 600.0,
        'category': 'efficiency',
        'trigger': 'low_pf',
    },
    {
        'id': 'anomaly_audit',
        'title': 'Investigate Consumption Anomalies',
        'description': 'Unusual spikes detected. An energy audit can identify faulty equipment or unauthorized usage.',
        'impact': 'High',
        'priority': 'critical',
        'estimated_savings_kwh': 120.0,
        'estimated_cost_savings': 1800.0,
        'category': 'audit',
        'trigger': 'has_anomalies',
    },
]


def _build_recommendations(user):
    """
    Build a filtered, data-driven recommendation list based on EnergyData.
    Falls back to full list if no data is available.
    """
    try:
        from apps.analytics.models import EnergyData
        from django.db.models import Avg, Max
        from apps.analytics.views import detect_anomalies

        qs = EnergyData.objects.all()
        if qs.count() < 10:
            # Not enough data — return all except trigger-specific ones
            return [r for r in ALL_RECOMMENDATIONS if r['trigger'] == 'always'], {}

        agg = qs.aggregate(avg_consumption=Avg('consumption_kwh'),
                           peak_demand=Max('demand_kw'),
                           avg_pf=Avg('power_factor'))

        is_admin = getattr(user, 'role', 'user') == 'admin' or user.is_staff or user.is_superuser
        anomaly_count = 0
        if is_admin:
            _, anomaly_count = detect_anomalies(qs)

        avg_consumption = agg['avg_consumption'] or 0
        peak_demand = agg['peak_demand'] or 0
        avg_pf = agg['avg_pf'] or 0.95

        conditions = {
            'high_peak': peak_demand > PEAK_THRESHOLD_KW,
            'high_consumption': avg_consumption > 900,
            'low_pf': avg_pf < 0.93,
            'has_anomalies': anomaly_count > 0,
            'always': True,
        }

        recs = [r for r in ALL_RECOMMENDATIONS if conditions.get(r['trigger'], False)]

        context = {
            'avg_consumption_kwh': round(avg_consumption, 2),
            'peak_demand_kw': round(peak_demand, 2),
            'avg_power_factor': round(avg_pf, 3),
        }
        return recs, context

    except Exception as exc:
        logger.warning("Could not build data-driven recommendations: %s", exc)
        return ALL_RECOMMENDATIONS, {}


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommendations(request):
    recs, context = _build_recommendations(request.user)

    # Strip internal 'trigger' field before returning
    clean_recs = [{k: v for k, v in r.items() if k != 'trigger'} for r in recs]

    total_savings_kwh = sum(r['estimated_savings_kwh'] for r in recs)
    total_cost_savings = sum(r['estimated_cost_savings'] for r in recs)

    return Response({
        'recommendations': clean_recs,
        'data_driven': bool(context),
        'context': context,
        'summary': {
            'total_recommendations': len(recs),
            'total_potential_savings_kwh': round(total_savings_kwh, 2),
            'total_potential_cost_savings': round(total_cost_savings, 2),
            'implementation_period_days': 90,
            'roi_estimate_months': 18,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def peak_shaving(request):
    """Return peak shaving analysis comparing before/after."""
    try:
        from apps.analytics.models import EnergyData
        from collections import defaultdict

        qs = EnergyData.objects.all()
        if qs.count() >= 48:
            # Use real hourly averages
            hour_buckets = defaultdict(list)
            for rec in qs.values('timestamp', 'demand_kw'):
                hour_buckets[rec['timestamp'].hour].append(rec['demand_kw'])

            hours = []
            for h in range(24):
                vals = hour_buckets.get(h, [])
                demand_before = round(sum(vals) / len(vals), 2) if vals else round(
                    max(10, 40 + 35 * math.sin(math.pi * (h - 6) / 12)), 2)
                is_peak = demand_before > PEAK_THRESHOLD_KW
                demand_after = round(demand_before * 0.75, 2) if is_peak else demand_before
                hours.append({
                    'hour': h,
                    'label': f"{h:02d}:00",
                    'demand_before_kw': demand_before,
                    'demand_after_kw': demand_after,
                    'shaved_kw': round(demand_before - demand_after, 2),
                    'is_peak': is_peak,
                    'rate': ENERGY_RATE_PEAK if is_peak else ENERGY_RATE_OFFPEAK,
                })
        else:
            # Synthetic fallback — deterministic sine curve (no random)
            hours = []
            for h in range(24):
                base = 40 + 35 * math.sin(math.pi * (h - 6) / 12)
                demand_before = round(max(10, base), 2)
                is_peak = demand_before > PEAK_THRESHOLD_KW
                demand_after = round(demand_before * 0.75, 2) if is_peak else demand_before
                hours.append({
                    'hour': h,
                    'label': f"{h:02d}:00",
                    'demand_before_kw': demand_before,
                    'demand_after_kw': demand_after,
                    'shaved_kw': round(demand_before - demand_after, 2),
                    'is_peak': is_peak,
                    'rate': ENERGY_RATE_PEAK if is_peak else ENERGY_RATE_OFFPEAK,
                })
    except Exception:
        hours = []
        for h in range(24):
            base = 40 + 35 * math.sin(math.pi * (h - 6) / 12)
            demand_before = round(max(10, base), 2)
            is_peak = demand_before > PEAK_THRESHOLD_KW
            demand_after = round(demand_before * 0.75, 2) if is_peak else demand_before
            hours.append({
                'hour': h, 'label': f"{h:02d}:00",
                'demand_before_kw': demand_before, 'demand_after_kw': demand_after,
                'shaved_kw': round(demand_before - demand_after, 2),
                'is_peak': is_peak, 'rate': ENERGY_RATE_PEAK if is_peak else ENERGY_RATE_OFFPEAK,
            })

    cost_before = sum(h['demand_before_kw'] * h['rate'] for h in hours)
    cost_after = sum(h['demand_after_kw'] * h['rate'] for h in hours)
    return Response({
        'threshold_kw': PEAK_THRESHOLD_KW,
        'hourly': hours,
        'cost_before': round(cost_before, 2),
        'cost_after': round(cost_after, 2),
        'cost_savings': round(cost_before - cost_after, 2),
        'savings_percent': round((cost_before - cost_after) / cost_before * 100, 1) if cost_before > 0 else 0,
    })
