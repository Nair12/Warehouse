from .models import ShipmentTask


def shipment_notifications(request):
    if not request.user.is_authenticated:
        return {
            "shipment_pending_count": 0,
        }

    count = ShipmentTask.objects.filter(
        assigned_to=request.user,
        status=ShipmentTask.STATUS_NEW,
    ).count()

    return {
        "shipment_pending_count": count,
    }
