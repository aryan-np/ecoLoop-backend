from decimal import Decimal

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from ecoLoop.management_seed_utils import get_seed_image_path, get_user_from_authorization
from products.models import Category, Condition, Product, ProductImage


class Command(BaseCommand):
    help = "Create 5 sample marketplace products for the user resolved from an authorization token."

    def add_arguments(self, parser):
        parser.add_argument(
            "--authorization",
            type=str,
            required=True,
            help="JWT access token or 'Bearer <token>' for the product owner.",
        )

    def handle(self, *args, **options):
        user = get_user_from_authorization(options["authorization"])
        image_path = get_seed_image_path()
        suffix = timezone.now().strftime("%Y%m%d%H%M%S")

        categories = self._ensure_categories()
        conditions = self._ensure_conditions()

        products_data = [
            {
                "title": f"Study Desk {suffix}-1",
                "description": "Compact wooden study desk suitable for student rooms.",
                "category": categories["Furniture"],
                "condition": conditions["Good"],
                "price": Decimal("6500.00"),
                "location": "Kathmandu, Baneshwor",
            },
            {
                "title": f"Used Laptop Bag {suffix}-2",
                "description": "Water-resistant laptop bag with padded compartments.",
                "category": categories["Accessories"],
                "condition": conditions["Like New"],
                "price": Decimal("1200.00"),
                "location": "Lalitpur, Jawalakhel",
            },
            {
                "title": f"Rice Cooker {suffix}-3",
                "description": "Working rice cooker, ideal for hostel or apartment use.",
                "category": categories["Home Appliances"],
                "condition": conditions["Fair"],
                "price": Decimal("1800.00"),
                "location": "Bhaktapur, Thimi",
            },
            {
                "title": f"Android Phone {suffix}-4",
                "description": "Second-hand Android phone with charger and back cover.",
                "category": categories["Electronics"],
                "condition": conditions["Good"],
                "price": Decimal("9500.00"),
                "location": "Kathmandu, Kalanki",
            },
            {
                "title": f"Winter Jacket {suffix}-5",
                "description": "Warm winter jacket in clean condition, suitable for reuse.",
                "category": categories["Clothing"],
                "condition": conditions["Like New"],
                "price": Decimal("2200.00"),
                "location": "Kirtipur, Balkhu",
            },
        ]

        created_products = []
        for item in products_data:
            product = Product.objects.create(
                owner=user,
                title=item["title"],
                description=item["description"],
                category=item["category"],
                condition=item["condition"],
                price=item["price"],
                location=item["location"],
                status="available",
                is_active=True,
            )
            created_products.append(product)

            if image_path:
                with image_path.open("rb") as image_file:
                    ProductImage.objects.create(
                        product=product,
                        image=File(image_file, name=f"{product.id}.png"),
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(created_products)} products for {user.email}."
            )
        )
        for product in created_products:
            self.stdout.write(f"- {product.title} ({product.id})")

    def _ensure_categories(self):
        data = {
            "Electronics": "Electronic devices and gadgets.",
            "Furniture": "Furniture and reusable home items.",
            "Clothing": "Wearable clothing and apparel.",
            "Home Appliances": "Kitchen and household appliances.",
            "Accessories": "Bags, cases, and daily-use accessories.",
        }
        categories = {}
        for name, description in data.items():
            category, _ = Category.objects.get_or_create(
                name=name,
                defaults={"description": description, "is_active": True},
            )
            if not category.is_active:
                category.is_active = True
                category.save(update_fields=["is_active"])
            categories[name] = category
        return categories

    def _ensure_conditions(self):
        data = {
            "Like New": "Barely used and in excellent condition.",
            "Good": "Used with minor wear and tear.",
            "Fair": "Functional with visible signs of use.",
        }
        conditions = {}
        for name, description in data.items():
            condition, _ = Condition.objects.get_or_create(
                name=name,
                defaults={"description": description, "is_active": True},
            )
            if not condition.is_active:
                condition.is_active = True
                condition.save(update_fields=["is_active"])
            conditions[name] = condition
        return conditions
