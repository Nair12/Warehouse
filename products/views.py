from django.shortcuts import render, redirect, get_object_or_404
from .models import Product
from users.decorators import role_required
from django.shortcuts import render, get_object_or_404
from products.models import Product


# 📦 Список товаров (всем)
@role_required(["admin", "manager", "reader"])
def product_list_view(request):
    products = Product.objects.all().order_by("-created_at")
    return render(request, "product_list.html", {"products": products})






# ➕ Создание (только manager/admin)
@role_required(["admin", "manager"])
def product_create_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")

        Product.objects.create(
            name=name,
            price=price
        )
        return redirect("product_list")

    return render(request, "products/product_create.html")


# 👁️ Просмотр одного товара (всем)
@role_required(["admin", "manager", "reader"])
def product_detail_view(request, pk):
    product = get_object_or_404(Product, id=pk)
    inventory_items = product.inventory_items.select_related('warehouse').all()
    return render(request, "product_detail.html", {"product": product,'inventory_items': inventory_items})