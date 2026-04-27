from django import forms
from django.forms import inlineformset_factory

from .models import Trading, TradingItem, TradingAttachment


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
            })
        }

        labels = {
            'name': 'Название сделки',
            'trade_type': 'Тип операции',
            'comment': 'Комментарий',
        }


class TradingItemForm(forms.ModelForm):
    class Meta:
        model = TradingItem
        fields = ['product', 'warehouse', 'requested_quantity', 'fulfilled_quantity']

        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control'
            }),
            'warehouse': forms.Select(attrs={
                'class': 'form-control'
            }),
            'requested_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Сколько заказано'
            }),
            'fulfilled_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Сколько выполнено сейчас',
                'value': 0
            }),
        }

        labels = {
            'product': 'Товар',
            'warehouse': 'Склад',
            'requested_quantity': 'Заказано',
            'fulfilled_quantity': 'Выполнено',
        }

TradingItemFormSet = inlineformset_factory(
    Trading,
    TradingItem,
    form=TradingItemForm,
    extra=1,
    can_delete=True
)


class TradingAttachmentForm(forms.ModelForm):
    class Meta:
        model = TradingAttachment
        fields = ['file']

        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }

        labels = {
            'file': 'Файл',
        }


AttachmentFormSet = inlineformset_factory(
    Trading,
    TradingAttachment,
    form=TradingAttachmentForm,
    extra=3,
    can_delete=True
)