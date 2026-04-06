import os

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from accounts.models import User
from recycle.models import ScrapCategory, ScrapImage, ScrapRequest


class Command(BaseCommand):
    help = "Populate 5 scrap requests for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner-id",
            type=str,
            default="9b4b4bbe-6f29-484f-86a9-1e2ac8f90d49",
            help="UUID of the user who will own seeded scrap requests.",
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

        categories = list(ScrapCategory.objects.order_by("id")[:5])
        if len(categories) < 5:
            self.stdout.write(
                self.style.ERROR(
                    "At least 5 scrap categories are required. Run populate_recycle_rates first."
                )
            )
            return

        scraps_data = [
            {
                "category": categories[0],
                "weight_kg": 12.50,
                "pickup_address": "Kathmandu, Maitighar",
                "preferred_time_slot": "morning",
                "condition": "clean",
                "latitude": 27.693000,
                "longitude": 85.324000,
            },
            {
                "category": categories[1],
                "weight_kg": 8.00,
                "pickup_address": "Lalitpur, Pulchowk",
                "preferred_time_slot": "afternoon",
                "condition": "mixed",
                "latitude": 27.678000,
                "longitude": 85.316000,
            },
            {
                "category": categories[2],
                "weight_kg": 5.75,
                "pickup_address": "Bhaktapur, Thimi",
                "preferred_time_slot": "evening",
                "condition": "clean",
                "latitude": 27.678500,
                "longitude": 85.395000,
            },
            {
                "category": categories[3],
                "weight_kg": 20.00,
                "pickup_address": "Kathmandu, New Baneshwor",
                "preferred_time_slot": "morning",
                "condition": "mixed",
                "latitude": 27.688000,
                "longitude": 85.336000,
            },
            {
                "category": categories[4],
                "weight_kg": 15.25,
                "pickup_address": "Kirtipur, Balkhu",
                "preferred_time_slot": "afternoon",
                "condition": "clean",
                "latitude": 27.680000,
                "longitude": 85.304000,
            },
        ]

        created_count = 0
        images_attached_count = 0

        for scrap_data in scraps_data:
            scrap, created = ScrapRequest.objects.get_or_create(
                user=owner,
                category=scrap_data["category"],
                weight_kg=scrap_data["weight_kg"],
                pickup_address=scrap_data["pickup_address"],
                defaults={
                    "preferred_time_slot": scrap_data["preferred_time_slot"],
                    "condition": scrap_data["condition"],
                    "latitude": scrap_data["latitude"],
                    "longitude": scrap_data["longitude"],
                    "status": "pending",
                },
            )

            if not scrap.images.exists():
                with open(image_path, "rb") as image_file:
                    ScrapImage.objects.create(
                        scrap=scrap,
                        image=File(image_file, name="image.png"),
                    )
                images_attached_count += 1

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created scrap request: {scrap.id}")
                )
            else:
                self.stdout.write(f"- Scrap request already exists: {scrap.id}")

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} scrap requests"))
        self.stdout.write(
            self.style.SUCCESS(f"Attached {images_attached_count} scrap images")
        )
        self.stdout.write("=" * 50)
