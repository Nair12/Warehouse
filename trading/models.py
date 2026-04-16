from django.db import models
from django.conf import settings


class Trading(models.Model):
    class TradeType(models.TextChoices):
        SELL = "sell", "Sell"
        PURCHASE = "purchase", "Purchase"

    trade_type = models.CharField(
        max_length=20,
        choices=TradeType.choices,
        verbose_name="Тип операции"
    )

    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='trades',
        verbose_name="Товар"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trades',
        verbose_name="Пользователь"
    )

    quantity = models.IntegerField(verbose_name="Количество")

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время операции")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    def __str__(self):
        return f"{self.trade_type} - {self.product} - {self.quantity}"


from django.db import models

# Create your models here.
