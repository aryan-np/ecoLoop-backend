from django.core.management.base import BaseCommand
from donations.models import DonationCategory, DonationCondition


class Command(BaseCommand):
    help = "Populate initial donation categories and conditions"

    def handle(self, *args, **options):
        # Categories data
        categories_data = [
            {
                "name": "Clothes",
                "description": "Clothing items, shoes, and accessories",
            },
            {
                "name": "Books",
                "description": "Books, magazines, and educational materials",
            },
            {
                "name": "Electronics",
                "description": "Electronic devices, gadgets, and appliances",
            },
            {
                "name": "Household Items",
                "description": "Furniture, kitchenware, and home decor",
            },
            {
                "name": "Other",
                "description": "Miscellaneous items not fitting other categories",
            },
        ]

        # Conditions data
        conditions_data = [
            {
                "name": "Good",
                "description": "Item is in excellent condition, like new or gently used",
            },
            {
                "name": "Usable",
                "description": "Item is functional with minor wear and tear",
            },
            {
                "name": "Need Maintenance",
                "description": "Item requires repair or maintenance but is repairable",
            },
        ]

        # Create categories
        created_categories = 0
        updated_categories = 0

        for category_data in categories_data:
            category, created = DonationCategory.objects.get_or_create(
                name=category_data["name"],
                defaults={"description": category_data["description"]},
            )
            if created:
                created_categories += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created category: "{category.name}"')
                )
            else:
                # Update description if different
                if category.description != category_data["description"]:
                    category.description = category_data["description"]
                    category.save()
                    updated_categories += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Updated category: "{category.name}"')
                    )
                else:
                    self.stdout.write(f'- Category already exists: "{category.name}"')

        # Create conditions
        created_conditions = 0
        updated_conditions = 0

        for condition_data in conditions_data:
            condition, created = DonationCondition.objects.get_or_create(
                name=condition_data["name"],
                defaults={"description": condition_data["description"]},
            )
            if created:
                created_conditions += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created condition: "{condition.name}"')
                )
            else:
                # Update description if different
                if condition.description != condition_data["description"]:
                    condition.description = condition_data["description"]
                    condition.save()
                    updated_conditions += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Updated condition: "{condition.name}"')
                    )
                else:
                    self.stdout.write(f'- Condition already exists: "{condition.name}"')

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Created {created_categories} new categories, updated {updated_categories} existing categories"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Created {created_conditions} new conditions, updated {updated_conditions} existing conditions"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Total in database: {DonationCategory.objects.count()} categories, {DonationCondition.objects.count()} conditions"
            )
        )
