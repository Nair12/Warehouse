from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Inventory
from warehouses.models import Warehouse
from .forms import ProductForm, InventoryQuantityForm
from users.decorators import role_required

@role_required(["admin", "manager", "reader", "senior_manager"])
def product_list_view(request):
    query = request.GET.get("q", "").strip()


    in_stock = request.GET.get("in_stock")
    if in_stock in ["None", ""]: in_stock = None

    sort = request.GET.get("sort")
    if sort in ["None", ""]: sort = None

    warehouse_id = request.GET.get("warehouse")
    if warehouse_id in ["None", ""]: warehouse_id = None


    products = Product.objects.all()

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

    warehouses = Warehouse.objects.all().order_by("city")

    return render(request, "products/product_list.html", {
        "page_obj": page_obj,          # Передаем объект страницы вместо списка products
        "query": query,
        "in_stock": in_stock,
        "sort": sort,
        "warehouses": warehouses,
        "selected_warehouse": warehouse_id,
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
    product = get_object_or_404(Product, id=pk)

    inventories = Inventory.objects.filter(product=product).select_related("warehouse")
    inventory_map = {item.warehouse_id: item for item in inventories}

    warehouse_rows = []
    for warehouse in Warehouse.objects.all():
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
    inventory = get_object_or_404(Inventory, id=pk)

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
    inventory = get_object_or_404(Inventory, id=pk)

    if request.method == "POST":
        if action == "increase":
            inventory.quantity += 1
        elif action == "decrease" and inventory.quantity > 0:
            inventory.quantity -= 1

        inventory.save()

    return redirect("products:product_detail", pk=inventory.product.id)


def warehouse_reader_list_view(request):
    warehouses = Warehouse.objects.all()

    return render(request, "products/warehouses/list.html", {
        "warehouses": warehouses,
    })


def warehouse_reader_detail_view(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)

    query = request.GET.get("q", "")

    inventory_items = (
        Inventory.objects
        .filter(warehouse=warehouse)
        .select_related("product")
        .order_by("product__name")
    )

    if query:
        inventory_items = inventory_items.filter(product__name__icontains=query)

    return render(request, "products/warehouses/detail.html", {
        "warehouse": warehouse,
        "inventory_items": inventory_items,
        "query": query,
    })
