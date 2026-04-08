import logging
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from datetime import timedelta, date
import random
import math
import numpy as np

from .models import ForecastResult, ModelTrainingJob
from .serializers import ForecastResultSerializer, ModelTrainingJobSerializer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Singleton prediction service — loaded once at startup (in apps.py ready())
# ---------------------------------------------------------------------------
_prediction_service = None


def get_prediction_service():
    """Return the singleton PredictionService, or None if model not trained."""
    global _prediction_service
    if _prediction_service is not None:
        return _prediction_service
    try:
        from ml_models.prediction_service import PredictionService
        svc = PredictionService(
            model_path=settings.ML_MODEL_PATH,
            scaler_path=settings.ML_SCALER_PATH,
        )
        svc.load_artifacts()   # raises FileNotFoundError if model absent
        _prediction_service = svc
        logger.info("LSTM PredictionService loaded successfully.")
        return _prediction_service
    except FileNotFoundError:
        logger.warning("LSTM model not found — forecasting will use synthetic fallback.")
        return None
    except Exception as exc:
        logger.warning("Could not load LSTM model (%s) — using synthetic fallback.", exc)
        return None


# ---------------------------------------------------------------------------
# Synthetic fallback generators (used when model not trained yet)
# ---------------------------------------------------------------------------

def _generate_forecast_data(days_ahead=14):
    """Generate synthetic forecast predictions."""
    results = []
    base_date = date.today()
    for i in range(days_ahead):
        d = base_date + timedelta(days=i)
        day_of_week = d.weekday()
        base = 950 if day_of_week < 5 else 680
        predicted = base + random.gauss(0, 60)
        actual = predicted + random.gauss(0, 40) if i < 7 else None
        results.append({
            'date': d.isoformat(),
            'predicted_kwh': round(max(400, predicted), 2),
            'actual_kwh': round(max(400, actual), 2) if actual else None,
            'confidence_upper': round(max(400, predicted + 80), 2),
            'confidence_lower': round(max(200, predicted - 80), 2),
        })
    return results


def _hourly_forecast():
    """Generate 24-hour synthetic forecast."""
    hours = []
    for h in range(24):
        base = 40 + 35 * math.sin(math.pi * (h - 6) / 12)
        hours.append({
            'hour': h,
            'label': f"{h:02d}:00",
            'predicted_kw': round(max(10, base + random.gauss(0, 4)), 2),
            'is_peak_hour': h in [7, 8, 9, 18, 19, 20],
        })
    return hours


# ---------------------------------------------------------------------------
# LSTM-powered daily forecast
# ---------------------------------------------------------------------------

def _lstm_forecast(days_ahead=14):
    """
    Use the real LSTM model to predict the next `days_ahead` daily totals.
    Falls back to synthetic data if the model isn't available.
    """
    svc = get_prediction_service()
    if svc is None:
        return _generate_forecast_data(days_ahead), False

    try:
        from apps.analytics.models import EnergyData
        # Grab the latest 24 hourly readings as input sequence
        recent_qs = EnergyData.objects.all()[:24]
        if recent_qs.count() < 24:
            return _generate_forecast_data(days_ahead), False

        # Build feature matrix: [consumption_kwh, demand_kw, temperature]
        recent = list(reversed(list(recent_qs)))
        feature_rows = []
        for rec in recent:
            feature_rows.append([
                rec.consumption_kwh,
                rec.demand_kw,
                rec.temperature if rec.temperature is not None else 22.0,
            ])
        input_seq = np.array(feature_rows, dtype=float)

        results = []
        base_date = date.today()
        for i in range(days_ahead):
            daily_total = 0.0
            # Predict 24 hours to get a daily total
            for _ in range(24):
                predicted_h_kwh = svc.predict_next(input_seq)
                daily_total += predicted_h_kwh
                # Roll input forward: drop oldest row, append new prediction row
                # We estimate demand_kw as ~0.9 * consumption_kwh and keep temp constant for now
                new_row = np.array([[predicted_h_kwh, predicted_h_kwh * 0.9, 22.0]])
                input_seq = np.vstack([input_seq[1:], new_row])
            
            d = base_date + timedelta(days=i)
            results.append({
                'date': d.isoformat(),
                'predicted_kwh': round(max(50.0, daily_total), 2),
                'actual_kwh': None,
                'confidence_upper': round(max(50.0, daily_total * 1.10), 2),
                'confidence_lower': round(max(30.0, daily_total * 0.90), 2),
            })

        return results, True

    except Exception as exc:
        logger.warning("LSTM prediction failed (%s) — using synthetic fallback.", exc)
        return _generate_forecast_data(days_ahead), False


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

from django.core.cache import cache

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def train_model(request):
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=403)

    # Create a job record with pending status
    job = ModelTrainingJob.objects.create(status='running')

    try:
        from ml_models.training_pipeline import train_and_evaluate
        rmse, mae, mape = train_and_evaluate(
            csv_path=settings.ML_CSV_PATH,
            model_path=settings.ML_MODEL_PATH,
            scaler_path=settings.ML_SCALER_PATH,
            epochs=30,
            batch_size=64,
            seq_length=24,
        )
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.rmse = round(rmse, 4)
        job.mae = round(mae, 4)
        job.mape = round(mape, 4)
        job.epochs = 30
        job.notes = 'Training completed via API.'
        job.save()

        # Invalidate cache and singleton
        global _prediction_service
        _prediction_service = None
        cache.delete('energy_forecast_14d')

        from apps.monitoring.utils import log_action
        log_action('model_trained', request.user.email,
                   f'Model training job #{job.pk} completed. RMSE={rmse:.2f}', request)

        return Response({
            'job_id': job.pk,
            'status': 'completed',
            'metrics': {'rmse': job.rmse, 'mae': job.mae, 'mape': job.mape},
            'message': 'LSTM model trained successfully.',
        })

    except Exception as exc:
        job.status = 'failed'
        job.notes = str(exc)
        job.save()
        logger.exception("Model training failed")
        return Response({'error': str(exc), 'job_id': job.pk}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def predict(request):
    days = int(request.query_params.get('days', 14))
    
    # Check cache
    cache_key = f'energy_forecast_{days}d'
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response({**cached_data, 'cached': True})

    forecast_data, used_lstm = _lstm_forecast(days)

    # Get the latest training job metrics (if any)
    latest_job = ModelTrainingJob.objects.filter(status='completed').order_by('-completed_at').first()
    mape = latest_job.mape if latest_job else None
    model_version = 'v1.0 (LSTM)' if used_lstm else 'v1.0 (synthetic)'

    result = {
        'forecast': forecast_data,
        'hourly_forecast': _hourly_forecast(),
        'model_version': model_version,
        'used_lstm': used_lstm,
        'mape': mape,
        'generated_at': timezone.now().isoformat(),
    }
    
    # Store in cache for 1 hour
    cache.set(cache_key, result, 3600)

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def forecast_results(request):
    qs = ForecastResult.objects.all()[:30]
    if qs.count() == 0:
        return Response({'demo': True, 'results': _generate_forecast_data(30)})
    return Response({'demo': False, 'results': ForecastResultSerializer(qs, many=True).data})
