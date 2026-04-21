from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from .models import Trading
from .forms import TradingForm
from products.models import Inventory
from users.decorators import role_required


@role_required(['admin', 'manager'])
def trading_list(request):
    tradings = Trading.objects.select_related(
        'product',
        'warehouse',
        'user',
    ).all()
    return render(request, 'trading/trading_list.html', {'tradings': tradings})


@role_required(['admin'])
def admin_trading_history(request):
    tradings = Trading.objects.select_related(
        'product',
        'warehouse',
        'user',
    ).all()

    return render(
        request,
        'trading/admin_trading_history.html',
        {'tradings': tradings}
    )


@role_required(['admin', 'manager'])
def trading_detail(request, pk):
    trading = get_object_or_404(
        Trading.objects.select_related('product', 'warehouse', 'user'),
        pk=pk
    )
    return render(request, 'trading/trading_detail.html', {'trading': trading})


@role_required(['admin', 'manager'])
def trading_create(request):
    if request.method == 'POST':
        form = TradingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                trading = form.save(commit=False)
                trading.user = request.user

                inventory, created = Inventory.objects.get_or_create(
                    product=trading.product,
                    warehouse=trading.warehouse,
                    defaults={'quantity': 0},
                )

                quantity_before = inventory.quantity
                trade_quantity = trading.quantity

                if trading.trade_type == Trading.TradeType.PURCHASE:
                    inventory.quantity += trade_quantity

                elif trading.trade_type == Trading.TradeType.SELL:
                    if inventory.quantity < trade_quantity:
                        form.add_error(
                            'quantity',
                            f'Недостаточно товара на складе. Сейчас в наличии: {inventory.quantity}'
                        )
                        return render(request, 'trading/trading_add.html', {'form': form})
                    inventory.quantity -= trade_quantity

                trading.quantity_before = quantity_before
                trading.quantity_after = inventory.quantity

                inventory.save()
                trading.save()

                return redirect('trading_list')
    else:
        form = TradingForm()

    return render(request, 'trading/trading_add.html', {'form': form})


@role_required(['admin', 'manager'])
def trading_update(request, pk):
    trading = get_object_or_404(Trading, pk=pk)

    if request.method == 'POST':
        form = TradingForm(request.POST, instance=trading)
        if form.is_valid():
            form.save()
            return redirect('trading_detail', pk=trading.pk)
    else:
        form = TradingForm(instance=trading)

    return render(request, 'trading/trading_add.html', {'form': form})