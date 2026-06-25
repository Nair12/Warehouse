from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import ShipmentTask, ShipmentTaskItem


class ShipmentTaskForm(forms.ModelForm):
    class Meta:
        model = ShipmentTask
        fields = [
            "assigned_to",
            "recipient_name",
            "comment",
        ]
        widgets = {
            "assigned_to": forms.Select(attrs={"class": "form-control"}),
            "recipient_name": forms.TextInput(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        User = get_user_model()
        self.fields["assigned_to"].queryset = User.objects.filter(
            is_active=True
        ).order_by("username")

        self.fields["assigned_to"].label = _("Кому дать задание")
        self.fields["recipient_name"].label = _("Кому отправить")
        self.fields["comment"].label = _("Комментарий для исполнителя")


class ShipmentTaskItemForm(forms.ModelForm):
    class Meta:
        model = ShipmentTaskItem
        fields = ["product", "quantity"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].label = _("Что отправить")
        self.fields["quantity"].label = _("Количество")


ShipmentTaskItemFormSet = forms.inlineformset_factory(
    ShipmentTask,
    ShipmentTaskItem,
    form=ShipmentTaskItemForm,
    extra=3,
    min_num=1,
    validate_min=True,
    can_delete=True,
)
