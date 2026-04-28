from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect

from products.forms import ProductForm
from products.models import Product, Inventory
from trading.models import Trading
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

    if request.user.role in ["manager", "senior_manager"]:
        return redirect('/users/manager-dashboard/')

    if request.user.role == "reader":
        return redirect('/users/reader-dashboard/')

    return redirect('/login/')


import json
from django.db.models import Sum
from django.db.models.functions import TruncDate

@role_required(["manager", "senior_manager"])
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
                "sell": 0,
                "purchase": 0,
            }

        grouped[day_str][row["trade_type"]] = row["total"] or 0

    chart_labels = list(grouped.keys())
    sales_values = [grouped[day]["sell"] for day in chart_labels]
    purchase_values = [grouped[day]["purchase"] for day in chart_labels]

    context = {
        "username": request.user.username,
        "role": request.user.role,
        "products_count": products_count,
        "warehouses_count": warehouses_count,
        "total_inventory": total_inventory,
        "last_trades": last_trades,

        "sales_labels": json.dumps(chart_labels),
        "sales_values": json.dumps(sales_values),
        "purchase_values": json.dumps(purchase_values),
    }

    return render(request, "users/manager_dashboard.html", context)


@role_required(["manager","senior_manager"])
def add_product_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('products:product_list')
    else:
        form = ProductForm()

    return render(request, 'product_add.html', {'form': form})


@role_required(["admin", "manager","senior_manager"])
def warehouse_create_view(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('warehouse_list')
    else:
        form = WarehouseForm()

    return render(request, 'warehouse_add.html', {'form': form})


@role_required(["admin", "manager", "reader","senior_manager"])
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


@role_required(["admin", "manager", "reader","senior_manager"])
def global_search(request):
    query = request.GET.get("q", "").strip()

    products = []
    warehouses = []
    tradings = []

    if query:
        query_lower = query.casefold()

        all_products = list(Product.objects.all())
        all_warehouses = list(Warehouse.objects.all())
        all_tradings = list(
            Trading.objects.select_related("product", "warehouse").order_by("-created_at")
        )

        products = [
            product for product in all_products
            if query_lower in (product.name or "").casefold()
               or query_lower in (product.description or "").casefold()
        ]
        products = sorted(products, key=lambda x: (x.name or "").casefold())

        warehouses = [
            warehouse for warehouse in all_warehouses
            if query_lower in (warehouse.city or "").casefold()
        ]
        warehouses = sorted(warehouses, key=lambda x: (x.city or "").casefold())

        tradings = [
            trading for trading in all_tradings
            if query_lower in str(getattr(trading, "name", "") or "").casefold()
               or query_lower in str(getattr(getattr(trading, "product", None), "name", "") or "").casefold()
               or query_lower in str(getattr(getattr(trading, "warehouse", None), "city", "") or "").casefold()
        ]

    context = {
        "query": query,
        "products": products,
        "warehouses": warehouses,
        "tradings": tradings,
    }

    return render(request, "users/search_results.html", context)


import json
from django.http import JsonResponse
def set_timezone(request):
    if request.method == "POST":
        data = json.loads(request.body)
        request.session["django_timezone"] = data.get("timezone")
        return JsonResponse({"status": "ok"})
