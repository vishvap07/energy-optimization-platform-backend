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
from .hf_client import HuggingFaceClient

logger = logging.getLogger(__name__)

_hf_client = None

def get_hf_client():
    """Return the singleton HuggingFaceClient."""
    global _hf_client
    if _hf_client is not None:
        return _hf_client
    try:
        if settings.HF_SPACE_ID:
            _hf_client = HuggingFaceClient()
            return _hf_client
    except Exception as exc:
        logger.warning("Could not initialize Hugging Face client: %s", exc)
    return None


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
    Use Hugging Face Space (or local LSTM fallback) to predict the next `days_ahead` daily totals.
    """
    hf_client = get_hf_client()
    local_svc = get_prediction_service()
    
    if hf_client is None and local_svc is None:
        return _generate_forecast_data(days_ahead), False, 'synthetic_fallback'

    try:
        from apps.analytics.models import EnergyData
        # Grab the latest 24 hourly readings as input sequence
        recent_qs = EnergyData.objects.all()[:24]
        if recent_qs.count() < 24:
            return _generate_forecast_data(days_ahead), False, 'insufficient_data'

        # Build feature lists
        recent = list(reversed(list(recent_qs)))
        consumption_list = [float(rec.consumption_kwh) for rec in recent]
        demand_list = [float(rec.demand_kw) for rec in recent]
        temp_list = [float(rec.temperature if rec.temperature is not None else 22.0) for rec in recent]

        results = []
        base_date = date.today()
        source = 'hugging_face' if hf_client else 'local_lstm'

        # Optimization: We keep the input lists for rolling forecast
        curr_c = list(consumption_list)
        curr_d = list(demand_list)
        curr_t = list(temp_list)

        for i in range(days_ahead):
            daily_total = 0.0
            # Predict 24 hours to get a daily total
            for h_idx in range(24):
                predicted_h_kwh = None
                
                # Hybrid Logic: Only call HF for the first 24 hours of prediction
                # (to avoid hundreds of sequential network calls)
                is_first_day = (i == 0)
                if hf_client and is_first_day:
                    predicted_h_kwh = hf_client.predict_next_hour(curr_c, curr_d, curr_t)
                
                # Fallback to local if HF fails, is absent, or after the first 24h
                if predicted_h_kwh is None and local_svc:
                    # Local service expects numpy array (24, 3)
                    input_seq = np.stack([curr_c, curr_d, curr_t], axis=1)
                    predicted_h_kwh = local_svc.predict_next(input_seq)
                    source = 'hugging_face'

                if predicted_h_kwh is None:
                    # Total failure, use mean or something
                    predicted_h_kwh = sum(curr_c) / 24

                daily_total += predicted_h_kwh
                
                # Roll input forward
                curr_c.pop(0)
                curr_c.append(predicted_h_kwh)
                curr_d.pop(0)
                curr_d.append(predicted_h_kwh * 0.9)
                curr_t.pop(0)
                curr_t.append(curr_t[-1]) # keep temp constant for projection
            
            d = base_date + timedelta(days=i)
            results.append({
                'date': d.isoformat(),
                'predicted_kwh': round(max(50.0, daily_total), 2),
                'actual_kwh': None,
                'confidence_upper': round(max(50.0, daily_total * 1.10), 2),
                'confidence_lower': round(max(30.0, daily_total * 0.90), 2),
            })

        return results, True, source

    except Exception as exc:
        logger.warning("LSTM prediction failed (%s) — using synthetic fallback.", exc)
        return _generate_forecast_data(days_ahead), False, 'error_fallback'


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

    forecast_data, used_lstm, source = _lstm_forecast(days)

    # Get the latest training job metrics (if any)
    latest_job = ModelTrainingJob.objects.filter(status='completed').order_by('-completed_at').first()
    mape = latest_job.mape if latest_job else None
    model_version = f'v1.0 ({source})' if used_lstm else f'v1.0 ({source})'

    result = {
        'forecast': forecast_data,
        'hourly_forecast': _hourly_forecast(),
        'model_version': model_version,
        'used_lstm': used_lstm,
        'source': source,
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
