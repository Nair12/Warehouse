from django import forms
from .models import Trading


class TradingForm(forms.ModelForm):
    class Meta:
        model = Trading
        fields = ['name', 'product', 'warehouse', 'quantity', 'trade_type', 'comment']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название сделки'
            }),
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
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Комментарий (необязательно)'
            }),
        }

        labels = {
            'name': 'Название сделки',
            'product': 'Продукт',
            'warehouse': 'Склад',
            'quantity': 'Количество',
            'trade_type': 'Тип операции',
            'comment': 'Комментарий',
        }