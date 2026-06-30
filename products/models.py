import re
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def normalize_product_code(value):
    """
    Безопасная нормализация чертежного номера.

    Автоматически игнорируем только разделители:
    пробелы, дефисы, точки, слэши и другие символы.

    Нули внутри номера НЕ удаляем.
    Нули в начале убираем только для базового поиска,
    но спорные случаи с нулями лучше отправлять на ручную проверку.

    Примеры:
    012-60226 -> 1260226
    001260226 -> 1260226
    01260226 != 10260226
    """
    if not value:
        return ""

    value = str(value).strip().upper()

    # Оставляем только буквы и цифры.
    value = re.sub(r"[^A-ZА-ЯЁ0-9]", "", value)

    # Убираем только ведущие нули.
    value = value.lstrip("0") or "0"

    return value


class Product(models.Model):
    UNIT_PIECE = "pcs"
    UNIT_KG = "kg"

    UNIT_CHOICES = (
        (UNIT_PIECE, _("шт")),
        (UNIT_KG, _("кг")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Основной код / чертежный номер товара
    name = models.CharField(max_length=255)

    # Очищенный код для поиска дублей
    normalized_code = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name=_("Нормализованный код"),
    )

    # Описание: русское название / английское название
    description = models.TextField(blank=True, null=True)

    picture = models.ImageField(upload_to="products/", blank=True, null=True)

    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default=UNIT_PIECE,
        verbose_name=_("Единица измерения"),
    )

    user_id = models.UUIDField(blank=True, null=True)

    warehouses = models.ManyToManyField(
        "warehouses.Warehouse",
        through="products.Inventory",
        related_name="products",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.normalized_code = normalize_product_code(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Inventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )

    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )

    quantity = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                name="unique_product_warehouse",
            )
        ]

    def __str__(self):
        return f"{self.product} @ {self.warehouse}: {self.quantity}"


class ProductImportBatch(models.Model):
    IMPORT_TYPE_PRODUCTS_ONLY = "products_only"
    IMPORT_TYPE_PRODUCTS_WITH_STOCK = "products_with_stock"

    IMPORT_TYPE_CHOICES = (
        (IMPORT_TYPE_PRODUCTS_ONLY, _("Только товары")),
        (IMPORT_TYPE_PRODUCTS_WITH_STOCK, _("Товары + остатки на склад")),
    )

    QUANTITY_MODE_REPLACE = "replace"
    QUANTITY_MODE_ADD = "add"

    QUANTITY_MODE_CHOICES = (
        (QUANTITY_MODE_REPLACE, _("Заменить остатки на складе")),
        (QUANTITY_MODE_ADD, _("Прибавить к текущим остаткам")),
    )

    STATUS_DRAFT = "draft"
    STATUS_CHECKED = "checked"
    STATUS_IMPORTED = "imported"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_DRAFT, _("Черновик")),
        (STATUS_CHECKED, _("Проверен")),
        (STATUS_IMPORTED, _("Импортирован")),
        (STATUS_CANCELLED, _("Отменён")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(
        max_length=255,
        default=_("Импорт товаров"),
        verbose_name=_("Название импорта"),
    )

    file = models.FileField(
        upload_to="product_imports/",
        verbose_name=_("Excel файл"),
    )

    import_type = models.CharField(
        max_length=30,
        choices=IMPORT_TYPE_CHOICES,
        default=IMPORT_TYPE_PRODUCTS_ONLY,
        verbose_name=_("Тип импорта"),
    )

    target_warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="product_import_batches",
        verbose_name=_("Склад для остатков"),
    )

    quantity_mode = models.CharField(
        max_length=20,
        choices=QUANTITY_MODE_CHOICES,
        default=QUANTITY_MODE_REPLACE,
        verbose_name=_("Как обновлять количество"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name=_("Статус"),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="product_import_batches",
        verbose_name=_("Кто загрузил"),
    )

    total_rows = models.PositiveIntegerField(default=0)
    existing_count = models.PositiveIntegerField(default=0)
    similar_code_count = models.PositiveIntegerField(default=0)
    similar_name_count = models.PositiveIntegerField(default=0)
    duplicate_in_file_count = models.PositiveIntegerField(default=0)
    new_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    quantity_error_count = models.PositiveIntegerField(default=0)

    created_products_count = models.PositiveIntegerField(default=0)
    updated_inventory_count = models.PositiveIntegerField(default=0)
    skipped_rows_count = models.PositiveIntegerField(default=0)
    linked_rows_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Импорт товаров")
        verbose_name_plural = _("Импорты товаров")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.created_at:%d.%m.%Y %H:%M}"

    @property
    def attention_count(self):
        return (
            self.similar_code_count
            + self.similar_name_count
            + self.duplicate_in_file_count
            + self.error_count
            + self.quantity_error_count
        )


