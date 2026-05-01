# warehouses/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect

from users.decorators import role_required
from .forms import WarehouseTransferForm
from .models import Warehouse, WarehouseTransfer
from products.models import Inventory


def warehouse_detail_view(request, pk):
    warehouse = get_object_or_404(Warehouse, id=pk)
    query = request.GET.get("q", "").strip()

    inventory = list(
        Inventory.objects.filter(
            warehouse=warehouse,
            quantity__gt=0
        ).select_related("product")
    )

    if query:
        query_lower = query.casefold()

        inventory = [
            item for item in inventory
            if query_lower in (item.product.name or "").casefold()
            or query_lower in (item.product.description or "").casefold()
        ]

    return render(request, "warehouse_detail.html", {
        "warehouse": warehouse,
        "inventory": inventory,
        "query": query,
    })


@login_required
@role_required(["admin", "manager", "senior_manager"])
def warehouse_transfer_create_view(request):
    if request.method == "POST":
        form = WarehouseTransferForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                transfer = form.save(commit=False)
                transfer.created_by = request.user
                transfer.save()

                from_inventory = Inventory.objects.select_for_update().get(
                    product=transfer.product,
                    warehouse=transfer.from_warehouse,
                )

                to_inventory, created = Inventory.objects.select_for_update().get_or_create(
                    product=transfer.product,
                    warehouse=transfer.to_warehouse,
                    defaults={"quantity": 0},
                )

                from_inventory.quantity -= transfer.quantity
                to_inventory.quantity += transfer.quantity

                from_inventory.save()
                to_inventory.save()

            messages.success(request, "Товар успешно перемещён между складами.")
            return redirect("warehouses:warehouse_detail", pk=transfer.to_warehouse.id)
    else:
        form = WarehouseTransferForm()

    return render(request, "warehouse_transfer_form.html", {
        "form": form,
    })


@login_required
@role_required(["admin", "manager", "senior_manager"])
def warehouse_transfer_history_view(request):
    transfers = WarehouseTransfer.objects.select_related(
        "product",
        "from_warehouse",
        "to_warehouse",
        "created_by",
    ).all()

    return render(request, "warehouse_transfer_history.html", {
        "transfers": transfers,
    })


@login_required
@role_required(["admin", "manager", "senior_manager"])
def warehouse_inventory_quantity_api(request):
    product_id = request.GET.get("product_id")
    warehouse_id = request.GET.get("warehouse_id")

    if not product_id or not warehouse_id:
        return JsonResponse({
            "success": False,
            "quantity": 0,
            "unit": "",
            "message": "Выберите товар и склад",
        })

    inventory = Inventory.objects.filter(
        product_id=product_id,
        warehouse_id=warehouse_id,
    ).select_related("product").first()

    if not inventory:
        return JsonResponse({
            "success": True,
            "quantity": 0,
            "unit": "",
            "message": "На этом складе нет выбранного товара",
        })

    return JsonResponse({
        "success": True,
        "quantity": inventory.quantity,
        "unit": inventory.product.get_unit_display(),
        "message": f"Доступно на складе: {inventory.quantity} {inventory.product.get_unit_display()}",
    })
