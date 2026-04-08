from django.db import models


class ForecastResult(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    forecast_date = models.DateField()
    predicted_consumption = models.FloatField()
    actual_consumption = models.FloatField(null=True, blank=True)
    model_version = models.CharField(max_length=50, default='v1.0')
    rmse = models.FloatField(null=True, blank=True)
    mae = models.FloatField(null=True, blank=True)
    mape = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    predicted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'forecast_results'
        ordering = ['-forecast_date']

    def __str__(self):
        return f"Forecast {self.forecast_date}: {self.predicted_consumption} kWh"


class ModelTrainingJob(models.Model):
    STATUS_CHOICES = [('pending','Pending'),('running','Running'),('completed','Completed'),('failed','Failed')]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rmse = models.FloatField(null=True, blank=True)
    mae = models.FloatField(null=True, blank=True)
    mape = models.FloatField(null=True, blank=True)
    epochs = models.IntegerField(default=50)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'model_training_jobs'
        ordering = ['-started_at']
