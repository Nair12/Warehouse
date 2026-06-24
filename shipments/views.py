from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from users.decorators import role_required

from .forms import ShipmentTaskForm, ShipmentTaskItemFormSet
from .models import ShipmentTask


@role_required(["manager", "senior_manager"])
def shipment_task_list(request):
    status_filter = request.GET.get("status", "all")
    query = request.GET.get("q", "").strip()

    tasks = ShipmentTask.objects.select_related(
        "created_by",
        "assigned_to",
    ).prefetch_related(
        "items",
        "items__product",
    )

    if status_filter == "mine":
        tasks = tasks.filter(assigned_to=request.user)
    elif status_filter == "created":
        tasks = tasks.filter(created_by=request.user)
    elif status_filter in [
        ShipmentTask.STATUS_NEW,
        ShipmentTask.STATUS_SEEN,
        ShipmentTask.STATUS_SHIPPED,
        ShipmentTask.STATUS_PROBLEM,
    ]:
        tasks = tasks.filter(status=status_filter)

    if query:
        tasks = tasks.filter(
            Q(recipient_name__icontains=query)
            | Q(comment__icontains=query)
            | Q(items__product__name__icontains=query)
            | Q(items__product__description__icontains=query)
        ).distinct()

    context = {
        "tasks": tasks,
        "status_filter": status_filter,
        "query": query,
    }

    return render(request, "shipments/shipment_task_list.html", context)


@role_required(["manager", "senior_manager"])
def shipment_task_create(request):
    if request.method == "POST":
        form = ShipmentTaskForm(request.POST)
        formset = ShipmentTaskItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()

            formset.instance = task
            formset.save()

            messages.success(request, "Задание на отправку создано.")
            return redirect("shipments:shipment_task_list")
    else:
        form = ShipmentTaskForm()
        formset = ShipmentTaskItemFormSet()

    context = {
        "form": form,
        "formset": formset,
    }

    return render(request, "shipments/shipment_task_create.html", context)


@role_required(["manager", "senior_manager"])
def shipment_task_detail(request, pk):
    task = get_object_or_404(
        ShipmentTask.objects.select_related(
            "created_by",
            "assigned_to",
        ).prefetch_related(
            "items",
            "items__product",
        ),
        pk=pk,
    )

    if task.assigned_to == request.user and task.status == ShipmentTask.STATUS_NEW:
        task.mark_seen()

    return render(
        request,
        "shipments/shipment_task_detail.html",
        {"task": task},
    )


@role_required(["manager", "senior_manager"])
@require_POST
def shipment_task_mark_shipped(request, pk):
    task = get_object_or_404(ShipmentTask, pk=pk)

    if task.assigned_to != request.user and request.user.role != "senior_manager":
        messages.error(request, "Вы не можете закрыть это задание.")
        return redirect("shipments:shipment_task_detail", pk=task.pk)

    task.mark_shipped()
    messages.success(request, "Задание отмечено как отправленное.")
    return redirect("shipments:shipment_task_detail", pk=task.pk)


@role_required(["manager", "senior_manager"])
@require_POST
def shipment_task_mark_problem(request, pk):
    task = get_object_or_404(ShipmentTask, pk=pk)

    if task.assigned_to != request.user and request.user.role != "senior_manager":
        messages.error(request, "Вы не можете изменить это задание.")
        return redirect("shipments:shipment_task_detail", pk=task.pk)

    task.mark_problem()
    messages.success(request, "Задание отмечено как проблемное.")
    return redirect("shipments:shipment_task_detail", pk=task.pk)
