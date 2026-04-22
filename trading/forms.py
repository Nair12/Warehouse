from django import forms
from .models import Trading, TradingItem


class TradingForm(forms.ModelForm):
    class Meta:
        model = Trading
        # ❗ УБРАЛИ product, warehouse, quantity
        fields = ['name', 'trade_type', 'comment']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название сделки'
            }),
            'trade_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Комментарий (необязательно)'
            }),
        }

        labels = {
            'name': 'Название сделки',
            'trade_type': 'Тип операции',
            'comment': 'Комментарий',
        }


class TradingItemForm(forms.ModelForm):
    class Meta:
        model = TradingItem
        fields = ['product', 'warehouse', 'quantity']

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
        }

        labels = {
            'product': 'Товар',
            'warehouse': 'Склад',
            'quantity': 'Количество',
        }