class ProductImportRow(models.Model):
    STATUS_EXISTING = "existing"
    STATUS_SIMILAR_CODE = "similar_code"
    STATUS_SIMILAR_NAME = "similar_name"
    STATUS_DUPLICATE_IN_FILE = "duplicate_in_file"
    STATUS_NEW = "new"
    STATUS_ERROR = "error"
    STATUS_QUANTITY_ERROR = "quantity_error"

    STATUS_CHOICES = (
        (STATUS_EXISTING, _("Уже есть в базе")),
        (STATUS_SIMILAR_CODE, _("Похожий код")),
        (STATUS_SIMILAR_NAME, _("Похожее название")),
        (STATUS_DUPLICATE_IN_FILE, _("Дубль внутри Excel")),
        (STATUS_NEW, _("Новый товар")),
        (STATUS_ERROR, _("Ошибка")),
        (STATUS_QUANTITY_ERROR, _("Ошибка количества")),
    )

    ACTION_SKIP = "skip"
    ACTION_CREATE = "create"
    ACTION_LINK = "link"

    ACTION_CHOICES = (
        (ACTION_SKIP, _("Пропустить")),
        (ACTION_CREATE, _("Создать новый товар")),
        (ACTION_LINK, _("Привязать к существующему")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    batch = models.ForeignKey(
        ProductImportBatch,
        on_delete=models.CASCADE,
        related_name="rows",
        verbose_name=_("Импорт"),
    )

    row_number = models.PositiveIntegerField(verbose_name=_("Строка Excel"))

    raw_code = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Код из Excel"),
    )

    normalized_code = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name=_("Очищенный код"),
    )

    raw_name = models.TextField(
        blank=True,
        verbose_name=_("Название из Excel"),
    )

    raw_unit = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Единица из Excel"),
    )

    raw_quantity = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Количество из Excel"),
    )

    quantity = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Количество"),
    )

    detected_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        verbose_name=_("Что нашёл сайт"),
    )

    suggested_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="suggested_import_rows",
        verbose_name=_("Похожий товар в базе"),
    )

    selected_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="selected_import_rows",
        verbose_name=_("Выбранный товар"),
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        default=ACTION_SKIP,
        verbose_name=_("Решение админа"),
    )

    note = models.TextField(
        blank=True,
        verbose_name=_("Комментарий проверки"),
    )

    is_processed = models.BooleanField(
        default=False,
        verbose_name=_("Обработано"),
    )

    created_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_from_import_rows",
        verbose_name=_("Созданный товар"),
    )

    inventory_updated = models.BooleanField(
        default=False,
        verbose_name=_("Остаток обновлён"),
    )

    inventory_before = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Остаток был"),
    )

    inventory_after = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Остаток стал"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Строка импорта товаров")
        verbose_name_plural = _("Строки импорта товаров")
        ordering = ["batch", "row_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "row_number"],
                name="unique_product_import_batch_row",
            )
        ]

    def save(self, *args, **kwargs):
        self.normalized_code = normalize_product_code(self.raw_code)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.row_number}: {self.raw_code} — {self.get_detected_status_display()}"