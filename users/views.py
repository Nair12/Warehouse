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

    if request.user.role == "manager":
        return redirect('/users/manager-dashboard/')

    if request.user.role == "reader":
        return redirect('/users/reader-dashboard/')

    return redirect('/login/')


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

    context = {
        "username": request.user.username,
        "role": request.user.role,
        "products_count": products_count,
        "warehouses_count": warehouses_count,
        "total_inventory": total_inventory,
        "last_trades": last_trades,
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