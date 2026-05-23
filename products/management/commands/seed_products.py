import random
import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Inventory
# Предполагаем, что модель Warehouse находится по этому пути:
from warehouses.models import Warehouse


class Command(BaseCommand):
    help = "Заполняет базу данных автозапчастями на основе 15 технических шаблонов"

    def add_arguments(self, parser):
        parser.add_argument(
            "-c",
            "--count",
            type=int,
            default=15,
            help="Количество автозапчастей, которое нужно создать",
        )

    def handle(self, *args, **options):
        count = options["count"]

        warehouses = list(Warehouse.objects.all())
        if not warehouses:
            self.stdout.write(
                self.style.WARNING(
                    "В базе нет складов (Warehouse). Запчасти будут созданы без остатков в Inventory."
                )
            )

        # 15 шаблонов автозапчастей с двуязычными комментариями в описании
        templates = [
            {"base_code": "15604-23ЮН", "desc": "Bearing / Подшипник ступицы", "unit": Product.UNIT_PIECE},
            {"base_code": "43211-12АБ", "desc": "Brake Pad / Колодка тормозная передняя", "unit": Product.UNIT_PIECE},
            {"base_code": "77301-89ВГ", "desc": "Oil Filter / Фильтр масляный ДВС", "unit": Product.UNIT_PIECE},
            {"base_code": "90919-02ДК", "desc": "Spark Plug / Свеча зажигания", "unit": Product.UNIT_PIECE},
            {"base_code": "31210-45ЕЖ", "desc": "Clutch Disc / Диск сцепления ведомый", "unit": Product.UNIT_PIECE},
            {"base_code": "48157-30ЗИ", "desc": "Shock Absorber / Амортизатор подвески", "unit": Product.UNIT_PIECE},
            {"base_code": "16100-11КЛ", "desc": "Water Pump / Насос водяной (помпа)", "unit": Product.UNIT_PIECE},
            {"base_code": "23300-54МН", "desc": "Fuel Filter / Фильтр топливный тонкой очистки",
             "unit": Product.UNIT_PIECE},
            {"base_code": "52119-22ОП", "desc": "Bumper Bracket / Кронштейн бампера", "unit": Product.UNIT_PIECE},
            {"base_code": "81110-67РС", "desc": "Headlight Assembly / Фара головного света в сборе",
             "unit": Product.UNIT_PIECE},
            {"base_code": "13568-90ТУ", "desc": "Timing Belt / Ремень ГРМ зубчатый", "unit": Product.UNIT_PIECE},
            {"base_code": "45046-15ФХ", "desc": "Tie Rod End / Наконечник рулевой тяги", "unit": Product.UNIT_PIECE},
            {"base_code": "28100-33ЦЧ", "desc": "Starter Motor / Стартер электрический ДВС",
             "unit": Product.UNIT_PIECE},
            {"base_code": "64461-77ШЩ", "desc": "Gasket / Прокладка ГБЦ металлическая", "unit": Product.UNIT_PIECE},
            {"base_code": "87139-50ЭЮ", "desc": "Cabin Air Filter / Фильтр салонный угольный",
             "unit": Product.UNIT_PIECE},
        ]

        products_to_create = []
        self.stdout.write(f"Начало генерации {count} автозапчастей...")

        with transaction.atomic():
            for i in range(count):

                template = templates[i % len(templates)]


                random_suffix = random.randint(1000, 9999)
                sku_name = f"{template['base_code']}{random_suffix}"


                extra_desc = f" (Batch #{i // len(templates) + 1})" if i >= len(templates) else ""
                full_desc = f"{template['desc']}{extra_desc}"

                product = Product(
                    name=sku_name,
                    description=full_desc,
                    unit=template['unit'],
                    user_id=uuid.uuid4()
                )
                products_to_create.append(product)

            # Сохраняем продукты в базу одним быстрым запросом
            created_products = Product.objects.bulk_create(products_to_create)

            # Привязываем к случайным складам, если склады существуют
            if warehouses:
                inventory_to_create = []
                for product in created_products:
                    sampled_warehouses = random.sample(warehouses, random.randint(1, len(warehouses)))
                    for warehouse in sampled_warehouses:
                        inventory_to_create.append(
                            Inventory(
                                product=product,
                                warehouse=warehouse,
                                quantity=random.randint(10, 150)  # Случайное кол-во запчастей на складе
                            )
                        )
                Inventory.objects.bulk_create(inventory_to_create)

        self.stdout.write(self.style.SUCCESS(f"Успешно добавлено продуктов: {count}"))