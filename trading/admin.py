from django.contrib import admin
from .models import Trading


@admin.register(Trading)
class TradingAdmin(admin.ModelAdmin):
    list_display = ('id', 'trade_type', 'product', 'user', 'quantity', 'timestamp')
    list_filter = ('trade_type', 'timestamp')