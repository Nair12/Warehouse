from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.forms import formset_factory

from .models import Trading, TradingItem
from .forms import TradingForm, TradingItemForm, AttachmentFormSet
from products.models import Inventory
from users.decorators import role_required


TradingItemFormSet = formset_factory(TradingItemForm, extra=1)


@role_required(['admin', 'manager', "senior_manager"])
def trading_list(request):
    current_type = request.GET.get('type')

    tradings = Trading.objects.select_related(
        'product',
        'warehouse',
        'user',
    ).prefetch_related(
        'items',
        'items__product',
        'items__warehouse',
    ).filter(
        status=Trading.Status.COMPLETED
    )

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
                    'fulfilled_quantity': 0
                }

            grouped_items[key]['requested_quantity'] += item.requested_quantity
            grouped_items[key]['fulfilled_quantity'] += item.fulfilled_quantity

        trading.grouped_items = list(grouped_items.values())

        trading.is_in_progress = False

    return render(
        request,
        'trading/trading_list.html',
        {
            'tradings': tradings,
            'current_type': current_type,
            'page_title': 'История сделок',
            'is_orders_page': False,
        }
    )


@role_required(['admin', 'manager', "senior_manager"])
def orders_list(request):
    current_type = request.GET.get('type')

    tradings = Trading.objects.select_related(
        'product',
        'warehouse',
        'user',
    ).prefetch_related(
        'items',
        'items__product',
        'items__warehouse',
    ).filter(
        status=Trading.Status.PENDING
    )

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

    return render(
        request,
        'trading/trading_list.html',
        {
            'tradings': tradings,
            'current_type': current_type,
            'page_title': 'Заказы',
            'is_orders_page': True,
        }
    )


@role_required(['admin'])
def admin_trading_history(request):
    tradings = Trading.objects.select_related(
        'product',
        'warehouse',
        'user',
    ).prefetch_related(
        'items',
        'items__product',
        'items__warehouse',
    ).all()

    return render(
        request,
        'trading/admin_trading_history.html',
        {'tradings': tradings}
    )


@role_required(['admin', 'manager', "senior_manager"])
def trading_detail(request, pk):
    trading = get_object_or_404(
        Trading.objects.select_related(
            'product',
            'warehouse',
            'user',
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

    return render(
        request,
        'trading/trading_detail.html',
        {
            'trading': trading,
            'grouped_items': grouped_items,
            'has_remaining': has_remaining,
        }
    )


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
                return render(
                    request,
                    'trading/trading_add.html',
                    {
                        'form': form,
                        'item_formset': item_formset,
                        'formset': formset,
                    }
                )

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

                if trading.trade_type == Trading.TradeType.PURCHASE:
                    first_fulfilled_quantity = first_item['fulfilled_quantity']
                    first_quantity_after = first_quantity_before + first_fulfilled_quantity
                else:
                    first_fulfilled_quantity = min(
                        first_inventory.quantity,
                        first_item['requested_quantity']
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
                        inventory.quantity += fulfilled_quantity

                    elif trading.trade_type == Trading.TradeType.SELL:
                        available_quantity = inventory.quantity
                        fulfilled_quantity = min(
                            fulfilled_quantity,
                            requested_quantity,
                            available_quantity
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

                if total_fulfilled >= total_requested:
                    trading.status = Trading.Status.COMPLETED
                else:
                    trading.status = Trading.Status.PENDING

                trading.save()

                attachments = formset.save(commit=False)
                for attachment in attachments:
                    attachment.trade = trading
                    attachment.save()

                return redirect('trading_list')

    else:
        form = TradingForm()
        item_formset = TradingItemFormSet(prefix='items')
        formset = AttachmentFormSet()

    return render(
        request,
        'trading/trading_add.html',
        {
            'form': form,
            'item_formset': item_formset,
            'formset': formset,
        }
    )


@role_required(['admin', 'manager', "senior_manager"])
def trading_update(request, pk):
    trading = get_object_or_404(Trading, pk=pk)

    if (
        not trading.can_be_modified
        and getattr(request.user, 'role', None) != 'admin'
    ):
        return redirect('trading_detail', pk=trading.pk)

    items = trading.items.select_related('product', 'warehouse').all()

    TradingItemEditFormSet = formset_factory(TradingItemForm, extra=0)

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
            form.save()
            return redirect('trading_detail', pk=trading.pk)

    else:
        form = TradingForm(instance=trading)
        item_formset = TradingItemEditFormSet(
            initial=initial_items,
            prefix='items'
        )

    return render(
        request,
        'trading/trading_add.html',
        {
            'form': form,
            'item_formset': item_formset,
            'trading': trading,
        }
    )


@role_required(['admin', 'manager', "senior_manager"])
def trading_delete(request, pk):
    trading = get_object_or_404(Trading, pk=pk)

    if (
        not trading.can_be_modified
        and getattr(request.user, 'role', None) != 'admin'
    ):
        return redirect('trading_detail', pk=trading.pk)

    if request.method == 'POST':
        trading.delete()
        return redirect('trading_list')

    return render(
        request,
        'trading/trading_confirm_delete.html',
        {'trading': trading}
    )


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
        "quantity": inventory.quantity if inventory else 0
    })


@role_required(['admin', 'manager'])
def trading_fulfill(request, pk):
    trading = get_object_or_404(
        Trading.objects.prefetch_related(
            'items',
            'items__product',
            'items__warehouse',
        ),
        pk=pk
    )

    if trading.trade_type != Trading.TradeType.SELL:
        messages.error(request, 'Довыдача доступна только для продаж.')
        return redirect('trading_detail', pk=trading.pk)

    if request.method != 'POST':
        return redirect('trading_detail', pk=trading.pk)

    was_fulfilled = False

    with transaction.atomic():
        items = trading.items.select_related(
            'product',
            'warehouse',
        ).select_for_update()

        for item in items:
            remaining_quantity = item.requested_quantity - item.fulfilled_quantity

            if remaining_quantity <= 0:
                continue

            inventory, _ = Inventory.objects.select_for_update().get_or_create(
                product=item.product,
                warehouse=item.warehouse,
                defaults={'quantity': 0},
            )

            if inventory.quantity <= 0:
                continue

            quantity_to_fulfill = min(
                remaining_quantity,
                inventory.quantity
            )

            quantity_before = inventory.quantity
            inventory.quantity -= quantity_to_fulfill
            quantity_after = inventory.quantity
            inventory.save()

            item.fulfilled_quantity += quantity_to_fulfill
            item.quantity += quantity_to_fulfill
            item.quantity_before = quantity_before
            item.quantity_after = quantity_after
            item.save()

            was_fulfilled = True

    if was_fulfilled:
        messages.success(request, 'Товар успешно довыдан по сделке.')
    else:
        messages.warning(request, 'На складе нет доступного товара для довыдачи.')

    all_items_done = all(
        (item.requested_quantity - item.fulfilled_quantity) <= 0
        for item in trading.items.all()
    )

    if was_fulfilled and all_items_done:
        trading.status = Trading.Status.COMPLETED
        trading.save()

    return redirect('trading_detail', pk=trading.pk)