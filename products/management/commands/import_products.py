import csv
from pathlib import Path
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from products.models import Product


class Command(BaseCommand):
    help = "Import products from CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])

        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            required_columns = {"name", "price", "description", "unit"}
            if not required_columns.issubset(reader.fieldnames or []):
                raise CommandError(
                    "CSV must contain columns: name, price, description, unit"
                )

            for row in reader:
                name = (row.get("name") or "").strip()
                price_raw = (row.get("price") or "").strip()
                description = (row.get("description") or "").strip()
                unit = (row.get("unit") or "").strip()

                if not name:
                    skipped_count += 1
                    continue

                if unit not in ["pcs", "kg"]:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped {name}: unit must be pcs or kg"
                        )
                    )
                    skipped_count += 1
                    continue

                try:
                    price = Decimal(price_raw)
                except Exception:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped {name}: invalid price {price_raw}"
                        )
                    )
                    skipped_count += 1
                    continue

                product, created = Product.objects.update_or_create(
                    name=name,
                    defaults={
                        "price": price,
                        "description": description,
                        "unit": unit,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed. Created: {created_count}, updated: {updated_count}, skipped: {skipped_count}"
            )
        )
