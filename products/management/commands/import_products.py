from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from products.models import Product


class Command(BaseCommand):
    help = "Robust import from broken CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    def handle(self, *args, **options):
        path = Path(options["csv_path"])

        if not path.exists():
            raise CommandError(f"File not found: {path}")

        created = 0
        skipped = 0

        with path.open("r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()

                if not line:
                    skipped += 1
                    continue

                # разбиваем по ; или ,
                raw_parts = []
                for part in line.replace(";", ",").split(","):
                    part = part.strip()
                    if part:
                        raw_parts.append(part)

                if not raw_parts:
                    skipped += 1
                    continue

                # ищем название (первое не число и не мусор)
                name = None
                for part in raw_parts:
                    if part.lower() in ["наименование", "подшипники"]:
                        name = None
                        break

                    # если не число → это товар
                    if not part.isdigit():
                        name = part
                        break

                if not name:
                    skipped += 1
                    continue

                if Product.objects.filter(name__iexact=name).exists():
                    skipped += 1
                    continue

                Product.objects.create(
                    name=name,
                    description="",
                    unit=Product.UNIT_PIECE,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Created: {created}, skipped: {skipped}"))
