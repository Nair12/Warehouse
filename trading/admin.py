from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from .models import Trading, TradingItem


class TradingItemInline(admin.TabularInline):
    model = TradingItem
    extra = 1
    fields = (
        'product',
        'warehouse',
        'quantity',
        'quantity_before',
        'quantity_after',
    )


@admin.register(Trading)
class TradingAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'name',
        'user',
        'trade_type',
        'product',
        'warehouse',
        'quantity',
        'quantity_before',
        'quantity_after',
    )

    list_filter = (
        'trade_type',
        'warehouse',
        'user',
        'created_at',
    )

    search_fields = (
        'name',
        'product__name',
        'user__username',
        'warehouse__city',
    )

    ordering = ('-created_at',)
    inlines = [TradingItemInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'history-page/',
                self.admin_site.admin_view(self.history_page_view),
                name='trading_trading_history_page',
            ),
        ]
        return custom_urls + urls

    def history_page_view(self, request):
        tradings = Trading.objects.select_related(
            'product',
            'warehouse',
            'user',
        ).order_by('-created_at')

        context = dict(
            self.admin_site.each_context(request),
            title='История операций по складу',
            tradings=tradings,
        )

        return TemplateResponse(
            request,
            'admin/trading/history_page.html',
            context,
        )


@admin.register(TradingItem)
class TradingItemAdmin(admin.ModelAdmin):
    list_display = (
        'trading',
        'product',
        'warehouse',
        'quantity',
        'quantity_before',
        'quantity_after',
        'created_at',
    )

    list_filter = (
        'warehouse',
        'created_at',
    )

    search_fields = (
        'trading__name',
        'product__name',
        'warehouse__city',
    )

    ordering = ('-created_at',)