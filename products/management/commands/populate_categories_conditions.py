from django.core.management.base import BaseCommand
from products.models import Category, Condition


class Command(BaseCommand):
    help = "Populate initial categories and conditions for products"

    def handle(self, *args, **options):
        # Categories
        categories_data = [
            {
                "name": "Electronics",
                "description": "Electronic devices and gadgets",
            },
            {
                "name": "Furniture",
                "description": "Furniture and home decor",
            },
            {
                "name": "Clothing",
                "description": "Clothes, shoes, and accessories",
            },
            {
                "name": "Books",
                "description": "Books and educational materials",
            },
            {
                "name": "Sports",
                "description": "Sports equipment and gear",
            },
            {
                "name": "Toys",
                "description": "Toys and games",
            },
            {
                "name": "Home Appliances",
                "description": "Kitchen and household appliances",
            },
            {
                "name": "Beauty & Personal Care",
                "description": "Beauty products and personal care items",
            },
        ]

        # Conditions
        conditions_data = [
            {
                "name": "Like New",
                "description": "Barely used, looks new",
            },
            {
                "name": "Fair",
                "description": "Used but in good condition",
            },
            {
                "name": "Good",
                "description": "Minor wear and tear",
            },
            {
                "name": "Damaged",
                "description": "Significant damage but still functional",
            },
        ]

        # Create categories
        created_categories = 0
        for category_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=category_data["name"],
                defaults={"description": category_data["description"]},
            )
            if created:
                created_categories += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created category: "{category.name}"')
                )
            else:
                self.stdout.write(f'- Category already exists: "{category.name}"')

        # Create conditions
        created_conditions = 0
        for condition_data in conditions_data:
            condition, created = Condition.objects.get_or_create(
                name=condition_data["name"],
                defaults={"description": condition_data["description"]},
            )
            if created:
                created_conditions += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created condition: "{condition.name}"')
                )
            else:
                self.stdout.write(f'- Condition already exists: "{condition.name}"')

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Created {created_categories} categories and {created_conditions} conditions"
            )
        )
        self.stdout.write("=" * 50)
