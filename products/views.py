import uuid
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect, get_object_or_404, Http404
from django.utils.translation import gettext as _

from .models import Product, Inventory
from warehouses.models import Warehouse
from .forms import ProductForm, InventoryQuantityForm
from users.decorators import role_required

User = get_user_model()


@role_required(["admin", "manager", "reader", "senior_manager"])
def product_list_view(request):
    user = request.user
    query = request.GET.get("q", "").strip()

    in_stock = request.GET.get("in_stock")
    if in_stock in ["None", ""]:
        in_stock = None

    sort = request.GET.get("sort")
    if sort in ["None", ""]:
        sort = None

    # ОПРЕДЕЛЯЕМ СКЛАД: Приоритет у жесткой привязки пользователя
    if user.is_authenticated and user.warehouse_id:
        warehouse_id = user.warehouse_id
        # Для фильтра в шаблоне оставляем доступным только этот склад
        warehouses = Warehouse.objects.filter(id=user.warehouse_id)
        user_warehouse = user.warehouse
    else:
        warehouse_id = request.GET.get("warehouse")
        if warehouse_id in ["None", ""]:
            warehouse_id = None
        # Админы и старшие видят все склады в фильтре
        warehouses = Warehouse.objects.all().order_by("city")
        user_warehouse = None

    products = Product.objects.all()

    # Считаем остатки только по выбранному/привязанному складу или вообще по всем
    if warehouse_id:
        products = products.annotate(
            total_quantity=Coalesce(
                Sum(
                    "inventory_items__quantity",
                    filter=Q(inventory_items__warehouse_id=warehouse_id)
                ),
                0
            )
        )
    else:
        products = products.annotate(
            total_quantity=Coalesce(
                Sum("inventory_items__quantity"),
                0
            )
        )

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if in_stock == "1":
        products = products.filter(total_quantity__gt=0)

    if sort == "qty_asc":
        products = products.order_by("total_quantity")
    elif sort == "qty_desc":
        products = products.order_by("-total_quantity")
    else:
        products = products.order_by("-created_at")

    paginator = Paginator(products, 30)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "products/product_list.html", {
        "page_obj": page_obj,
        "query": query,
        "in_stock": in_stock,
        "sort": sort,
        "warehouses": warehouses,
        "selected_warehouse": str(warehouse_id) if warehouse_id else None,
        "user_warehouse": user_warehouse,  # Передаем, чтобы вывести плашку на главной
    })


@role_required(["admin", "manager", "senior_manager"])
def product_create_view(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.user_id = request.user.id
            product.save()
            return redirect("products:product_list")
    else:
        form = ProductForm()

    return render(request, "products/product_form.html", {"form": form})


@role_required(["admin", "manager", "reader", "senior_manager"])
def product_detail_view(request, pk):
    user = request.user
    product = get_object_or_404(Product, id=pk)

    # Ограничиваем отображение складов внутри карточки товара
    if user.is_authenticated and user.warehouse_id:
        allowed_warehouses = Warehouse.objects.filter(id=user.warehouse_id)
        inventories = Inventory.objects.filter(product=product, warehouse_id=user.warehouse_id).select_related(
            "warehouse")
    else:
        allowed_warehouses = Warehouse.objects.all()
        inventories = Inventory.objects.filter(product=product).select_related("warehouse")

    inventory_map = {item.warehouse_id: item for item in inventories}

    warehouse_rows = []
    for warehouse in allowed_warehouses:
        inventory_item = inventory_map.get(warehouse.id)

        warehouse_rows.append({
            "warehouse": warehouse,
            "inventory": inventory_item,
            "quantity": inventory_item.quantity if inventory_item else 0,
        })

    return render(request, "products/product_detail.html", {
        "product": product,
        "warehouse_rows": warehouse_rows,
    })


@role_required(["admin", "manager", "senior_manager"])
def inventory_create_view(request, product_id, warehouse_id):
    user = request.user
    # Защита: менеджер склада не может плодить остатки на чужом складе через URL
    if user.warehouse_id and str(user.warehouse_id) != str(warehouse_id):
        raise Http404(_("Вы не имеете доступа к этому складу."))

    product = get_object_or_404(Product, id=product_id)
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)

    inventory = Inventory(product=product, warehouse=warehouse)

    if request.method == "POST":
        form = InventoryQuantityForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            return redirect("products:product_detail", pk=product.id)
    else:
        form = InventoryQuantityForm(instance=inventory)

    return render(request, "products/inventory_quantity_form.html", {
        "form": form,
        "inventory": inventory
    })


@role_required(["admin", "manager", "senior_manager"])
def inventory_update_view(request, pk):
    user = request.user
    inventory = get_object_or_404(Inventory, id=pk)

    # Защита: проверка изменения остатков
    if user.warehouse_id and inventory.warehouse_id != user.warehouse_id:
        raise Http404(_("Вы не имеете доступа к этому складу."))

    if request.method == "POST":
        form = InventoryQuantityForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            return redirect("products:product_detail", pk=inventory.product.id)
    else:
        form = InventoryQuantityForm(instance=inventory)

    return render(request, "products/inventory_quantity_form.html", {
        "form": form,
        "inventory": inventory
    })


@role_required(["admin", "manager", "senior_manager"])
def inventory_adjust_view(request, pk, action):
    user = request.user
    inventory = get_object_or_404(Inventory, id=pk)

    # Защита: проверка быстрых кнопок +/- 1
    if user.warehouse_id and inventory.warehouse_id != user.warehouse_id:
        raise Http404(_("Вы не имеете доступа к этому складу."))

    if request.method == "POST":
        if action == "increase":
            inventory.quantity += 1
        elif action == "decrease" and inventory.quantity > 0:
            inventory.quantity -= 1

        inventory.save()

    return redirect("products:product_detail", pk=inventory.product.id)


@role_required(["admin", "manager", "reader", "senior_manager"])
def warehouse_reader_list_view(request):
    user = request.user
    warehouses = Warehouse.objects.all().order_by("city")

    if user.is_authenticated and user.warehouse_id:
        warehouses = warehouses.filter(id=user.warehouse_id)

    return render(request, "products/warehouses/list.html", {
        "warehouses": warehouses,
    })


@role_required(["admin", "manager", "reader", "senior_manager"])
def warehouse_reader_detail_view(request, pk):
    user = request.user

    # Защита: если передан ID чужого склада, шлём 404
    if user.is_authenticated and user.warehouse_id and str(user.warehouse_id) != str(pk):
        raise Http404(_("Вы не имеете доступа к просмотру этого склада."))

    warehouse = get_object_or_404(Warehouse, pk=pk)
    query = request.GET.get("q", "").strip()

    inventory_items = (
        Inventory.objects
        .filter(warehouse=warehouse)
        .select_related("product")
        .order_by("product__name")
    )

    if query:
        inventory_items = inventory_items.filter(product__name__icontains=query)

    paginator = Paginator(inventory_items, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "products/warehouses/detail.html", {
        "warehouse": warehouse,
        "page_obj": page_obj,
        "query": query,
    })
