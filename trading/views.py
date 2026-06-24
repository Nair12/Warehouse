from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction, models
from django.http import JsonResponse, HttpResponseForbidden
from django.forms import formset_factory
from django.core.paginator import Paginator
from django.utils.translation import gettext as _

from .models import Trading, TradingItem, TradingAuditLog, TradingComment
from .forms import TradingForm, TradingItemForm, AttachmentFormSet, TradingCommentForm
from products.models import Inventory
from users.decorators import role_required

TradingItemFormSet = formset_factory(TradingItemForm, extra=1)


def make_trading_snapshot(trading):
    items_data = []

    for item in trading.items.select_related('product', 'warehouse').all():
        items_data.append({
            'product': str(item.product),
            'warehouse': str(item.warehouse),
            'requested_quantity': item.requested_quantity,
            'fulfilled_quantity': item.fulfilled_quantity,
            'quantity': item.quantity,
            'quantity_before': item.quantity_before,
            'quantity_after': item.quantity_after,
        })

    return {
        'id': trading.id,
        'name': trading.name,
        'trade_type': trading.trade_type,
        'status': trading.status,
        'comment': trading.comment,
        'items': items_data,
    }


def create_trading_audit_log(trading, user, action, description, before_data=None, after_data=None):
    TradingAuditLog.objects.create(
        trading=trading,
        trading_id_snapshot=trading.id if trading else None,
        user=user,
        action=action,
        description=description,
        before_data=before_data or {},
        after_data=after_data or {},
    )


def manager_24h_limit_expired(user, trading):
    return (
        getattr(user, 'role', None) == 'manager'
        and not trading.can_be_modified
    )


@role_required(['admin', 'manager', "senior_manager"])
def trading_list(request):
    current_type = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'newest')

    tradings = Trading.objects.select_related(
        'product', 'warehouse', 'user'
    ).prefetch_related(
        'items', 'items__product', 'items__warehouse'
    ).filter(status=Trading.Status.COMPLETED)

    if current_type in ['purchase', 'sell']:
        tradings = tradings.filter(trade_type=current_type)

    if date_from:
        tradings = tradings.filter(created_at__date__gte=date_from)

    if date_to:
        tradings = tradings.filter(created_at__date__lte=date_to)

    if sort_by == 'oldest':
        tradings = tradings.order_by('created_at', 'id')
    elif sort_by == 'name_az':
        tradings = tradings.order_by('name', 'id')
    elif sort_by == 'name_za':
        tradings = tradings.order_by('-name', '-id')
    else:
        sort_by = 'newest'
        tradings = tradings.order_by('-created_at', '-id')

    tradings = list(tradings)

    if search_query:
        search_text = search_query.lower()
        filtered_tradings = []

        for trading in tradings:
            searchable_parts = [
                trading.name or '',
                trading.comment or '',
                trading.product.name if trading.product else '',
                trading.warehouse.city if trading.warehouse else '',
            ]

            for item in trading.items.all():
                searchable_parts.append(item.product.name if item.product else '')
                searchable_parts.append(item.warehouse.city if item.warehouse else '')

            searchable_text = ' '.join(searchable_parts).lower()

            if search_text in searchable_text:
                filtered_tradings.append(trading)

        tradings = filtered_tradings

    for trading in tradings:
        total_requested = 0
        total_fulfilled = 0

        for item in trading.items.all():
            total_requested += item.requested_quantity
            total_fulfilled += item.fulfilled_quantity

        trading.total_requested = total_requested
        trading.total_fulfilled = total_fulfilled

        grouped_items = {}

        for item in trading.items.all():
            key = (item.product_id, item.warehouse_id)

            if key not in grouped_items:
                grouped_items[key] = {
                    'product': item.product,
                    'warehouse': item.warehouse,
                    'requested_quantity': 0,
                    'fulfilled_quantity': 0,
                }

            grouped_items[key]['requested_quantity'] += item.requested_quantity
            grouped_items[key]['fulfilled_quantity'] += item.fulfilled_quantity

        trading.grouped_items = list(grouped_items.values())
        trading.is_in_progress = True

    paginator = Paginator(tradings, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, 'trading/trading_list.html', {
        'tradings': page_obj,
        'page_obj': page_obj,
        'current_type': current_type,
        'page_title': _('История сделок'),
        'is_orders_page': False,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'sort_by': sort_by,
        'query_string': query_params.urlencode(),
    })




