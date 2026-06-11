from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path
from django import forms

from openpyxl import Workbook, load_workbook

from .models import Product, Inventory


class ProductImportExcelForm(forms.Form):
    excel_file = forms.FileField(label="Excel файл")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "id")
    search_fields = ("name", "description")
    list_filter = ("unit",)
    ordering = ("name",)

    change_list_template = "admin/products/product/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-excel/",
                self.admin_site.admin_view(self.import_excel),
                name="products_product_import_excel",
            ),
            path(
                "export-excel/",
                self.admin_site.admin_view(self.export_excel),
                name="products_product_export_excel",
            ),
        ]
        return custom_urls + urls

    def export_excel(self, request):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Products"

        sheet.append(["name", "description", "unit"])

        products = Product.objects.all().order_by("name")

        for product in products:
            sheet.append([
                product.name,
                product.description or "",
                product.unit,
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="products_export.xlsx"'

        workbook.save(response)
        return response

    def import_excel(self, request):
        if request.method == "POST":
            form = ProductImportExcelForm(request.POST, request.FILES)

            if form.is_valid():
                excel_file = request.FILES["excel_file"]

                try:
                    workbook = load_workbook(excel_file)
                    sheet = workbook.active

                    headers = [
                        str(cell.value).strip().lower() if cell.value else ""
                        for cell in sheet[1]
                    ]

                    required_headers = ["name", "description", "unit"]
                    missing_headers = [
                        header for header in required_headers
                        if header not in headers
                    ]

                    if missing_headers:
                        messages.error(
                            request,
                            "В Excel обязательно должны быть колонки: name, description, unit."
                        )
                        return redirect("..")

                    name_index = headers.index("name") + 1
                    description_index = headers.index("description") + 1
                    unit_index = headers.index("unit") + 1

                    allowed_units = [choice[0] for choice in Product.UNIT_CHOICES]

                    created_count = 0
                    skipped_duplicate_count = 0
                    skipped_empty_count = 0
                    skipped_invalid_unit_count = 0

                    for row_number in range(2, sheet.max_row + 1):
                        name = sheet.cell(row=row_number, column=name_index).value
                        description = sheet.cell(row=row_number, column=description_index).value
                        unit = sheet.cell(row=row_number, column=unit_index).value

                        if (
                            name is None or str(name).strip() == ""
                            or description is None or str(description).strip() == ""
                            or unit is None or str(unit).strip() == ""
                        ):
                            skipped_empty_count += 1
                            continue

                        name = str(name).strip()
                        description = str(description).strip()
                        unit = str(unit).strip().lower()

                        if unit in ["шт", "штук", "pcs", "pc"]:
                            unit = Product.UNIT_PIECE
                        elif unit in ["кг", "kg"]:
                            unit = Product.UNIT_KG

                        if unit not in allowed_units:
                            skipped_invalid_unit_count += 1
                            continue

                        if Product.objects.filter(name__iexact=name).exists():
                            skipped_duplicate_count += 1
                            continue

                        Product.objects.create(
                            name=name,
                            description=description,
                            unit=unit,
                        )
                        created_count += 1

                    messages.success(
                        request,
                        f"Импорт завершён. Создано: {created_count}. "
                        f"Пропущено дубликатов: {skipped_duplicate_count}. "
                        f"Пропущено строк с пустыми полями: {skipped_empty_count}. "
                        f"Пропущено строк с неправильной единицей: {skipped_invalid_unit_count}."
                    )

                    return redirect("..")

                except Exception as e:
                    messages.error(request, f"Ошибка импорта Excel: {e}")
                    return redirect("..")
        else:
            form = ProductImportExcelForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Импорт товаров из Excel",
            "form": form,
        }

        return render(request, "admin/products/product/import_excel.html", context)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("product_name", "warehouse_city", "quantity")
    search_fields = ("product__name", "warehouse__city")
    list_filter = ("warehouse__city",)
    ordering = ("warehouse__city", "product__name")

    @admin.display(description="Товар", ordering="product__name")
    def product_name(self, obj):
        return obj.product.name

    @admin.display(description="Город", ordering="warehouse__city")
    def warehouse_city(self, obj):
        return obj.warehouse.city