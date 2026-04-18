from django.shortcuts import render, redirect, get_object_or_404
from .models import Product
from .forms import ProductForm
from users.decorators import role_required


@role_required(["admin", "manager", "reader"])
def product_list_view(request):
    products = Product.objects.all().order_by("-created_at")
    return render(request, "product_list.html", {"products": products})


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

    return render(request, "product_form.html", {"form": form})


@role_required(["admin", "manager", "reader"])
def product_detail_view(request, pk):
    product = get_object_or_404(Product, id=pk)
    return render(request, "product_detail.html", {"product": product})