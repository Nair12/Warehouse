from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Inventory
from warehouses.models import Warehouse
from .forms import ProductForm, InventoryQuantityForm
from users.decorators import role_required


@role_required(["admin", "manager", "reader"])
def product_list_view(request):
    products = Product.objects.all().order_by("-created_at")
    return render(request, "products/product_list.html", {"products": products})


@role_required(["admin", "manager"])
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


@role_required(["admin", "manager", "reader"])
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


@role_required(["admin", "manager"])
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


@role_required(["admin", "manager"])
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


@role_required(["admin", "manager"])
def inventory_adjust_view(request, pk, action):
    inventory = get_object_or_404(Inventory, id=pk)

    if request.method == "POST":
        if action == "increase":
            inventory.quantity += 1
        elif action == "decrease" and inventory.quantity > 0:
            inventory.quantity -= 1

        inventory.save()

    return redirect("products:product_detail", pk=inventory.product.id)