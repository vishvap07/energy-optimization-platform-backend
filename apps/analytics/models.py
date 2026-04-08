from django.db import models


class EnergyData(models.Model):
    timestamp = models.DateTimeField()
    consumption_kwh = models.FloatField()
    demand_kw = models.FloatField()
    voltage = models.FloatField(default=230.0)
    current = models.FloatField(default=0.0)
    power_factor = models.FloatField(default=0.95)
    temperature = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=50, default='meter')
    location = models.CharField(max_length=100, default='Building A')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'energy_data'
        ordering = ['-timestamp']

    def __str__(self):
        return f"EnergyData @ {self.timestamp}: {self.consumption_kwh} kWh"
