import logging
import math
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Avg, Max, Min, Sum
from django.utils import timezone
from datetime import timedelta
import random

from .models import EnergyData
from .serializers import EnergyDataSerializer, AnalyticsSummarySerializer

logger = logging.getLogger(__name__)

RATE_PEAK = 15.0      # ₹/kWh peak
RATE_OFFPEAK = 7.5    # ₹/kWh off-peak


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_demo_data():
    """Generate in-memory demo data if DB is empty."""
    from datetime import datetime
    data = []
    base = datetime(2024, 1, 1, 0, 0)
    for i in range(720):  # 30 days hourly
        hour = (base + timedelta(hours=i)).hour
        base_val = 45 + 20 * math.sin(math.pi * hour / 12) + random.gauss(0, 5)
        data.append({
            'timestamp': (base + timedelta(hours=i)).isoformat(),
            'consumption_kwh': round(max(10, base_val), 2),
            'demand_kw': round(max(5, base_val * 0.9), 2),
            'temperature': round(20 + 10 * math.sin(math.pi * (i % 24) / 12) + random.gauss(0, 2), 1),
        })
    return data


def detect_anomalies(qs):
    """
    Z-score anomaly detection on consumption_kwh.
    Returns a list of anomalous EnergyData PKs and the count.
    """
    if qs.count() < 10:
        return [], 0

    values = list(qs.values_list('consumption_kwh', flat=True))
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = variance ** 0.5

    if std == 0:
        return [], 0

    threshold = 2.5
    anomaly_ids = []
    for rec in qs.values('id', 'consumption_kwh'):
        z = abs(rec['consumption_kwh'] - mean) / std
        if z > threshold:
            anomaly_ids.append(rec['id'])

    return anomaly_ids, len(anomaly_ids)


def _get_hourly_peak_from_db():
    """
    Compute real hourly average demand from EnergyData.
    Returns list of 24 hour buckets or None if not enough data.
    """
    qs = EnergyData.objects.all()
    if qs.count() < 48:
        return None

    # Group by hour-of-day — use Python since SQLite doesn't have EXTRACT
    from collections import defaultdict
    hour_buckets = defaultdict(list)
    for rec in qs.values('timestamp', 'demand_kw'):
        hour_buckets[rec['timestamp'].hour].append(rec['demand_kw'])

    PEAK_THRESHOLD_KW = 70.0
    result = []
    for h in range(24):
        vals = hour_buckets.get(h, [])
        avg = sum(vals) / len(vals) if vals else 0.0
        result.append({
            'hour': h,
            'label': f"{h:02d}:00",
            'avg_demand_kw': round(avg, 2),
            'is_peak': avg > PEAK_THRESHOLD_KW,
        })
    return result


