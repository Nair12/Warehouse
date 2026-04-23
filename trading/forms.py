from django import forms
from django.forms import inlineformset_factory

from .models import Trading, TradingItem, TradingAttachment


class TradingForm(forms.ModelForm):
    class Meta:
        model = Trading
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

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')

        if quantity is None:
            return quantity

        if quantity <= 0:
            raise forms.ValidationError('Количество должно быть больше нуля.')

        return quantity
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
    extra=1,
    can_delete=True
)