@role_required(['admin', 'manager', "senior_manager"])
def orders_list(request):
    current_type = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'newest')

    tradings = Trading.objects.select_related(
        'product', 'warehouse', 'user'
    ).prefetch_related(
        'items', 'items__product', 'items__warehouse'
    ).filter(status=Trading.Status.PENDING)

    if current_type in ['purchase', 'sell']:
        tradings = tradings.filter(trade_type=current_type)

    if date_from:
        tradings = tradings.filter(created_at__date__gte=date_from)

    if date_to:
        tradings = tradings.filter(created_at__date__lte=date_to)

    if sort_by == 'oldest':
        tradings = tradings.order_by('created_at', 'id')
    elif sort_by == 'name_az':
        tradings = tradings.order_by('name', 'id')
    elif sort_by == 'name_za':
        tradings = tradings.order_by('-name', '-id')
    else:
        sort_by = 'newest'
        tradings = tradings.order_by('-created_at', '-id')

    tradings = list(tradings)

    if search_query:
        search_text = search_query.lower()
        filtered_tradings = []

        for trading in tradings:
            searchable_parts = [
                trading.name or '',
                trading.comment or '',
                trading.product.name if trading.product else '',
                trading.warehouse.city if trading.warehouse else '',
            ]

            for item in trading.items.all():
                searchable_parts.append(item.product.name if item.product else '')
                searchable_parts.append(item.warehouse.city if item.warehouse else '')

            searchable_text = ' '.join(searchable_parts).lower()

            if search_text in searchable_text:
                filtered_tradings.append(trading)

        tradings = filtered_tradings

    for trading in tradings:
        total_requested = 0
        total_fulfilled = 0

        for item in trading.items.all():
            total_requested += item.requested_quantity
            total_fulfilled += item.fulfilled_quantity

        trading.total_requested = total_requested
        trading.total_fulfilled = total_fulfilled

        grouped_items = {}

        for item in trading.items.all():
            key = (item.product_id, item.warehouse_id)

            if key not in grouped_items:
                grouped_items[key] = {
                    'product': item.product,
                    'warehouse': item.warehouse,
                    'requested_quantity': 0,
                    'fulfilled_quantity': 0,
                }

            grouped_items[key]['requested_quantity'] += item.requested_quantity
            grouped_items[key]['fulfilled_quantity'] += item.fulfilled_quantity

        trading.grouped_items = list(grouped_items.values())
        trading.is_in_progress = True

    paginator = Paginator(tradings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, 'trading/trading_list.html', {
        'tradings': page_obj,
        'page_obj': page_obj,
        'current_type': current_type,
        'page_title': _('Заказы'),
        'is_orders_page': True,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'sort_by': sort_by,
        'query_string': query_params.urlencode(),
    })




@role_required(['admin'])
def admin_trading_history(request):
    tradings = Trading.objects.select_related(
        'product', 'warehouse', 'user'
    ).prefetch_related(
        'items', 'items__product', 'items__warehouse'
    ).all()

    return render(request, 'trading/admin_trading_history.html', {
        'tradings': tradings
    })


