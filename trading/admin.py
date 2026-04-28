from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe
from django.db.models import Q

from .models import Trading, TradingItem, TradingAuditLog


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


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


@admin.register(TradingAuditLog)
class TradingAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'trading_id_snapshot',
        'deal_name_display',
        'last_action_display',
        'user',
        'created_at',
    )

    list_filter = (
        'action',
        'created_at',
        'user',
    )

    search_fields = (
        'description',
        'trading_id_snapshot',
        'user__username',
    )

    ordering = ('-created_at',)

    readonly_fields = (
        'deal_header',
        'deal_history',
    )

    fields = (
        'deal_header',
        'deal_history',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        latest_ids = []
        seen_deals = set()

        for log in queryset.order_by('-created_at', '-id'):
            key = log.trading_id_snapshot or log.trading_id

            if key in seen_deals:
                continue

            seen_deals.add(key)
            latest_ids.append(log.id)

        return queryset.filter(id__in=latest_ids)

    def get_search_results(self, request, queryset, search_term):
        search_term = (search_term or '').strip().lower()

        if not search_term:
            return queryset, False

        matched_deal_ids = set()

        all_logs = TradingAuditLog.objects.select_related('user')

        for log in all_logs:
            deal_id = log.trading_id_snapshot or log.trading_id

            before_data = log.before_data or {}
            after_data = log.after_data or {}

            before_name = str(before_data.get('name') or '').lower()
            after_name = str(after_data.get('name') or '').lower()
            description = str(log.description or '').lower()
            username = str(log.user.username if log.user else '').lower()
            deal_id_text = str(deal_id or '').lower()

            if (
                search_term in before_name
                or search_term in after_name
                or search_term in description
                or search_term in username
                or search_term in deal_id_text
            ):
                matched_deal_ids.add(deal_id)

        if matched_deal_ids:
            queryset = self.get_queryset(request).filter(
                Q(trading_id_snapshot__in=matched_deal_ids)
                | Q(trading_id__in=matched_deal_ids)
            )
        else:
            queryset = self.get_queryset(request).none()

        return queryset, False

    def deal_name_display(self, obj):
        data = obj.after_data or obj.before_data or {}
        return data.get('name') or 'Без названия'

    deal_name_display.short_description = 'Название сделки'

    def last_action_display(self, obj):
        return obj.get_action_display()

    last_action_display.short_description = 'Последнее действие'

    def get_all_logs_for_deal(self, obj):
        deal_id = obj.trading_id_snapshot or obj.trading_id

        return TradingAuditLog.objects.filter(
            Q(trading_id_snapshot=deal_id) | Q(trading_id=deal_id)
        ).select_related('user').order_by('created_at', 'id')

    def deal_header(self, obj):
        data = obj.after_data or obj.before_data or {}
        deal_name = data.get('name') or 'Без названия'
        deal_id = obj.trading_id_snapshot or obj.trading_id
        trade_type = data.get('trade_type')

        if trade_type == 'purchase':
            trade_label = 'Покупка'
            trade_color = '#2ecc71'
            trade_icon = '➕'
        elif trade_type == 'sell':
            trade_label = 'Продажа'
            trade_color = '#e74c3c'
            trade_icon = '➖'
        else:
            trade_label = '—'
            trade_color = '#888'
            trade_icon = '•'

        logs_count = TradingAuditLog.objects.filter(
            Q(trading_id_snapshot=deal_id) | Q(trading_id=deal_id)
        ).count()

        html = f'''
        <div style="background:#1e1e1e;border:1px solid #333;border-radius:14px;padding:18px;margin-bottom:18px;">
            <div style="font-size:13px;color:#aaa;margin-bottom:6px;">
                История сделки
            </div>

            <div style="font-size:26px;font-weight:800;color:white;">
                {deal_name}
            </div>

            <div style="margin-top:10px;">
                <span style="background:{trade_color};color:white;padding:5px 12px;border-radius:999px;font-size:13px;font-weight:700;display:inline-block;">
                    {trade_icon} {trade_label}
                </span>
            </div>

            <div style="margin-top:14px;color:#aaa;">
                ID: <b style="color:white;">#{deal_id}</b>
                <span style="margin:0 8px;">|</span>
                Действий: <b style="color:white;">{logs_count}</b>
            </div>
        </div>
        '''
        return mark_safe(html)

    deal_header.short_description = 'Сделка'

    def deal_history(self, obj):
        logs = self.get_all_logs_for_deal(obj)

        html = '<div style="display:flex;flex-direction:column;gap:12px;">'

        for log in logs:
            html += self.render_log_card(log)

        html += '</div>'
        return mark_safe(html)

    def render_log_card(self, log):
        colors = {
            'created': '#2ecc71',
            'fulfilled': '#3498db',
            'updated': '#f1c40f',
            'deleted': '#e74c3c',
            'rollback': '#8a4fb8',
            'Создание': '#2ecc71',
            'Дополнение': '#3498db',
            'Редактирование': '#f1c40f',
            'Удаление': '#e74c3c',
            'Откат склада': '#8a4fb8',
        }

        color = colors.get(log.action) or colors.get(log.get_action_display(), '#4f7c8a')
        changes_html = self.render_changes(log)

        return f'''
        <div style="background:#1e1e1e;border-left:6px solid {color};border-radius:12px;padding:14px;">
            <div style="display:flex;justify-content:space-between;">
                <div>
                    <span style="color:{color};font-weight:800;">{log.get_action_display()}</span>
                    <div style="margin-top:5px;">{log.description}</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#aaa;font-size:12px;">
                        {log.created_at.strftime('%d.%m.%Y %H:%M:%S')}
                    </div>
                    <div style="color:#ffffff;font-weight:700;font-size:14px;margin-top:2px;">
                        👤 {log.user or '—'}
                    </div>
                </div>
            </div>

            <div style="margin-top:10px;">
                {changes_html}
            </div>
        </div>
        '''

    def render_changes(self, log):
        before = log.before_data or {}
        after = log.after_data or {}

        before_items = before.get('items', [])
        after_items = after.get('items', [])

        max_len = max(len(before_items), len(after_items))

        item_fields = {
            'requested_quantity': 'Заказано',
            'fulfilled_quantity': 'Передано',
            'quantity_after': 'Остаток на складе',
        }

        grouped = {}

        for i in range(max_len):
            old_item = before_items[i] if i < len(before_items) else None
            new_item = after_items[i] if i < len(after_items) else None

            if not old_item or not new_item:
                continue

            product = new_item.get('product') or old_item.get('product') or 'Товар'

            if product not in grouped:
                grouped[product] = []

            for key, label in item_fields.items():
                old = old_item.get(key)
                new = new_item.get(key)

                if old != new:
                    grouped[product].append((label, old, new))

        grouped = {
            product: changes
            for product, changes in grouped.items()
            if changes
        }

        if not grouped:
            return '<div style="color:#aaa;">Нет изменений</div>'

        html = '<div style="display:flex;flex-direction:column;gap:10px;">'

        for product, changes in grouped.items():
            html += f'''
            <div style="background:#151515;border:1px solid #2a2a2a;border-radius:10px;padding:10px;">
                <div style="font-weight:800;margin-bottom:8px;color:#fff;">
                    📦 {product}
                </div>

                <table style="width:100%;border-collapse:collapse;">
            '''

            for label, old, new in changes:
                html += f'''
                <tr>
                    <td style="padding:6px;color:#ddd;width:34%;">{label}</td>
                    <td style="padding:6px;width:33%;">
                        <span style="color:#aaa;">было:</span>
                        <span style="color:#e74c3c;font-weight:600;"> {old}</span>
                    </td>
                    <td style="padding:6px;width:33%;">
                        <span style="color:#aaa;">стало:</span>
                        <span style="color:#2ecc71;font-weight:700;"> {new}</span>
                    </td>
                </tr>
                '''

            html += '''
                </table>
            </div>
            '''

        html += '</div>'
        return html
