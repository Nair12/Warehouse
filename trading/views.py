from django.shortcuts import render, get_object_or_404, redirect
from .models import Trading
from .forms import TradingForm
from users.decorators import role_required


@role_required(['admin', 'manager'])
def trading_list(request):
    tradings = Trading.objects.all()
    return render(request, 'trading/trading_list.html', {'tradings': tradings})


@role_required(['admin', 'manager'])
def trading_detail(request, pk):
    trading = get_object_or_404(Trading, pk=pk)
    return render(request, 'trading/trading_detail.html', {'trading': trading})


@role_required(['admin', 'manager'])
def trading_create(request):
    if request.method == 'POST':
        form = TradingForm(request.POST)
        if form.is_valid():
            trading = form.save(commit=False)
            trading.user = request.user
            trading.save()
            return redirect('trading_list')
    else:
        form = TradingForm()

    return render(request, 'trading/trading_form.html', {'form': form})


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

    return render(request, 'trading/trading_form.html', {'form': form})