@role_required(['admin', 'manager', "senior_manager"])
def trading_detail(request, pk):
    trading = get_object_or_404(
        Trading.objects.select_related(
            'product', 'warehouse', 'user'
        ).prefetch_related(
            'items',
            'items__product',
            'items__warehouse',
            'attachments',
        ),
        pk=pk
    )

    items = trading.items.select_related(
        'product',
        'warehouse',
    ).order_by(
        'product__name',
        'warehouse__city',
        'created_at',
        'id',
    )

    grouped_items_dict = {}

    for item in items:
        key = (item.product_id, item.warehouse_id)

        if key not in grouped_items_dict:
            grouped_items_dict[key] = {
                'product': item.product,
                'warehouse': item.warehouse,
                'requested_quantity': 0,
                'fulfilled_quantity': 0,
            }

        grouped_items_dict[key]['requested_quantity'] += item.requested_quantity
        grouped_items_dict[key]['fulfilled_quantity'] += item.fulfilled_quantity

    for grouped_item in grouped_items_dict.values():
        grouped_item['remaining_quantity'] = max(
            grouped_item['requested_quantity'] - grouped_item['fulfilled_quantity'],
            0
        )

        if grouped_item['fulfilled_quantity'] == 0:
            grouped_item['fulfillment_status_display'] = _('Не выполнено')
        elif grouped_item['remaining_quantity'] == 0:
            grouped_item['fulfillment_status_display'] = _('Выполнено')
        else:
            grouped_item['fulfillment_status_display'] = _('В процессе')

    grouped_items = list(grouped_items_dict.values())

    has_remaining = any(
        item['remaining_quantity'] > 0
        for item in grouped_items
    )

    # 🔥 ИСТОРИЯ ДООТПРАВОК / ДОПОЛНЕНИЙ
    fulfillment_logs = trading.audit_logs.select_related("user").filter(
        action=TradingAuditLog.Action.FULFILLED
    )

    for log in fulfillment_logs:
        display_items = []

        before_items = {}
        after_items = {}

        for item_data in log.before_data.get("items", []):
            key = (
                item_data.get("product"),
                item_data.get("warehouse"),
            )
            before_items[key] = item_data

        for item_data in log.after_data.get("items", []):
            key = (
                item_data.get("product"),
                item_data.get("warehouse"),
            )
            after_items[key] = item_data

        for key, after_item in after_items.items():
            before_item = before_items.get(key, {})

            fulfilled_before = before_item.get("fulfilled_quantity", 0) or 0
            fulfilled_after = after_item.get("fulfilled_quantity", 0) or 0
            requested_quantity = after_item.get("requested_quantity", 0) or 0
            added_quantity = fulfilled_after - fulfilled_before

            if added_quantity <= 0:
                continue

            display_items.append({
                "product": after_item.get("product") or "—",
                "warehouse": after_item.get("warehouse") or "—",
                "added_quantity": added_quantity,
                "fulfilled_before": fulfilled_before,
                "fulfilled_after": fulfilled_after,
                "remaining_after": max(requested_quantity - fulfilled_after, 0),
            })

        log.display_items = display_items

    # 🔥 КОММЕНТАРИИ
    comments = trading.comments.select_related("user").all()

    if request.method == "POST":
        comment_form = TradingCommentForm(request.POST)

        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.trading = trading
            comment.user = request.user
            comment.save()

            messages.success(request, _("Комментарий добавлен."))
            return redirect("trading_detail", pk=trading.pk)
    else:
        comment_form = TradingCommentForm()

    return render(request, 'trading/trading_detail.html', {
        'trading': trading,
        'grouped_items': grouped_items,
        'has_remaining': has_remaining,
        'fulfillment_logs': fulfillment_logs,
        'comments': comments,
        'comment_form': comment_form,
    })


@role_required(['admin', 'manager', "senior_manager"])
def trading_comment_delete(request, pk, comment_id):
    trading = get_object_or_404(Trading, pk=pk)

    comment = get_object_or_404(
        TradingComment,
        pk=comment_id,
        trading=trading
    )

    if comment.user != request.user:
        messages.error(request, _("Можно удалить только свой комментарий."))
        return redirect("trading_detail", pk=trading.pk)

    if request.method != "POST":
        return HttpResponseForbidden(_("Удаление комментария доступно только через POST-запрос."))

    comment.delete()
    messages.success(request, _("Комментарий удален."))
    return redirect("trading_detail", pk=trading.pk)


