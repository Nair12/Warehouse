import json

from django.db.models import Sum, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render, redirect

from products.forms import ProductForm
from products.models import Product, Inventory
from trading.models import Trading, TradingItem
from warehouses.forms import WarehouseForm
from warehouses.models import Warehouse
from .decorators import role_required


def test_view(request):
    return HttpResponse(f"Твоя роль: {request.user.role}")


def home_view(request):
    return HttpResponse("Главная страница")


def role_redirect_view(request):
    print(
        f"User: {request.user}, Auth: {request.user.is_authenticated}, Role: {getattr(request.user, 'role', 'no role')}"
    )
    if not request.user.is_authenticated:
        return redirect('/login/')

    if request.user.role == "admin":
        return redirect('/admin/')

    if request.user.role == "manager":
        return redirect('/users/manager-dashboard/')

    if request.user.role == "reader":
        return redirect('/users/reader-dashboard/')

    return redirect('/login/')


import json

from django.db.models import Sum
from django.db.models.functions import TruncDate

import json
from django.db.models import Sum
from django.db.models.functions import TruncDate


@role_required(["manager"])
def manager_dashboard(request):
    products_count = Product.objects.count()
    warehouses_count = Warehouse.objects.count()
    total_inventory = Inventory.objects.aggregate(total=Sum("quantity"))["total"] or 0

    last_trades = Trading.objects.select_related(
        "product",
        "warehouse",
        "user",
    ).order_by("-created_at")[:5]

    trades_by_day = (
        Trading.objects
        .annotate(day=TruncDate("created_at"))
        .values("day", "trade_type")
        .annotate(total=Sum("quantity"))
        .order_by("day")
    )

    grouped = {}
    for row in trades_by_day:
        day = row["day"]
        if not day:
            continue

        day_str = day.strftime("%d.%m.%Y")
        if day_str not in grouped:
            grouped[day_str] = {
                "purchase": 0,
                "sell": 0,
            }

        grouped[day_str][row["trade_type"]] = row["total"] or 0

    chart_labels = list(grouped.keys())
    purchase_values = [grouped[day]["purchase"] for day in chart_labels]
    sales_values = [grouped[day]["sell"] for day in chart_labels]

    context = {
        "username": request.user.username,
        "role": request.user.role,
        "products_count": products_count,
        "warehouses_count": warehouses_count,
        "total_inventory": total_inventory,
        "last_trades": last_trades,
        "sales_labels": json.dumps(chart_labels),
        "purchase_values": json.dumps(purchase_values),
        "sales_values": json.dumps(sales_values),
    }
    return render(request, "users/manager_dashboard.html", context)


@role_required(["manager"])
def add_product_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('products:product_list')
    else:
        form = ProductForm()

    return render(request, 'product_add.html', {'form': form})


@role_required(["admin", "manager"])
def warehouse_create_view(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('warehouse_list')
    else:
        form = WarehouseForm()

    return render(request, 'warehouse_add.html', {'form': form})


@role_required(["admin", "manager", "reader"])
def warehouse_list_view(request):
    warehouses = Warehouse.objects.all().order_by('-created_at')
    return render(request, 'warehouse_list.html', {'warehouses': warehouses})


@role_required(["admin"])
def users_manage_view(request):
    pass


@role_required(["reader"])
def reader_dashboard(request):
    context = {
        "username": request.user.username,
        "role": request.user.role,
    }
    return render(request, "users/reader_dashboard.html", context)


@role_required(["admin", "manager", "reader"])
def global_search(request):
    query = request.GET.get("q", "").strip()

    products = Product.objects.none()
    warehouses = Warehouse.objects.none()
    tradings = Trading.objects.none()

    if query:
        products = Product.objects.filter(
            name__icontains=query
        ).order_by("name")

        warehouses = Warehouse.objects.filter(
            city__icontains=query
        ).order_by("city")

        tradings = Trading.objects.filter(
            Q(name__icontains=query) |
            Q(product__name__icontains=query) |
            Q(warehouse__city__icontains=query)
        ).select_related("product", "warehouse").order_by("-created_at")

    context = {
        "query": query,
        "products": products,
        "warehouses": warehouses,
        "tradings": tradings,
    }

    return render(request, "users/search_results.html", context)
