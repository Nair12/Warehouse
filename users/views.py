from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from django.conf import settings

from products.forms import ProductForm
from products.models import Product, Inventory
from trading.models import Trading
from warehouses.forms import WarehouseForm
from warehouses.models import Warehouse
from .decorators import role_required
import json
from urllib.parse import urlsplit, urlunsplit
from datetime import timedelta
from django.db.models.functions import TruncDate
from django.utils import timezone


def test_view(request):
    return HttpResponse(f"Твоя роль: {request.user.role}")


def home_view(request):
    return HttpResponse("Главная страница")




def switch_language_view(request, language_code):
    allowed_codes = [code for code, name in settings.LANGUAGES]

    if language_code not in allowed_codes:
        language_code = settings.LANGUAGE_CODE

    next_url = request.META.get('HTTP_REFERER') or '/'
    parsed_url = urlsplit(next_url)
    path_parts = parsed_url.path.split('/')

    if len(path_parts) > 1 and path_parts[1] in allowed_codes:
        path_parts[1] = language_code
    else:
        path_parts.insert(1, language_code)

    new_path = '/'.join(path_parts)
    if not new_path.startswith('/'):
        new_path = '/' + new_path

    redirect_url = urlunsplit(('', '', new_path, parsed_url.query, parsed_url.fragment))

    request.session['_language'] = language_code

    response = redirect(redirect_url)
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        language_code,
        max_age=getattr(settings, 'LANGUAGE_COOKIE_AGE', None),
        path=getattr(settings, 'LANGUAGE_COOKIE_PATH', '/'),
        domain=getattr(settings, 'LANGUAGE_COOKIE_DOMAIN', None),
        secure=getattr(settings, 'LANGUAGE_COOKIE_SECURE', False),
        httponly=getattr(settings, 'LANGUAGE_COOKIE_HTTPONLY', False),
        samesite=getattr(settings, 'LANGUAGE_COOKIE_SAMESITE', 'Lax'),
    )
    return response

def role_redirect_view(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if request.user.role == "admin":
        return redirect('/admin/')

    if request.user.role in ["manager", "senior_manager"]:
        return redirect('/users/manager-dashboard/')

    if request.user.role == "reader":
        return redirect('/users/reader-dashboard/')

    return redirect('/login/')


@role_required(["manager", "senior_manager"])
def manager_dashboard(request):
    period = request.GET.get("period", "30d")

    products_count = Product.objects.count()
    warehouses_count = Warehouse.objects.count()
    total_inventory = Inventory.objects.aggregate(total=Sum("quantity"))["total"] or 0

    last_trades = Trading.objects.select_related(
        "product",
        "warehouse",
        "user",
    ).filter(
        product__isnull=False,
    ).order_by("-created_at")[:5]

    now = timezone.now()

    period_map = {
        "7d": now - timedelta(days=7),
        "30d": now - timedelta(days=30),
        "90d": now - timedelta(days=90),
        "year": now - timedelta(days=365),
    }

    trades = Trading.objects.all()

    if period in period_map:
        trades = trades.filter(created_at__gte=period_map[period])

    trades_by_day = (
        trades
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

        grouped[day_str][row["trade_type"]] = float(row["total"] or 0)

    chart_labels = list(grouped.keys())
    sales_values = [float(grouped[day]["sell"]) for day in chart_labels]
    purchase_values = [float(grouped[day]["purchase"]) for day in chart_labels]

    popular_products = (
        Trading.objects
        .filter(
            trade_type=Trading.TradeType.SELL,
            product__isnull=False,
        )
        .values("product__id", "product__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:5]
    )

    context = {
        "username": request.user.username,
        "role": request.user.role,
        "products_count": products_count,
        "warehouses_count": warehouses_count,
        "total_inventory": float(total_inventory),
        "last_trades": last_trades,
        "sales_labels": json.dumps(chart_labels),
        "sales_values": json.dumps(sales_values),
        "purchase_values": json.dumps(purchase_values),
        "period": period,
        "popular_products": popular_products,
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


@role_required(["admin", "manager", "reader", "senior_manager"])
def warehouse_list_view(request):
    user = request.user


    warehouses = Warehouse.objects.annotate(
        total_quantity=Coalesce(Sum("inventory_items__quantity"), 0)
    )


    if user.is_authenticated and user.warehouse_id:
        warehouses = warehouses.filter(id=user.warehouse_id)

    # В конце применяем сортировку
    warehouses = warehouses.order_by("-created_at")

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


from django.http import JsonResponse


@login_required
@require_POST
def set_timezone(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Некорректный JSON"}, status=400)

    timezone_name = data.get("timezone")

    if not timezone_name:
        return JsonResponse({"status": "error", "message": "Часовой пояс не передан"}, status=400)

    if request.user.timezone != timezone_name:
        request.user.timezone = timezone_name
        request.user.save(update_fields=["timezone"])

    return JsonResponse({"status": "ok", "timezone": timezone_name})