@role_required(['admin', 'manager', "senior_manager"])
def trading_create(request):
    if request.method == 'POST':
        form = TradingForm(request.POST)
        item_formset = TradingItemFormSet(request.POST, prefix='items')
        formset = AttachmentFormSet(request.POST, request.FILES)

        if form.is_valid() and item_formset.is_valid() and formset.is_valid():
            valid_items = []

            for item_form in item_formset:
                if not item_form.cleaned_data:
                    continue

                product = item_form.cleaned_data.get('product')
                warehouse = item_form.cleaned_data.get('warehouse')
                requested_quantity = item_form.cleaned_data.get('requested_quantity')
                fulfilled_quantity = item_form.cleaned_data.get('fulfilled_quantity') or 0

                if product and warehouse and requested_quantity:
                    valid_items.append({
                        'product': product,
                        'warehouse': warehouse,
                        'requested_quantity': requested_quantity,
                        'fulfilled_quantity': fulfilled_quantity,
                    })

            if not valid_items:
                form.add_error(None, _('Добавьте хотя бы одну позицию сделки.'))
                return render(request, 'trading/trading_add.html', {
                    'form': form,
                    'item_formset': item_formset,
                    'formset': formset,
                })

            with transaction.atomic():
                trading = form.save(commit=False)
                trading.user = request.user

                first_item = valid_items[0]

                first_inventory, _ = Inventory.objects.get_or_create(
                    product=first_item['product'],
                    warehouse=first_item['warehouse'],
                    defaults={'quantity': 0},
                )

                first_quantity_before = first_inventory.quantity
                first_fulfilled_quantity = first_item['fulfilled_quantity']

                if trading.trade_type == Trading.TradeType.PURCHASE:
                    first_quantity_after = first_quantity_before + first_fulfilled_quantity
                else:
                    first_fulfilled_quantity = min(
                        first_fulfilled_quantity,
                        first_item['requested_quantity'],
                        first_inventory.quantity
                    )
                    first_quantity_after = first_quantity_before - first_fulfilled_quantity

                trading.product = first_item['product']
                trading.warehouse = first_item['warehouse']
                trading.quantity = first_item['requested_quantity']
                trading.quantity_before = first_quantity_before
                trading.quantity_after = first_quantity_after
                trading.status = Trading.Status.PENDING
                trading.save()

                total_requested = 0
                total_fulfilled = 0

                for item in valid_items:
                    product = item['product']
                    warehouse = item['warehouse']
                    requested_quantity = item['requested_quantity']
                    fulfilled_quantity = item['fulfilled_quantity']

                    inventory, _ = Inventory.objects.get_or_create(
                        product=product,
                        warehouse=warehouse,
                        defaults={'quantity': 0},
                    )

                    quantity_before = inventory.quantity

                    if trading.trade_type == Trading.TradeType.PURCHASE:
                        fulfilled_quantity = min(fulfilled_quantity, requested_quantity)
                        inventory.quantity += fulfilled_quantity

                    elif trading.trade_type == Trading.TradeType.SELL:
                        fulfilled_quantity = min(
                            fulfilled_quantity,
                            requested_quantity,
                            inventory.quantity
                        )
                        inventory.quantity -= fulfilled_quantity

                    else:
                        fulfilled_quantity = 0

                    quantity_after = inventory.quantity
                    inventory.save()

                    total_requested += requested_quantity
                    total_fulfilled += fulfilled_quantity

                    TradingItem.objects.create(
                        trading=trading,
                        product=product,
                        warehouse=warehouse,
                        quantity=fulfilled_quantity,
                        requested_quantity=requested_quantity,
                        fulfilled_quantity=fulfilled_quantity,
                        quantity_before=quantity_before,
                        quantity_after=quantity_after,
                    )

                trading.status = (
                    Trading.Status.COMPLETED
                    if total_fulfilled >= total_requested
                    else Trading.Status.PENDING
                )
                trading.save()

                attachments = formset.save(commit=False)
                for attachment in attachments:
                    attachment.trade = trading
                    attachment.save()

                create_trading_audit_log(
                    trading=trading,
                    user=request.user,
                    action=TradingAuditLog.Action.CREATED,
                    description=_('Создана сделка #%(id)s') % {'id': trading.id},
                    before_data={},
                    after_data=make_trading_snapshot(trading),
                )

                return redirect('trading_list')

    else:
        form = TradingForm()
        item_formset = TradingItemFormSet(prefix='items')
        formset = AttachmentFormSet()

    return render(request, 'trading/trading_add.html', {
        'form': form,
        'item_formset': item_formset,
        'formset': formset,
    })


