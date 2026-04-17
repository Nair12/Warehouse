from django.http import HttpResponse
from django.shortcuts import render, redirect

from products.forms import ProductForm
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
    return render(request, "manager_dashboard.html", context)


@role_required(["reader"])
def reader_dashboard(request):
    context = {
        "username": request.user.username,
        "role": request.user.role,
    }
    return render(request, "reader_dashboard.html", context)


@role_required(["manager"])
def add_product_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('products:list')
    else:
        form = ProductForm()

    return render(request, 'product_add.html', {'form': form})


@role_required(["admin"])
def users_manage_view(request):
    pass