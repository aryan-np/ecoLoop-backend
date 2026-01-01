from django.core.management.base import BaseCommand
from products.models import Product, Category, Condition
from accounts.models import User
import os


class Command(BaseCommand):
    help = "Populate initial products for testing"

    def handle(self, *args, **options):
        admin_id = "692f860d-aba2-47e0-aadd-a626cd4b056f"

        # Get admin user
        try:
            owner = User.objects.get(id=admin_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ User with id {admin_id} not found"))
            return

        # Check if logo.png exists
        image_path = "products/logo.png"
        if not os.path.exists(os.path.join("media", image_path)):
            self.stdout.write(
                self.style.WARNING(f"⚠ Image file not found at media/{image_path}")
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
        except Category.DoesNotExist or Condition.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "✗ Categories or Conditions not found. Run populate_categories_conditions first"
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
            {
                "title": "Sneaker Collection",
                "description": "Nike and Adidas sneakers, various sizes",
                "category": clothing,
                "condition": like_new,
                "price": 200.00,
                "location": "Austin, TX",
            },
            {
                "title": "Samsung 55-inch Smart TV",
                "description": "4K resolution, all streaming apps included",
                "category": electronics,
                "condition": good,
                "price": 400.00,
                "location": "Houston, TX",
            },
            {
                "title": "Coffee Table",
                "description": "Modern glass and wood coffee table",
                "category": furniture,
                "condition": like_new,
                "price": 180.00,
                "location": "Washington, DC",
            },
            {
                "title": "Casual Jeans Pack",
                "description": "5 pairs of casual jeans, mixed sizes",
                "category": clothing,
                "condition": good,
                "price": 100.00,
                "location": "Philadelphia, PA",
            },
            {
                "title": "Portable Bluetooth Speaker",
                "description": "Waterproof speaker, great battery life",
                "category": electronics,
                "condition": like_new,
                "price": 60.00,
                "location": "Las Vegas, NV",
            },
        ]

        created_count = 0
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
                    "image": image_path,
                    "product_type": "sell",
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f' Created product: "{product.title}"')
                )
            else:
                self.stdout.write(f'- Product already exists: "{product.title}"')

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f" Created {created_count} products"))
        self.stdout.write("=" * 50)
