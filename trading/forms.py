# trading/forms.py

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from .models import Trading, TradingItem, TradingAttachment, TradingComment


class TradingForm(forms.ModelForm):
    class Meta:
        model = Trading
        fields = ['name', 'trade_type', 'comment']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Введите название сделки'),
            }),
            'trade_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Комментарий (необязательно)'),
            }),
        }

        labels = {
            'name': _('Название сделки'),
            'trade_type': _('Тип операции'),
            'comment': _('Комментарий'),
        }


class TradingItemForm(forms.ModelForm):
    class Meta:
        model = TradingItem
        fields = ['product', 'warehouse', 'requested_quantity', 'fulfilled_quantity']

        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control',
            }),
            'warehouse': forms.Select(attrs={
                'class': 'form-control',
            }),
            'requested_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'step': '1',
                'placeholder': _('Сколько заказано'),
            }),
            'fulfilled_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '1',
                'placeholder': _('Сколько выполнено сейчас'),
                'value': 0,
            }),
        }

        labels = {
            'product': _('Товар'),
            'warehouse': _('Склад'),
            'requested_quantity': _('Заказано'),
            'fulfilled_quantity': _('Выполнено'),
        }

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get('product')
        requested_quantity = cleaned_data.get('requested_quantity')
        fulfilled_quantity = cleaned_data.get('fulfilled_quantity')

        if not product:
            return cleaned_data

        if product.unit == product.UNIT_PIECE:
            if requested_quantity is not None and requested_quantity != int(requested_quantity):
                self.add_error(
                    'requested_quantity',
                    _('Для товара в штуках нельзя вводить дробное количество.'),
                )

            if fulfilled_quantity is not None and fulfilled_quantity != int(fulfilled_quantity):
                self.add_error(
                    'fulfilled_quantity',
                    _('Для товара в штуках нельзя вводить дробное количество.'),
                )

        return cleaned_data


TradingItemFormSet = inlineformset_factory(
    Trading,
    TradingItem,
    form=TradingItemForm,
    extra=1,
    can_delete=True,
)


class TradingAttachmentForm(forms.ModelForm):
    class Meta:
        model = TradingAttachment
        fields = ['file']

        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
        }

        labels = {
            'file': _('Файл'),
        }


AttachmentFormSet = inlineformset_factory(
    Trading,
    TradingAttachment,
    form=TradingAttachmentForm,
    extra=3,
    can_delete=True,
)


class TradingCommentForm(forms.ModelForm):
    class Meta:
        model = TradingComment
        fields = ['text']

        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Напишите комментарий...'),
            }),
        }

        labels = {
            'text': _('Комментарий'),
        }
