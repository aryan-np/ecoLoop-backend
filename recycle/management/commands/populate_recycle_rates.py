from django.core.management.base import BaseCommand
from recycle.models import ScrapCategory


class Command(BaseCommand):
    help = "Populate initial scrap categories for recyclable materials"

    def handle(self, *args, **options):
        # Scrap rates data (rates per kg in your currency)
        scrap_rates_data = [
            {
                "material_type": "Plastic (PET)",
                "rate_per_kg": 15.00,
                "description": "Clear plastic bottles and containers (PET/PETE #1)",
            },
            {
                "material_type": "Plastic (HDPE)",
                "rate_per_kg": 18.00,
                "description": "High-density polyethylene - milk jugs, detergent bottles (#2)",
            },
            {
                "material_type": "Plastic (Mixed)",
                "rate_per_kg": 10.00,
                "description": "Mixed plastic types (#3-7)",
            },
            {
                "material_type": "Paper (Newspaper)",
                "rate_per_kg": 8.00,
                "description": "Old newspapers and newsprint",
            },
            {
                "material_type": "Paper (Cardboard)",
                "rate_per_kg": 12.00,
                "description": "Corrugated cardboard boxes",
            },
            {
                "material_type": "Paper (White Paper)",
                "rate_per_kg": 14.00,
                "description": "Office paper, printer paper, notebooks",
            },
            {
                "material_type": "Paper (Mixed)",
                "rate_per_kg": 6.00,
                "description": "Mixed paper and magazines",
            },
            {
                "material_type": "Glass (Clear)",
                "rate_per_kg": 5.00,
                "description": "Clear glass bottles and jars",
            },
            {
                "material_type": "Glass (Colored)",
                "rate_per_kg": 4.00,
                "description": "Brown, green, and colored glass",
            },
            {
                "material_type": "Aluminum",
                "rate_per_kg": 85.00,
                "description": "Aluminum cans, foil, and scrap",
            },
            {
                "material_type": "Steel/Tin Cans",
                "rate_per_kg": 25.00,
                "description": "Food cans, tin containers",
            },
            {
                "material_type": "Copper",
                "rate_per_kg": 650.00,
                "description": "Copper wire, pipes, and scrap",
            },
            {
                "material_type": "Brass",
                "rate_per_kg": 350.00,
                "description": "Brass fittings, fixtures, and scrap",
            },
            {
                "material_type": "Iron/Steel Scrap",
                "rate_per_kg": 20.00,
                "description": "Heavy iron and steel scrap metal",
            },
            {
                "material_type": "E-Waste (Computers)",
                "rate_per_kg": 45.00,
                "description": "Computer parts, motherboards, CPUs",
            },
            {
                "material_type": "E-Waste (Mobile Phones)",
                "rate_per_kg": 120.00,
                "description": "Old mobile phones and smartphones",
            },
            {
                "material_type": "E-Waste (General)",
                "rate_per_kg": 30.00,
                "description": "General electronic waste and components",
            },
            {
                "material_type": "Batteries (Lead-Acid)",
                "rate_per_kg": 55.00,
                "description": "Car batteries and UPS batteries",
            },
            {
                "material_type": "Batteries (Other)",
                "rate_per_kg": 40.00,
                "description": "Rechargeable and other battery types",
            },
            {
                "material_type": "Textiles",
                "rate_per_kg": 7.00,
                "description": "Old clothes, fabric, and textile waste",
            },
        ]

        # Create scrap rates
        created_rates = 0
        updated_rates = 0

        for rate_data in scrap_rates_data:
            rate, created = ScrapCategory.objects.get_or_create(
                material_type=rate_data["material_type"],
                defaults={
                    "rate_per_kg": rate_data["rate_per_kg"],
                    "description": rate_data["description"],
                },
            )
            if created:
                created_rates += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created rate: "{rate.material_type}" - Rs.{rate.rate_per_kg}/kg'
                    )
                )
            else:
                # Update existing rate if different
                if (
                    rate.rate_per_kg != rate_data["rate_per_kg"]
                    or rate.description != rate_data["description"]
                ):
                    rate.rate_per_kg = rate_data["rate_per_kg"]
                    rate.description = rate_data["description"]
                    rate.save()
                    updated_rates += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'↻ Updated rate: "{rate.material_type}" - Rs.{rate.rate_per_kg}/kg'
                        )
                    )
                else:
                    self.stdout.write(
                        f'- Rate already exists: "{rate.material_type}" - Rs.{rate.rate_per_kg}/kg'
                    )

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Created {created_rates} new categories, updated {updated_rates} existing categories"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Total scrap categories in database: {ScrapCategory.objects.count()}"
            )
        )
