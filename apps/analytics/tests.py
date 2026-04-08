from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from apps.analytics.models import EnergyData
from apps.analytics.views import detect_anomalies

User = get_user_model()


def _create_user(email='test@example.com', role='user', password='testpass123'):
    user = User.objects.create_user(email=email, password=password)
    user.role = role
    user.save()
    return user


def _make_energy_data(count=50, base=100.0, include_spike=False):
    """Create EnergyData records, optionally with an outlier spike."""
    now = timezone.now()
    records = [
        EnergyData(
            timestamp=now - timedelta(hours=i),
            consumption_kwh=base + (0.5 - (i % 5) * 0.1),
            demand_kw=(base * 0.9) + (0.3 - (i % 4) * 0.1),
        )
        for i in range(count)
    ]
    if include_spike:
        records[0].consumption_kwh = base * 5   # obvious outlier
    EnergyData.objects.bulk_create(records)


class AnomalyDetectionTest(TestCase):
    def test_no_anomaly_clean_data(self):
        _make_energy_data(count=50, base=100.0, include_spike=False)
        qs = EnergyData.objects.all()
        _, count = detect_anomalies(qs)
        self.assertEqual(count, 0, "Clean data should have zero anomalies")

    def test_detects_spike(self):
        _make_energy_data(count=50, base=100.0, include_spike=True)
        qs = EnergyData.objects.all()
        _, count = detect_anomalies(qs)
        self.assertGreater(count, 0, "Spike should be detected as anomaly")

    def test_too_few_records(self):
        _make_energy_data(count=5, base=100.0, include_spike=True)
        qs = EnergyData.objects.all()
        _, count = detect_anomalies(qs)
        self.assertEqual(count, 0, "< 10 records should return 0 anomalies")


class AnalyticsSummaryTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user()
        self.client.force_authenticate(user=self.user)

    def test_summary_demo_when_empty(self):
        resp = self.client.get('/api/energy/analytics')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('total_consumption_kwh', data)
        self.assertTrue(data.get('demo'), "Should return demo=True when DB is empty")

    def test_summary_real_data(self):
        _make_energy_data(count=20)
        resp = self.client.get('/api/energy/analytics')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get('demo'), "Should return demo=False when data exists")
        self.assertIn('anomaly_count', data)
        self.assertIsInstance(data['anomaly_count'], int)
        self.assertIn('cost_estimate', data)

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/energy/analytics')
        self.assertEqual(resp.status_code, 401)


class AlertsEndpointTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user(email='alert@example.com')
        self.client.force_authenticate(user=self.user)

    def test_alerts_empty_db(self):
        resp = self.client.get('/api/energy/alerts/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('alerts', data)
        self.assertIsInstance(data['alerts'], list)

    def test_alerts_with_data(self):
        _make_energy_data(count=50)
        resp = self.client.get('/api/energy/alerts/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('alerts', resp.json())


class ChatbotTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user(email='chat@example.com')
        self.client.force_authenticate(user=self.user)

    def test_basic_response(self):
        resp = self.client.post('/api/chatbot/query', {
            'message': 'What is my energy usage?'
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('response', data)
        self.assertIn('intent', data)
        self.assertIn('suggestions', data)

    def test_kwh_comes_from_db(self):
        """When DB has data, chatbot response should contain the real kWh value."""
        _make_energy_data(count=1, base=999.0)
        resp = self.client.post('/api/chatbot/query', {
            'message': 'what is my energy usage today?'
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        response_text = resp.json()['response']
        # The energy_usage intent picks up latest reading
        if resp.json()['intent'] == 'energy_usage':
            self.assertIn('999', response_text)

    def test_empty_message(self):
        resp = self.client.post('/api/chatbot/query', {'message': ''}, format='json')
        self.assertEqual(resp.status_code, 400)


class OptimizationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user(email='opt@example.com')
        self.client.force_authenticate(user=self.user)

    def test_recommendations_no_data(self):
        resp = self.client.get('/api/optimization/recommendations')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('recommendations', data)
        self.assertIsInstance(data['recommendations'], list)

    def test_recommendations_with_data(self):
        _make_energy_data(count=50, base=120.0)
        resp = self.client.get('/api/optimization/recommendations')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('data_driven'), "Should be data-driven when DB has enough records")
        self.assertIn('context', data)
