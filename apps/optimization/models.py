from django.db import models


class OptimizationResult(models.Model):
    STRATEGY_CHOICES = [
        ('peak_shaving', 'Peak Shaving'),
        ('load_shifting', 'Load Shifting'),
        ('demand_response', 'Demand Response'),
    ]
    date = models.DateField()
    strategy = models.CharField(max_length=50, choices=STRATEGY_CHOICES, default='peak_shaving')
    peak_demand_before = models.FloatField()
    peak_demand_after = models.FloatField()
    cost_before = models.FloatField()
    cost_after = models.FloatField()
    savings_kwh = models.FloatField()
    savings_cost = models.FloatField()
    recommendations = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'optimization_results'
        ordering = ['-date']

    def __str__(self):
        return f"Optimization {self.date}: saved ${self.savings_cost:.2f}"