@role_required(['admin', 'manager', "senior_manager"])
def trading_update(request, pk):
    trading = get_object_or_404(Trading, pk=pk)

    if not trading.can_be_edited:
        messages.error(request, _("Можно редактировать только незавершенные сделки."))
        return redirect('trading_detail', pk=trading.pk)

    TradingItemEditFormSet = formset_factory(
        TradingItemForm,
        extra=0,
        can_delete=True
    )

    items = trading.items.select_related(
        'product',
        'warehouse'
    ).order_by('id')

    initial_items = [
        {
            'product': item.product,
            'warehouse': item.warehouse,
            'requested_quantity': item.requested_quantity,
            'fulfilled_quantity': item.fulfilled_quantity,
        }
        for item in items
    ]

    if request.method == 'POST':
        form = TradingForm(request.POST, instance=trading)
        item_formset = TradingItemEditFormSet(request.POST, prefix='items')
        formset = AttachmentFormSet(request.POST, request.FILES)

        if form.is_valid() and item_formset.is_valid() and formset.is_valid():
            with transaction.atomic():
                trading = Trading.objects.select_for_update().get(pk=pk)
                before_snapshot = make_trading_snapshot(trading)

                form = TradingForm(request.POST, instance=trading)
                form.save()

                attachments = formset.save(commit=False)
                for attachment in attachments:
                    attachment.trade = trading
                    attachment.save()

                locked_items = list(
                    trading.items.select_related(
                        'product',
                        'warehouse'
                    ).select_for_update().order_by('id')
                )

                for index, item_form in enumerate(item_formset):
                    cleaned_data = item_form.cleaned_data

                    if not cleaned_data:
                        continue

                    item = locked_items[index] if index < len(locked_items) else None

                    if item is None:
                        product = cleaned_data.get('product')
                        warehouse = cleaned_data.get('warehouse')
                        requested_quantity = cleaned_data.get('requested_quantity')
                        fulfilled_quantity = cleaned_data.get('fulfilled_quantity') or 0

                        if cleaned_data.get('DELETE'):
                            continue

                        if product and warehouse and requested_quantity:
                            if fulfilled_quantity > requested_quantity:
                                messages.error(
                                    request,
                                    _('Выполнено не может быть больше заказано: %(product)s') % {'product': product}
                                )
                                return redirect('trading_update', pk=trading.pk)

                            inventory, _ = Inventory.objects.select_for_update().get_or_create(
                                product=product,
                                warehouse=warehouse,
                                defaults={'quantity': 0},
                            )

                            quantity_before = inventory.quantity

                            if trading.trade_type == Trading.TradeType.PURCHASE:
                                inventory.quantity += fulfilled_quantity

                            elif trading.trade_type == Trading.TradeType.SELL:
                                if fulfilled_quantity > inventory.quantity:
                                    messages.error(
                                        request,
                                        f'Недостаточно товара на складе для {product}. '
                                        f'Доступно: {inventory.quantity}, нужно: {fulfilled_quantity}.'
                                    )
                                    return redirect('trading_update', pk=trading.pk)

                                inventory.quantity -= fulfilled_quantity

                            inventory.save()
                            quantity_after = inventory.quantity

                            TradingItem.objects.create(
                                trading=trading,
                                product=product,
                                warehouse=warehouse,
                                quantity=fulfilled_quantity,
                                requested_quantity=requested_quantity,
                                fulfilled_quantity=fulfilled_quantity,
                                quantity_before=quantity_before,
                                quantity_after=quantity_after,
                            )

                        continue

                    # Существующие позиции сделки нельзя менять через редактирование.
                    # Это защищает складские остатки, историю fulfill и аудит:
                    # товар, склад, заказано, выполнено и удаление старой позиции игнорируются.
                    # Если нужно изменить объём или добавить тот же товар ещё раз —
                    # добавляем новую позицию отдельной строкой.
                    continue

                all_done = not TradingItem.objects.filter(
                    trading=trading,
                    fulfilled_quantity__lt=models.F('requested_quantity')
                ).exists()

                trading.status = (
                    Trading.Status.COMPLETED if all_done else Trading.Status.PENDING
                )
                trading.save(update_fields=['status'])

                create_trading_audit_log(
                    trading=trading,
                    user=request.user,
                    action=TradingAuditLog.Action.UPDATED,
                    description=_('Отредактирована сделка #%(id)s') % {'id': trading.id},
                    before_data=before_snapshot,
                    after_data=make_trading_snapshot(trading),
                )

            from django.contrib.messages import get_messages
            storage = get_messages(request)
            for _ in storage:
                pass

            messages.success(request, _('Сделка обновлена.'))
            return redirect('trading_detail', pk=trading.pk)

    else:
        form = TradingForm(instance=trading)
        item_formset = TradingItemEditFormSet(
            initial=initial_items,
            prefix='items'
        )
        formset = AttachmentFormSet()

    return render(request, 'trading/trading_add.html', {
        'form': form,
        'item_formset': item_formset,
        'formset': formset,
        'trading': trading,
    })


