from django.shortcuts import render, get_object_or_404
from .models import Warehouse
from products.models import Inventory


def warehouse_detail_view(request, pk):
    warehouse = get_object_or_404(Warehouse, id=pk)
    inventory = Inventory.objects.filter(warehouse=warehouse)

    return render(request, "warehouse_detail.html", {
        "warehouse": warehouse,
        "inventory": inventory
    })