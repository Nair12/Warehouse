# warehouses/forms.py

from django import forms
from .models import Warehouse, WarehouseTransfer
from products.models import Inventory


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['city']
        widgets = {
            'city': forms.TextInput(attrs={'placeholder': 'Введите город склада'}),
        }


class WarehouseTransferForm(forms.ModelForm):
    class Meta:
        model = WarehouseTransfer
        fields = ['product', 'from_warehouse', 'to_warehouse', 'quantity']

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get('product')
        from_warehouse = cleaned_data.get('from_warehouse')
        to_warehouse = cleaned_data.get('to_warehouse')
        quantity = cleaned_data.get('quantity')

        if from_warehouse == to_warehouse:
            raise forms.ValidationError("Склад отправки и получения не могут быть одинаковыми")

        if product and from_warehouse and quantity:
            try:
                inventory = Inventory.objects.get(
                    product=product,
                    warehouse=from_warehouse
                )
            except Inventory.DoesNotExist:
                raise forms.ValidationError("На складе-отправителе нет этого товара")

            if inventory.quantity < quantity:
                raise forms.ValidationError("Недостаточно товара на складе")

        return cleaned_data
