import random
import math
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.analytics.models import EnergyData

class Command(BaseCommand):
    help = 'Seeds the database with 30 days of hourly energy data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding energy data...')
        
        if EnergyData.objects.count() > 700:
            self.stdout.write(self.style.SUCCESS('Database already has enough data.'))
            return

        now = timezone.now()
        records = []
        
        # 720 hours = 30 days
        for i in range(720, 0, -1):
            ts = now - timedelta(hours=i)
            hour = ts.hour
            
            # Realistic consumption curve (higher in evening/morning)
            # base value between 30 and 80 kWh
            base_val = 50 + 25 * math.sin(math.pi * (hour - 6) / 12) + random.uniform(-5, 5)
            consumption = round(max(10, base_val), 2)
            demand = round(max(5, consumption * 0.85 + random.uniform(-2, 2)), 2)
            temp = round(22 + 8 * math.sin(math.pi * (hour - 12) / 12) + random.uniform(-1, 1), 1)
            
            records.append(EnergyData(
                timestamp=ts,
                consumption_kwh=consumption,
                demand_kw=demand,
                voltage=231.5 + random.uniform(-2, 2),
                current=consumption / 0.230, # dummy calc
                power_factor=0.92 + random.uniform(-0.05, 0.05),
                temperature=temp,
                source='smart_meter',
                location='Main Building'
            ))

        EnergyData.objects.bulk_create(records)
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {len(records)} records.'))