def _ensure_live_data():
    """
    Ensure the DB has records up to the current hour.
    If the latest record is old, backfill missing hours with realistic simulated data.
    """
    try:
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        latest = EnergyData.objects.order_by('-timestamp').first()
        
        if not latest:
            return
            
        last_time = latest.timestamp.replace(minute=0, second=0, microsecond=0)
        
        # Max backfill to avoid long loops if DB is ancient
        limit = 500 
        count = 0
        
        while last_time < now and count < limit:
            last_time += timedelta(hours=1)
            hour = last_time.hour
            # Seasonal pattern matching seed_data
            base_val = 45 + 20 * math.sin(math.pi * hour / 12) + random.gauss(0, 5)
            EnergyData.objects.create(
                timestamp=last_time,
                consumption_kwh=round(max(10, base_val), 2),
                demand_kw=round(max(5, base_val * 0.9), 2),
                temperature=round(22 + 8 * math.sin(math.pi * (hour - 6) / 12) + random.gauss(0, 1), 1),
                source='simulated_live'
            )
            count += 1
            
        if count > 0:
            logger.info(f"Backfilled {count} live energy records.")
            
    except Exception as e:
        logger.error(f"Failed to generate live data: {e}")


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def energy_data(request):
    if request.method == 'GET':
        # Ensure data is up to date before fetching
        _ensure_live_data()
        
        days = int(request.query_params.get('days', 30))
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 100))

        since = timezone.now() - timedelta(days=days)
        qs = EnergyData.objects.filter(timestamp__gte=since)

        if qs.count() == 0:
            return Response({'demo': True, 'data': generate_demo_data()})

        # Simple manual pagination (avoids DRF pagination boilerplate for this endpoint)
        start = (page - 1) * page_size
        end = start + page_size
        sliced_qs = qs[start:end]
        return Response({
            'demo': False,
            'total': qs.count(),
            'page': page,
            'page_size': page_size,
            'data': EnergyDataSerializer(sliced_qs, many=True).data,
        })

    if request.method == 'POST':
        serializer = EnergyDataSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_csv(request):
    """Handle CSV file uploads for bulk data ingestion."""
    if 'file' not in request.FILES:
        return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

    csv_file = request.FILES['file']
    if not csv_file.name.endswith('.csv'):
        return Response({'error': 'File must be a CSV'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        import pandas as pd
        import numpy as np
        df = pd.read_csv(csv_file)

        required = ['timestamp', 'consumption_kwh', 'demand_kw']
        if not all(col in df.columns for col in required):
            return Response({'error': f'Missing columns. Required: {required}'}, status=status.HTTP_400_BAD_REQUEST)

        # Analysis logic (Simulation Mode)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        total_rows = len(df)
        avg_consumption = df['consumption_kwh'].mean()
        max_demand = df['demand_kw'].max()
        total_consumption = df['consumption_kwh'].sum()
        
        # Simple Z-score anomaly detection within the file
        std = df['consumption_kwh'].std()
        mean = df['consumption_kwh'].mean()
        anomalies_df = df[np.abs(df['consumption_kwh'] - mean) > (2.5 * std)] if std > 0 else pd.DataFrame()
        
        # Prepare graph data (top 100 points to keep response light)
        chart_data = df.head(100)[['timestamp', 'consumption_kwh', 'demand_kw']].to_dict(orient='records')

        return Response({
            'message': 'Simulation analysis complete. Data was analyzed but NOT saved to production database.',
            'simulation': True,
            'summary': {
                'total_rows': total_rows,
                'total_consumption_kwh': round(total_consumption, 2),
                'avg_consumption_kwh': round(avg_consumption, 2),
                'peak_demand_kw': round(max_demand, 2),
                'anomaly_count': len(anomalies_df),
                'cost_estimate': round(total_consumption * 15.0 * 0.4 + total_consumption * 7.5 * 0.6, 2)
            },
            'chart_data': chart_data,
            'anomalous_records': anomalies_df.head(10).to_dict(orient='records')
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_summary(request):
    # Ensure data is up to date
    _ensure_live_data()
    
    is_admin = getattr(request.user, 'role', 'user') == 'admin' or request.user.is_staff or request.user.is_superuser
    
    # Filter to last 30 days for dashboard consistency (Rolling Billing Cycle)
    now = timezone.now()
    since = now - timedelta(days=30)
    qs = EnergyData.objects.filter(timestamp__gte=since)
    
    if qs.count() == 0:
        # Fallback to demo data if no records in last 30 days
        return Response({
            'total_consumption_kwh': 34560.5,
            'avg_daily_kwh': 1152.0,
            'peak_demand_kw': 98.4,
            'peak_hour': 19,
            'min_consumption_kwh': 620.1,
            'max_consumption_kwh': 1820.3,
            'anomaly_count': 3 if is_admin else 0,
            'anomalous_records': [
                {'id': 9991, 'timestamp': '2026-04-01T14:00:00Z', 'consumption_kwh': 2950.5, 'demand_kw': 180.2},
                {'id': 9992, 'timestamp': '2026-04-02T09:30:00Z', 'consumption_kwh': 3100.8, 'demand_kw': 195.4},
                {'id': 9993, 'timestamp': '2026-04-03T18:15:00Z', 'consumption_kwh': 2850.1, 'demand_kw': 175.5}
            ] if is_admin else [],
            'cost_estimate': 362885.25,
            'demo': True,
        })

    agg = qs.aggregate(
        total=Sum('consumption_kwh'),
        avg=Avg('consumption_kwh'),
        peak=Max('demand_kw'),
        min_c=Min('consumption_kwh'),
        max_c=Max('consumption_kwh'),
    )

    anomaly_count = 0
    anomalous_data = []

    if is_admin:
        anomaly_ids, anomaly_count = detect_anomalies(qs)
        if anomaly_ids:
            anomalous_qs = qs.filter(id__in=anomaly_ids)
            anomalous_data = EnergyDataSerializer(anomalous_qs, many=True).data

    total = agg['total'] or 0
    cost = total * RATE_PEAK * 0.4 + total * RATE_OFFPEAK * 0.6   # 40% peak, 60% off-peak

    return Response({
        'demo': False,
        'total_consumption_kwh': round(total, 2),
        'avg_daily_kwh': round(agg['avg'] or 0, 2),
        'peak_demand_kw': round(agg['peak'] or 0, 2),
        'peak_hour': 19,
        'min_consumption_kwh': round(agg['min_c'] or 0, 2),
        'max_consumption_kwh': round(agg['max_c'] or 0, 2),
        'anomaly_count': anomaly_count,
        'anomalous_records': anomalous_data,
        'cost_estimate': round(cost, 2),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def peak_demand(request):
    """Real hourly demand profile from DB, or synthetic fallback."""
    real_hours = _get_hourly_peak_from_db()
    if real_hours is not None:
        return Response({'peak_hours': real_hours, 'threshold_kw': 70.0, 'source': 'real'})

    # Synthetic fallback — deterministic (no random), so it doesn't change per-request
    hours = []
    for h in range(24):
        base = 40 + 30 * math.sin(math.pi * (h - 6) / 12)
        is_peak = h in [7, 8, 9, 18, 19, 20]
        hours.append({
            'hour': h,
            'label': f"{h:02d}:00",
            'avg_demand_kw': round(max(15, base), 2),
            'is_peak': is_peak,
        })
    return Response({'peak_hours': hours, 'threshold_kw': 70.0, 'source': 'synthetic'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_alerts(request):
    """
    Compare recent 24h average consumption vs 30-day rolling average.
    Return structured alert objects for the dashboard.
    """
    now = timezone.now()
    recent_24h = EnergyData.objects.filter(timestamp__gte=now - timedelta(hours=24))
    last_30d = EnergyData.objects.filter(timestamp__gte=now - timedelta(days=30))

    alerts = []

    if recent_24h.count() > 0 and last_30d.count() > 0:
        avg_24h = recent_24h.aggregate(a=Avg('consumption_kwh'))['a'] or 0
        avg_30d = last_30d.aggregate(a=Avg('consumption_kwh'))['a'] or 0

        if avg_30d > 0:
            pct_change = ((avg_24h - avg_30d) / avg_30d) * 100
            if pct_change > 10:
                alerts.append({
                    'type': 'warning',
                    'title': 'Above-average consumption detected',
                    'message': f'Today\'s usage is {pct_change:.1f}% above your 30-day average.',
                })
            elif pct_change < -10:
                alerts.append({
                    'type': 'success',
                    'title': 'Great progress on energy savings!',
                    'message': f'Today\'s usage is {abs(pct_change):.1f}% below your 30-day average.',
                })

        # Peak-hour alert: check current hour
        current_hour = now.hour
        if current_hour in [6, 7, 17, 18]:
            alerts.append({
                'type': 'warning',
                'title': 'Peak hour approaching',
                'message': 'High loads typically occur 7–10 AM and 6–9 PM. Consider shifting non-critical loads.',
            })

        # Anomaly check for admins only
        is_admin = getattr(request.user, 'role', 'user') == 'admin'
        if is_admin:
            _, anomaly_count = detect_anomalies(last_30d)
            if anomaly_count > 0:
                alerts.append({
                    'type': 'error',
                    'title': f'{anomaly_count} consumption anomalies detected',
                    'message': 'Unusual spikes found in the last 30 days. Check Analytics for details.',
                })
    else:
        # Fallback hints when no real data
        alerts = [
            {
                'type': 'info',
                'title': 'Peak hour approaching',
                'message': 'Historically high loads detected between 6 PM and 9 PM.',
            },
            {
                'type': 'info',
                'title': 'Optimization available',
                'message': '3 recommendations can save you an estimated ₹12,000 this month.',
            },
        ]

    return Response({'alerts': alerts, 'generated_at': now.isoformat()})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_csv(request):
    """Stream EnergyData as a downloadable CSV file."""
    import csv
    from django.http import StreamingHttpResponse

    def _rows():
        yield 'timestamp,consumption_kwh,demand_kw,voltage,current,power_factor,temperature,source,location\n'
        for rec in EnergyData.objects.all().iterator():
            yield (
                f"{rec.timestamp},{rec.consumption_kwh},{rec.demand_kw},"
                f"{rec.voltage},{rec.current},{rec.power_factor},"
                f"{rec.temperature or ''},{rec.source},{rec.location}\n"
            )

    response = StreamingHttpResponse(_rows(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="energy_data_export.csv"'
    return response