@role_required(['admin', 'manager', "senior_manager"])
def trading_delete(request, pk):
    trading = get_object_or_404(
        Trading.objects.prefetch_related(
            'items',
            'items__product',
            'items__warehouse',
        ),
        pk=pk
    )

    if manager_24h_limit_expired(request.user, trading):
        messages.error(request, _("Менеджер может удалить сделку только в течение 24 часов после создания."))
        return redirect('trading_detail', pk=trading.pk)

    if request.method == 'POST':
        with transaction.atomic():
            trading = Trading.objects.select_for_update().get(pk=pk)
            before_snapshot = make_trading_snapshot(trading)

            items = trading.items.select_related(
                'product',
                'warehouse'
            ).select_for_update()

            for item in items:
                rollback_quantity = item.fulfilled_quantity

                if rollback_quantity <= 0:
                    continue

                inventory, _ = Inventory.objects.select_for_update().get_or_create(
                    product=item.product,
                    warehouse=item.warehouse,
                    defaults={'quantity': 0},
                )

                if trading.trade_type == Trading.TradeType.SELL:
                    inventory.quantity += rollback_quantity

                elif trading.trade_type == Trading.TradeType.PURCHASE:
                    if rollback_quantity > inventory.quantity:
                        messages.error(
                            request,
                            _('Нельзя удалить сделку: на складе недостаточно товара для отката %(product)s. На складе: %(available)s, нужно откатить: %(needed)s.') % {
                                'product': item.product,
                                'available': inventory.quantity,
                                'needed': rollback_quantity,
                            }
                        )
                        return redirect('trading_detail', pk=trading.pk)

                    inventory.quantity -= rollback_quantity

                inventory.save()

            before_snapshot = make_trading_snapshot(trading)

            create_trading_audit_log(
                trading=trading,
                user=request.user,
                action=TradingAuditLog.Action.DELETED,
                description=_('Удалена сделка #%(id)s, склад откатан') % {'id': trading.id},
                before_data=before_snapshot,
                after_data={'deleted': True},
            )

            trading.delete()

        messages.success(request, _('Сделка удалена, склад откатан.'))
        return redirect('trading_list')

    return render(request, 'trading/trading_confirm_delete.html', {
        'trading': trading
    })


def get_stock(request):
    product_id = request.GET.get("product")
    warehouse_id = request.GET.get("warehouse")

    if not product_id or not warehouse_id:
        return JsonResponse({"quantity": 0})

    inventory = Inventory.objects.filter(
        product_id=product_id,
        warehouse_id=warehouse_id
    ).first()

    return JsonResponse({
        "quantity": inventory.quantity if inventory else 0,
        "unit": inventory.product.get_unit_display() if inventory else ""
    })


