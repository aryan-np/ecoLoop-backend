import os

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from accounts.models import User
from donations.models import (
    DonationCategory,
    DonationCondition,
    DonationImage,
    DonationRequest,
)


class Command(BaseCommand):
    help = "Populate 5 donation requests for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner-id",
            type=str,
            default="9b4b4bbe-6f29-484f-86a9-1e2ac8f90d49",
            help="UUID of the user who will own seeded donation requests.",
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

        try:
            clothes = DonationCategory.objects.get(name="Clothes")
            books = DonationCategory.objects.get(name="Books")
            electronics = DonationCategory.objects.get(name="Electronics")
            household = DonationCategory.objects.get(name="Household Items")
            other = DonationCategory.objects.get(name="Other")

            good = DonationCondition.objects.get(name="Good")
            usable = DonationCondition.objects.get(name="Usable")
            maintenance = DonationCondition.objects.get(name="Need Maintenance")
        except (DonationCategory.DoesNotExist, DonationCondition.DoesNotExist):
            self.stdout.write(
                self.style.ERROR(
                    "Donation categories or conditions not found. Run populate_donations first."
                )
            )
            return

        donations_data = [
            {
                "category": clothes,
                "condition": good,
                "quantity": "8 shirts and 3 jeans",
                "notes": "Clean and packed in two bags.",
                "pickup_address": "Kathmandu, Baneshwor",
                "latitude": 27.690000,
                "longitude": 85.340000,
            },
            {
                "category": books,
                "condition": usable,
                "quantity": "25 school books",
                "notes": "Includes grade 8 and 9 science books.",
                "pickup_address": "Lalitpur, Jawalakhel",
                "latitude": 27.671000,
                "longitude": 85.313000,
            },
            {
                "category": electronics,
                "condition": maintenance,
                "quantity": "2 old laptops",
                "notes": "Need battery replacement but power on.",
                "pickup_address": "Bhaktapur, Suryabinayak",
                "latitude": 27.673000,
                "longitude": 85.429000,
            },
            {
                "category": household,
                "condition": good,
                "quantity": "Kitchen utensils set",
                "notes": "Steel utensils in good condition.",
                "pickup_address": "Kathmandu, Kalanki",
                "latitude": 27.694000,
                "longitude": 85.281000,
            },
            {
                "category": other,
                "condition": usable,
                "quantity": "Assorted toys",
                "notes": "Soft toys and board games.",
                "pickup_address": "Kirtipur, Chobhar",
                "latitude": 27.658000,
                "longitude": 85.292000,
            },
        ]

        created_count = 0
        images_attached_count = 0

        for donation_data in donations_data:
            donation, created = DonationRequest.objects.get_or_create(
                user=owner,
                category=donation_data["category"],
                quantity=donation_data["quantity"],
                pickup_address=donation_data["pickup_address"],
                defaults={
                    "condition": donation_data["condition"],
                    "notes": donation_data["notes"],
                    "latitude": donation_data["latitude"],
                    "longitude": donation_data["longitude"],
                    "status": "pending",
                },
            )

            if not donation.images.exists():
                with open(image_path, "rb") as image_file:
                    DonationImage.objects.create(
                        donation=donation,
                        image=File(image_file, name="image.png"),
                    )
                images_attached_count += 1

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created donation request: {donation.id}")
                )
            else:
                self.stdout.write(f"- Donation request already exists: {donation.id}")

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} donation requests")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Attached {images_attached_count} donation images")
        )
        self.stdout.write("=" * 50)
