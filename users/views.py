from django.http import HttpResponse
from django.shortcuts import render, redirect

from products.forms import ProductForm
from warehouses.forms import WarehouseForm
from warehouses.models import Warehouse
from .decorators import role_required


def test_view(request):
    return HttpResponse(f"Твоя роль: {request.user.role}")


def home_view(request):
    return HttpResponse("Главная страница")


def role_redirect_view(request):
    print(
        f"User: {request.user}, Auth: {request.user.is_authenticated}, Role: {getattr(request.user, 'role', 'no role')}")
    if not request.user.is_authenticated:
        return redirect('/login/')

    if request.user.role == "admin":
        return redirect('/admin/')

    if request.user.role == "manager":
        return redirect('/users/manager-dashboard/')

    if request.user.role == "reader":
        return redirect('/users/reader-dashboard/')

    return redirect('/login/')


@role_required(["manager"])
def manager_dashboard(request):
    context = {
        "username": request.user.username,
        "role": request.user.role,
    }
    return render(request, "users/manager_dashboard.html", context)


@role_required(["manager"])
def add_product_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST,request.FILES)
        if form.is_valid():
            form.save()
            return redirect('products:product_list')
    else:
        form = ProductForm()

    return render(request, 'product_add.html', {'form': form})




def warehouse_create_view(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('warehouse_list')
    else:
        form = WarehouseForm()

    return render(request, 'warehouse_add.html', {'form': form})



def warehouse_list_view(request):
    warehouses = Warehouse.objects.all().order_by('-created_at')
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