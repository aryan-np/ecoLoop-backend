from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from products.models import Product, ProductImage, Category, Condition
from accounts.models import User
import os


class Command(BaseCommand):
    help = "Populate initial products for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner-id",
            type=str,
            default="9b4b4bbe-6f29-484f-86a9-1e2ac8f90d49",
            help="UUID of the user who will own seeded products.",
        )

    def handle(self, *args, **options):
        owner_id = options["owner_id"]

        try:
            owner = User.objects.get(id=owner_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with UUID {owner_id} not found."))
            return

        image_path = os.path.join(settings.BASE_DIR, "image.png")
        if not os.path.exists(image_path):
            self.stdout.write(
                self.style.ERROR(f"Image file not found at project root: {image_path}.")
            )
            return

        # Get categories and conditions
        try:
            electronics = Category.objects.get(name="Electronics")
            furniture = Category.objects.get(name="Furniture")
            clothing = Category.objects.get(name="Clothing")

            like_new = Condition.objects.get(name="Like New")
            fair = Condition.objects.get(name="Fair")
            good = Condition.objects.get(name="Good")
        except (Category.DoesNotExist, Condition.DoesNotExist):
            self.stdout.write(
                self.style.ERROR(
                    "Categories or conditions not found. Run populate_categories_conditions first."
                )
            )
            return

        products_data = [
            {
                "title": "iPhone 13 Pro",
                "description": "Excellent condition, fully functional with box and accessories",
                "category": electronics,
                "condition": like_new,
                "price": 750.00,
                "location": "New York, NY",
            },
            {
                "title": "Wooden Dining Table",
                "description": "6-seater dining table in good condition",
                "category": furniture,
                "condition": good,
                "price": 300.00,
                "location": "Los Angeles, CA",
            },
            {
                "title": "Designer Winter Coat",
                "description": "Brand new, never worn, size M",
                "category": clothing,
                "condition": like_new,
                "price": 150.00,
                "location": "Chicago, IL",
            },
            {
                "title": "Vintage Camera",
                "description": "Working vintage camera with some cosmetic wear",
                "category": electronics,
                "condition": fair,
                "price": 120.00,
                "location": "Seattle, WA",
            },
            {
                "title": "Office Chair",
                "description": "Ergonomic office chair, lightly used",
                "category": furniture,
                "condition": good,
                "price": 200.00,
                "location": "Boston, MA",
            },
            {
                "title": "Sony Headphones",
                "description": "Noise-cancelling wireless headphones, barely used",
                "category": electronics,
                "condition": like_new,
                "price": 200.00,
                "location": "Denver, CO",
            },
            {
                "title": "Leather Sofa",
                "description": "Brown leather sofa, comfortable and spacious",
                "category": furniture,
                "condition": fair,
                "price": 400.00,
                "location": "Miami, FL",
            },
            {
                "title": "Summer Dress Collection",
                "description": "Bundle of 3 summer dresses, never worn",
                "category": clothing,
                "condition": like_new,
                "price": 80.00,
                "location": "Phoenix, AZ",
            },
            {
                "title": "MacBook Pro 15-inch",
                "description": "2019 model, excellent working condition",
                "category": electronics,
                "condition": good,
                "price": 900.00,
                "location": "San Francisco, CA",
            },
            {
                "title": "Bookshelf",
                "description": "Wooden bookshelf, 5 shelves, sturdy construction",
                "category": furniture,
                "condition": good,
                "price": 120.00,
                "location": "Portland, OR",
            },
        ]

        created_count = 0
        images_attached_count = 0
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                title=product_data["title"],
                owner=owner,
                defaults={
                    "description": product_data["description"],
                    "category": product_data["category"],
                    "condition": product_data["condition"],
                    "price": product_data["price"],
                    "location": product_data["location"],
                    "is_active": True,
                },
            )

            # Attach the same root image once per product if it has no image yet.
            if not product.images.exists():
                with open(image_path, "rb") as image_file:
                    ProductImage.objects.create(
                        product=product,
                        image=File(image_file, name="image.png"),
                    )
                images_attached_count += 1

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created product: "{product.title}"')
                )
            else:
                self.stdout.write(f'- Product already exists: "{product.title}"')

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} products"))
        self.stdout.write(
            self.style.SUCCESS(f"Attached {images_attached_count} images")
        )
        self.stdout.write("=" * 50)