@role_required(['admin', 'manager', 'senior_manager'])
def trading_fulfill(request, pk):
    trading = get_object_or_404(
        Trading.objects.prefetch_related(
            'items',
            'items__product',
            'items__warehouse',
        ),
        pk=pk
    )

    if request.method == 'POST':
        requested_additions = {}

        for item in trading.items.all():
            raw_quantity = request.POST.get(f'quantity_{item.id}', '').strip()

            if not raw_quantity:
                continue

            try:
                quantity_to_add = int(raw_quantity)
            except ValueError:
                quantity_to_add = 0

            if quantity_to_add > 0:
                requested_additions[item.id] = quantity_to_add

        if not requested_additions:
            messages.error(request, _('Введите количество хотя бы для одной позиции.'))
            return redirect('trading_fulfill', pk=pk)

        was_fulfilled = False
        fulfillment_details = []

        with transaction.atomic():
            trading = Trading.objects.select_for_update().get(pk=pk)
            before_snapshot = make_trading_snapshot(trading)

            items = trading.items.select_related(
                'product',
                'warehouse'
            ).select_for_update().order_by('id')

            for item in items:
                quantity_to_add = requested_additions.get(item.id, 0)

                if quantity_to_add <= 0:
                    continue

                remaining = item.requested_quantity - item.fulfilled_quantity

                if remaining <= 0:
                    continue

                add_quantity = min(quantity_to_add, remaining)

                inventory, _ = Inventory.objects.select_for_update().get_or_create(
                    product=item.product,
                    warehouse=item.warehouse,
                    defaults={'quantity': 0},
                )

                quantity_before = inventory.quantity

                if trading.trade_type == Trading.TradeType.SELL:
                    if add_quantity > inventory.quantity:
                        messages.error(
                            request,
                            _('Недостаточно товара на складе для %(product)s. Доступно: %(available)s, нужно: %(needed)s.') % {
                                'product': item.product,
                                'available': inventory.quantity,
                                'needed': add_quantity,
                            }
                        )
                        return redirect('trading_fulfill', pk=pk)

                    inventory.quantity -= add_quantity

                elif trading.trade_type == Trading.TradeType.PURCHASE:
                    inventory.quantity += add_quantity

                inventory.save()

                fulfilled_before = item.fulfilled_quantity

                item.fulfilled_quantity += add_quantity
                item.quantity += add_quantity
                item.quantity_before = quantity_before
                item.quantity_after = inventory.quantity
                item.save()

                fulfilled_after = item.fulfilled_quantity
                remaining_after = max(item.requested_quantity - item.fulfilled_quantity, 0)

                fulfillment_details.append(
                    {
                        'product': str(item.product),
                        'warehouse': str(item.warehouse),
                        'unit': item.product.get_unit_display() if item.product else '',
                        'added_quantity': add_quantity,
                        'fulfilled_before': fulfilled_before,
                        'fulfilled_after': fulfilled_after,
                        'remaining_after': remaining_after,
                        'stock_before': quantity_before,
                        'stock_after': inventory.quantity,
                    }
                )

                was_fulfilled = True

        all_done = not TradingItem.objects.filter(
            trading=trading,
            fulfilled_quantity__lt=models.F('requested_quantity')
        ).exists()

        if was_fulfilled:
            detail_lines = [_('Дополнена сделка #%(id)s') % {'id': trading.id}]

            for detail in fulfillment_details:
                unit = detail.get('unit') or ''
                unit_suffix = f" {unit}" if unit else ""

                detail_lines.extend([
                    '',
                    _('Товар: %(product)s') % {'product': detail['product']},
                    _('Склад: %(warehouse)s') % {'warehouse': detail['warehouse']},
                    _('Доотправлено: %(quantity)s%(unit)s') % {
                        'quantity': detail['added_quantity'],
                        'unit': unit_suffix,
                    },
                    _('Выполнено: %(before)s → %(after)s%(unit)s') % {
                        'before': detail['fulfilled_before'],
                        'after': detail['fulfilled_after'],
                        'unit': unit_suffix,
                    },
                    _('Осталось: %(quantity)s%(unit)s') % {
                        'quantity': detail['remaining_after'],
                        'unit': unit_suffix,
                    },
                    _('Остаток на складе: %(before)s → %(after)s%(unit)s') % {
                        'before': detail['stock_before'],
                        'after': detail['stock_after'],
                        'unit': unit_suffix,
                    },
                ])

            create_trading_audit_log(
                trading=trading,
                user=request.user,
                action=TradingAuditLog.Action.FULFILLED,
                description='\n'.join(detail_lines),
                before_data=before_snapshot,
                after_data=make_trading_snapshot(trading),
            )

        if all_done:
            trading.status = Trading.Status.COMPLETED
            trading.save()
            messages.success(request, _('Заказ полностью выполнен.'))
        elif was_fulfilled:
            trading.status = Trading.Status.PENDING
            trading.save()
            messages.success(request, _('Заказ частично дополнен.'))
        else:
            messages.warning(request, _('Не удалось дополнить заказ. Проверьте остатки на складе.'))

        return redirect('trading_detail', pk=pk)

    fulfill_items = []

    for item in trading.items.all():
        remaining = item.requested_quantity - item.fulfilled_quantity

        fulfill_items.append({
            'id': item.id,
            'product': item.product,
            'warehouse': item.warehouse,
            'requested_quantity': item.requested_quantity,
            'fulfilled_quantity': item.fulfilled_quantity,
            'remaining_quantity': remaining,
        })

    return render(request, 'trading/trading_fulfill.html', {
        'trading': trading,
        'fulfill_items': fulfill_items
    })
