from django import forms
from .models import Trading


class TradingForm(forms.ModelForm):
    class Meta:
        model = Trading
        fields = ['product', 'warehouse', 'quantity', 'trade_type']

        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control'
            }),
            'warehouse': forms.Select(attrs={
                'class': 'form-control'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'trade_type': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

        labels = {
            'product': 'Продукт',
            'warehouse': 'Склад',
            'quantity': 'Количество',
            'trade_type': 'Тип операции',
        }