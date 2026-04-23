from collections import defaultdict

from django.forms import inlineformset_factory
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.http import JsonResponse
from django.forms import formset_factory

from .models import Trading, TradingItem
from .forms import TradingForm, TradingItemForm, AttachmentFormSet
from .models import Trading, TradingAttachment
from .forms import TradingForm
from products.models import Inventory
from users.decorators import role_required


TradingItemFormSet = formset_factory(TradingItemForm, extra=1)


@role_required(['admin', 'manager'])
def trading_list(request):
    tradings = Trading.objects.select_related(
        'product',
        'warehouse',
        'user',
    ).prefetch_related('items').all()

    return render(request, 'trading/trading_list.html', {'tradings': tradings})


@role_required(['admin'])
def admin_trading_history(request):
    tradings = Trading.objects.select_related(
        'product',
        'warehouse',
        'user',
    ).prefetch_related('items').all()

    return render(
        request,
        'trading/admin_trading_history.html',
        {'tradings': tradings}
    )


@role_required(['admin', 'manager'])
def trading_detail(request, pk):
    trading = get_object_or_404(
        Trading.objects.select_related(
            'product',
            'warehouse',
            'user'
        ).prefetch_related('items'),
        pk=pk
    )
    return render(request, 'trading/trading_detail.html', {'trading': trading})


def _get_filled_item_forms(item_formset):
    filled_forms = []

    for item_form in item_formset:
        cleaned_data = getattr(item_form, 'cleaned_data', None)
        if not cleaned_data:
            continue

        product = cleaned_data.get('product')
        warehouse = cleaned_data.get('warehouse')
        quantity = cleaned_data.get('quantity')

        if product and warehouse and quantity:
            filled_forms.append(item_form)

    return filled_forms


def _validate_sell_stock(item_forms):
    grouped_quantities = defaultdict(int)
    grouped_forms = defaultdict(list)

    for item_form in item_forms:
        product = item_form.cleaned_data['product']
        warehouse = item_form.cleaned_data['warehouse']
        quantity = item_form.cleaned_data['quantity']

        key = (product.id, warehouse.id)
        grouped_quantities[key] += quantity
        grouped_forms[key].append(item_form)

    has_errors = False

    for (product_id, warehouse_id), total_quantity in grouped_quantities.items():
        inventory = Inventory.objects.filter(
            product_id=product_id,
            warehouse_id=warehouse_id
        ).first()

        stock = inventory.quantity if inventory else 0

        if total_quantity > stock:
            has_errors = True
            related_forms = grouped_forms[(product_id, warehouse_id)]

            error_message = (
                f'Недостаточно товара на складе. '
                f'Доступно: {stock}, запрошено суммарно: {total_quantity}'
            )

            for item_form in related_forms:
                item_form.add_error('quantity', error_message)

    return not has_errors


@role_required(['admin', 'manager'])
def trading_create(request):
    if request.method == 'POST':
        form = TradingForm(request.POST)
        item_formset = TradingItemFormSet(request.POST, prefix='items')
        formset = AttachmentFormSet(request.POST, request.FILES)

        if form.is_valid() and item_formset.is_valid():
            valid_items = _get_filled_item_forms(item_formset)
        if form.is_valid() and item_formset.is_valid() and formset.is_valid():
            filled_forms = [
                item_form for item_form in item_formset
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False)
            ]

            valid_items = []
            for item_form in filled_forms:
                product = item_form.cleaned_data.get('product')
                warehouse = item_form.cleaned_data.get('warehouse')
                quantity = item_form.cleaned_data.get('quantity')

                if product and warehouse and quantity:
                    valid_items.append(item_form)

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

            trade_type = form.cleaned_data.get('trade_type')

            if trade_type == Trading.TradeType.SELL:
                is_stock_valid = _validate_sell_stock(valid_items)
                if not is_stock_valid:
                    return render(
                        request,
                        'trading/trading_add.html',
                        {
                            'form': form,
                            'item_formset': item_formset,
                        }
                    )

            with transaction.atomic():
                trading = form.save(commit=False)
                trading.user = request.user

                # Первая позиция для legacy-полей Trading
                first_item_data = valid_items[0].cleaned_data
                first_product = first_item_data['product']
                first_warehouse = first_item_data['warehouse']
                first_quantity = first_item_data['quantity']

                first_inventory, _ = Inventory.objects.get_or_create(
                    product=first_product,
                    warehouse=first_warehouse,
                    defaults={'quantity': 0},
                )

                first_quantity_before = first_inventory.quantity

                if trade_type == Trading.TradeType.PURCHASE:
                    first_quantity_after = first_quantity_before + first_quantity
                else:
                    if first_inventory.quantity < first_quantity:
                        form.add_error(
                            None,
                            f'Недостаточно товара "{first_product}" на складе "{first_warehouse}". '
                            f'Сейчас в наличии: {first_inventory.quantity}'
                        )
                        return render(
                            request,
                            'trading/trading_add.html',
                            {
                                'form': form,
                                'item_formset': item_formset,
                                'formset': formset,
                            }
                        )
                    first_quantity_after = first_quantity_before - first_quantity

                # legacy-поля в Trading
                trading.product = first_product
                trading.warehouse = first_warehouse
                trading.quantity = first_quantity
                trading.quantity_before = first_quantity_before
                trading.quantity_after = first_quantity_after
                trading.save()

                for item_form in valid_items:
                    product = item_form.cleaned_data['product']
                    warehouse = item_form.cleaned_data['warehouse']
                    quantity = item_form.cleaned_data['quantity']

                    inventory, _ = Inventory.objects.get_or_create(
                        product=product,
                        warehouse=warehouse,
                        defaults={'quantity': 0},
                    )

                    quantity_before = inventory.quantity

                    if trade_type == Trading.TradeType.PURCHASE:
                        inventory.quantity += quantity
                    elif trade_type == Trading.TradeType.SELL:
                    elif trading.trade_type == Trading.TradeType.SELL:
                        if inventory.quantity < quantity:
                            form.add_error(
                                None,
                                f'Недостаточно товара "{product}" на складе "{warehouse}". '
                                f'В наличии: {inventory.quantity}'
                            )
                            return render(
                                request,
                                'trading/trading_add.html',
                                {
                                    'form': form,
                                    'item_formset': item_formset,
                                    'formset': formset,
                                }
                            )
                        inventory.quantity -= quantity

                    inventory.save()

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

@role_required(['admin', 'manager'])
def trading_update(request, pk):
    trading = get_object_or_404(Trading, pk=pk)
    items = trading.items.all()

    TradingItemEditFormSet = formset_factory(TradingItemForm, extra=0)

    initial_items = [
        {
            'product': item.product,
            'warehouse': item.warehouse,
            'quantity': item.quantity,
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
        item_formset = TradingItemEditFormSet(initial=initial_items, prefix='items')

    return render(
        request,
        'trading/trading_add.html',
        {
            'form': form,
            'item_formset': item_formset,
            'trading': trading,
        }
    )


@role_required(['admin', 'manager'])
def get_stock(request):
    product_id = request.GET.get('product')
    warehouse_id = request.GET.get('warehouse')

    quantity = 0

    if product_id and warehouse_id:
        inventory = Inventory.objects.filter(
            product_id=product_id,
            warehouse_id=warehouse_id
        ).first()

        if inventory:
            quantity = inventory.quantity

    return JsonResponse({'quantity': quantity})