from django.shortcuts import render
from products.models import Product


def product_list_view(request):
    products = Product.objects.all().order_by("-created_at")
    return render(request, "product_list.html", {"products": products})