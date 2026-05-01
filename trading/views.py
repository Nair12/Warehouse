from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction, models
from django.http import JsonResponse, HttpResponseForbidden
from django.forms import formset_factory

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

    tradings = Trading.objects.select_related(
        'product', 'warehouse', 'user'
    ).prefetch_related(
        'items', 'items__product', 'items__warehouse'
    ).filter(status=Trading.Status.COMPLETED)

    if current_type in ['purchase', 'sell']:
        tradings = tradings.filter(trade_type=current_type)

    tradings = list(tradings)

    for trading in tradings:
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
        trading.is_in_progress = False

    return render(request, 'trading/trading_list.html', {
        'tradings': tradings,
        'current_type': current_type,
        'page_title': 'История сделок',
        'is_orders_page': False,
    })


@role_required(['admin', 'manager', "senior_manager"])
def orders_list(request):
    current_type = request.GET.get('type')

    tradings = Trading.objects.select_related(
        'product', 'warehouse', 'user'
    ).prefetch_related(
        'items', 'items__product', 'items__warehouse'
    ).filter(status=Trading.Status.PENDING)

    if current_type in ['purchase', 'sell']:
        tradings = tradings.filter(trade_type=current_type)

    tradings = list(tradings)

    for trading in tradings:
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

    return render(request, 'trading/trading_list.html', {
        'tradings': tradings,
        'current_type': current_type,
        'page_title': 'Заказы',
        'is_orders_page': True,
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
            grouped_item['fulfillment_status_display'] = 'Не выполнено'
        elif grouped_item['remaining_quantity'] == 0:
            grouped_item['fulfillment_status_display'] = 'Выполнено'
        else:
            grouped_item['fulfillment_status_display'] = 'В процессе'

    grouped_items = list(grouped_items_dict.values())

    has_remaining = any(
        item['remaining_quantity'] > 0
        for item in grouped_items
    )

    # 🔥 КОММЕНТАРИИ
    comments = trading.comments.select_related("user").all()

    if request.method == "POST":
        comment_form = TradingCommentForm(request.POST)

        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.trading = trading
            comment.user = request.user
            comment.save()

            messages.success(request, "Комментарий добавлен.")
            return redirect("trading_detail", pk=trading.pk)
    else:
        comment_form = TradingCommentForm()

    return render(request, 'trading/trading_detail.html', {
        'trading': trading,
        'grouped_items': grouped_items,
        'has_remaining': has_remaining,
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
        messages.error(request, "Можно удалить только свой комментарий.")
        return redirect("trading_detail", pk=trading.pk)

    if request.method != "POST":
        return HttpResponseForbidden("Удаление комментария доступно только через POST-запрос.")

    comment.delete()
    messages.success(request, "Комментарий удален.")
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
                form.add_error(None, 'Добавьте хотя бы одну позицию сделки.')
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
                    description=f'Создана сделка #{trading.id}',
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
        messages.error(request, "Можно редактировать только незавершенные сделки.")
        return redirect('trading_detail', pk=trading.pk)

    if manager_24h_limit_expired(request.user, trading):
        messages.error(request, "Менеджер может редактировать сделку только в течение 24 часов после создания.")
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

        if form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                trading = Trading.objects.select_for_update().get(pk=pk)
                before_snapshot = make_trading_snapshot(trading)

                form = TradingForm(request.POST, instance=trading)
                form.save()

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
                                    f'Выполнено не может быть больше заказано: {product}'
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

                    if cleaned_data.get('DELETE'):
                        if item.fulfilled_quantity > 0:
                            messages.error(
                                request,
                                f'Нельзя удалить позицию, по которой уже есть выполнение: {item.product}'
                            )
                            return redirect('trading_update', pk=trading.pk)

                        item.delete()
                        continue

                    requested_quantity = cleaned_data.get('requested_quantity')
                    fulfilled_quantity = cleaned_data.get('fulfilled_quantity')

                    if requested_quantity is None:
                        continue

                    if fulfilled_quantity is None:
                        fulfilled_quantity = item.fulfilled_quantity

                    if fulfilled_quantity > requested_quantity:
                        messages.error(
                            request,
                            f'Выполнено не может быть больше заказано: {item.product}'
                        )
                        return redirect('trading_update', pk=trading.pk)

                    quantity_delta = fulfilled_quantity - item.fulfilled_quantity

                    inventory, _ = Inventory.objects.select_for_update().get_or_create(
                        product=item.product,
                        warehouse=item.warehouse,
                        defaults={'quantity': 0},
                    )

                    quantity_before = inventory.quantity

                    if trading.trade_type == Trading.TradeType.PURCHASE:
                        inventory.quantity += quantity_delta

                    elif trading.trade_type == Trading.TradeType.SELL:
                        if quantity_delta > inventory.quantity:
                            messages.error(
                                request,
                                f'Недостаточно товара на складе для {item.product}. '
                                f'Доступно: {inventory.quantity}, нужно ещё: {quantity_delta}.'
                            )
                            return redirect('trading_update', pk=trading.pk)

                        inventory.quantity -= quantity_delta

                    inventory.save()

                    item.requested_quantity = requested_quantity
                    item.fulfilled_quantity = fulfilled_quantity
                    item.quantity = fulfilled_quantity
                    item.quantity_before = quantity_before
                    item.quantity_after = inventory.quantity
                    item.save(update_fields=[
                        'requested_quantity',
                        'fulfilled_quantity',
                        'quantity',
                        'quantity_before',
                        'quantity_after',
                    ])

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
                    description=f'Отредактирована сделка #{trading.id}',
                    before_data=before_snapshot,
                    after_data=make_trading_snapshot(trading),
                )

            from django.contrib.messages import get_messages
            storage = get_messages(request)
            for _ in storage:
                pass

            messages.success(request, 'Сделка обновлена.')
            return redirect('trading_detail', pk=trading.pk)

    else:
        form = TradingForm(instance=trading)
        item_formset = TradingItemEditFormSet(
            initial=initial_items,
            prefix='items'
        )

    return render(request, 'trading/trading_add.html', {
        'form': form,
        'item_formset': item_formset,
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
        messages.error(request, "Менеджер может удалить сделку только в течение 24 часов после создания.")
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
                            f'Нельзя удалить сделку: на складе недостаточно товара для отката {item.product}. '
                            f'На складе: {inventory.quantity}, нужно откатить: {rollback_quantity}.'
                        )
                        return redirect('trading_detail', pk=trading.pk)

                    inventory.quantity -= rollback_quantity

                inventory.save()

            before_snapshot = make_trading_snapshot(trading)

            create_trading_audit_log(
                trading=trading,
                user=request.user,
                action=TradingAuditLog.Action.DELETED,
                description=f'Удалена сделка #{trading.id}, склад откатан',
                before_data=before_snapshot,
                after_data={'deleted': True},
            )

            trading.delete()

        messages.success(request, 'Сделка удалена, склад откатан.')
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
        try:
            quantity_to_add = int(request.POST.get('quantity', 0))
        except ValueError:
            quantity_to_add = 0

        if quantity_to_add <= 0:
            messages.error(request, 'Введите корректное количество.')
            return redirect('trading_fulfill', pk=pk)

        was_fulfilled = False

        with transaction.atomic():
            trading = Trading.objects.select_for_update().get(pk=pk)
            before_snapshot = make_trading_snapshot(trading)

            items = trading.items.select_related(
                'product',
                'warehouse'
            ).select_for_update()

            for item in items:
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
                    add_quantity = min(add_quantity, inventory.quantity)

                    if add_quantity <= 0:
                        continue

                    inventory.quantity -= add_quantity

                elif trading.trade_type == Trading.TradeType.PURCHASE:
                    inventory.quantity += add_quantity

                inventory.save()

                item.fulfilled_quantity += add_quantity
                item.quantity += add_quantity
                item.quantity_before = quantity_before
                item.quantity_after = inventory.quantity
                item.save()

                was_fulfilled = True
                quantity_to_add -= add_quantity

                if quantity_to_add <= 0:
                    break

        all_done = not TradingItem.objects.filter(
            trading=trading,
            fulfilled_quantity__lt=models.F('requested_quantity')
        ).exists()

        if was_fulfilled:
            create_trading_audit_log(
                trading=trading,
                user=request.user,
                action=TradingAuditLog.Action.FULFILLED,
                description=f'Дополнена сделка #{trading.id}',
                before_data=before_snapshot,
                after_data=make_trading_snapshot(trading),
            )

        if all_done:
            trading.status = Trading.Status.COMPLETED
            trading.save()
            messages.success(request, 'Заказ полностью выполнен.')
        elif was_fulfilled:
            trading.status = Trading.Status.PENDING
            trading.save()
            messages.success(request, 'Заказ частично дополнен.')
        else:
            messages.warning(request, 'Не удалось дополнить заказ. Проверьте остатки на складе.')

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