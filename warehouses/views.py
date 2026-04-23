from django.shortcuts import render, get_object_or_404

from .models import Warehouse
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