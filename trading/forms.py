from django import forms
from .models import Trading


class TradingForm(forms.ModelForm):
    class Meta:
        model = Trading
        fields = ['product', 'quantity', 'trade_type']  # user не даём выбирать

        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
        }

        labels = {
            'product': 'Продукт',
            'quantity': 'Количество',
        }