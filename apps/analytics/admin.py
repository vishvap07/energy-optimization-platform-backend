from django.contrib import admin
from .models import EnergyData

@admin.register(EnergyData)
class EnergyDataAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'consumption_kwh', 'demand_kw', 'source', 'location')
    list_filter = ('source', 'location', 'timestamp')
    search_fields = ('location', 'source')
