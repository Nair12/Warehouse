from django import forms
from .models import Warehouse

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['city']
        widgets = {
            'city': forms.TextInput(attrs={'placeholder': 'Введите город склада'}),
        }
