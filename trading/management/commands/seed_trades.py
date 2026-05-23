import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

# Настрой импорты под реальную структуру своих приложений
from products.models import Product
from warehouses.models import Warehouse
from trading.models import Trading, TradingItem, TradingComment, TradingAuditLog

User = get_user_model()


class Command(BaseCommand):
    help = "Генерирует случайные сделки и привязывает их к существующим товарам"

    def add_arguments(self, parser):
        parser.add_argument(
            "-c",
            "--count",
            type=int,
            default=10,
            help="Количество сделок для генерации",
        )

    def handle(self, *args, **options):
        count = options["count"]

        # 1. Загружаем пулы существующих данных для связывания
        product_pool = list(Product.objects.all())
        warehouse_pool = list(Warehouse.objects.all())
        user_pool = list(User.objects.all())

        # Проверки на то, что база не пустая
        if not product_pool:
            self.stdout.write(self.style.ERROR("Сначала наполни базу продуктами через скрипт seed_products!"))
            return
        if not warehouse_pool:
            self.stdout.write(self.style.ERROR("В базе нет ни одного склада. Сделки не к чему привязать."))
            return
        if not user_pool:
            self.stdout.write(self.style.ERROR("Нет пользователей. Создай хотя бы одного юзера/админа."))
            return

        # Реалистичные заготовки для названий
        purchase_names = [
            "Поставка расходников", "Импорт: Партия запчастей",
            "Закупка тормозных систем", "Пополнение остатков (Опт)"
        ]
        sell_names = [
            "Отгрузка для СТО 'Интер'", "Заказ клиента",
            "Реализация: Розничная сеть", "Договор поставки"
        ]

        self.stdout.write(f"Начинаем генерацию {count} сделок...")

        # Оборачиваем всё в транзакцию
        with transaction.atomic():
            for i in range(count):
                trade_type = random.choice([Trading.TradeType.PURCHASE, Trading.TradeType.SELL])
                status = random.choice([Trading.Status.PENDING, Trading.Status.COMPLETED])
                user = random.choice(user_pool)

                # Выбираем имя и добавляем случайный номер
                base_name = random.choice(purchase_names if trade_type == Trading.TradeType.PURCHASE else sell_names)
                trade_name = f"{base_name} #{random.randint(1000, 9999)}"

                # Выбираем один случайный склад и продукт для старых полей (для обратной совместимости)
                legacy_product = random.choice(product_pool)
                legacy_warehouse = random.choice(warehouse_pool)

                # Шаг 2: Создаем родительский объект сделки
                trading = Trading.objects.create(
                    name=trade_name,
                    trade_type=trade_type,
                    status=status,
                    user=user,
                    comment="Сгенерировано автоматически сид-скриптом.",
                    product=legacy_product,  # Legacy-совместимость
                    warehouse=legacy_warehouse,  # Legacy-совместимость
                )

                # Имитируем дату создания в прошлом (чтобы проверить свойства can_be_modified)
                if random.random() > 0.5:
                    trading.created_at = timezone.now() - timedelta(hours=random.randint(2, 36))
                    trading.save()

                # Шаг 3: Привязываем товары через TradingItem
                # Выбираем от 1 до 4 случайных уникальных продуктов из пула
                items_count = random.randint(1, min(4, len(product_pool)))
                selected_products = random.sample(product_pool, items_count)

                for product in selected_products:
                    # Для каждой позиции выбираем случайный склад отгрузки/приемки
                    warehouse = random.choice(warehouse_pool)

                    requested = random.randint(10, 150)

                    # Логика заполнения в зависимости от статуса сделки
                    if status == Trading.Status.COMPLETED:
                        fulfilled = requested
                        quantity = requested
                    else:
                        # Если сделка PENDING, она может быть "Ожидает" или быть "Частично выполнена"
                        fulfilled = random.choice([0, random.randint(1, requested - 1)])
                        quantity = fulfilled

                    # Симулируем расчет остатков до и после операции
                    qty_before = random.randint(200, 2000)
                    if trade_type == Trading.TradeType.PURCHASE:
                        qty_after = qty_before + quantity
                    else:
                        qty_after = qty_before - quantity

                    # Создаем дочернюю позицию, передавая инстансы trading и product
                    TradingItem.objects.create(
                        trading=trading,
                        product=product,
                        warehouse=warehouse,
                        requested_quantity=requested,
                        fulfilled_quantity=fulfilled,
                        quantity=quantity,
                        quantity_before=qty_before,
                        quantity_after=qty_after
                    )

                # Шаг 4: Генерируем сопутствующий системный аудит-лог
                TradingAuditLog.objects.create(
                    trading=trading,
                    trading_id_snapshot=trading.id,
                    user=user,
                    action=TradingAuditLog.Action.CREATED,
                    description=f"Сделка {trade_name} успешно создана системой генерации тестовых данных.",
                )

                # Иногда добавляем случайный комментарий пользователя
                if random.random() > 0.6:
                    TradingComment.objects.create(
                        trading=trading,
                        user=random.choice(user_pool),
                        text="Уточнить время прибытия курьера на погрузку."
                    )

        self.stdout.write(self.style.SUCCESS(f"Успешно сгенерировано сделок: {count}"))