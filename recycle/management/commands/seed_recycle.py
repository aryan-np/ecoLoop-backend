from decimal import Decimal

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from ecoLoop.management_seed_utils import get_seed_image_path, get_user_from_authorization
from recycle.models import ScrapCategory, ScrapImage, ScrapRequest


class Command(BaseCommand):
    help = "Create 5 sample recycle requests for the user resolved from an authorization token."

    def add_arguments(self, parser):
        parser.add_argument(
            "--authorization",
            type=str,
            required=True,
            help="JWT access token or 'Bearer <token>' for the recycle request owner.",
        )

    def handle(self, *args, **options):
        user = get_user_from_authorization(options["authorization"])
        image_path = get_seed_image_path()
        suffix = timezone.now().strftime("%Y%m%d%H%M%S")

        categories = self._ensure_categories()
        requests_data = [
            {
                "category": categories["Plastic (PET)"],
                "weight_kg": Decimal("6.50"),
                "pickup_address": f"Kathmandu, Maitidevi {suffix}-1",
                "preferred_time_slot": "morning",
                "condition": "clean",
                "latitude": "27.708000",
                "longitude": "85.334000",
            },
            {
                "category": categories["Paper (Cardboard)"],
                "weight_kg": Decimal("12.00"),
                "pickup_address": f"Lalitpur, Kupondole {suffix}-2",
                "preferred_time_slot": "afternoon",
                "condition": "mixed",
                "latitude": "27.689000",
                "longitude": "85.318000",
            },
            {
                "category": categories["Glass (Clear)"],
                "weight_kg": Decimal("9.25"),
                "pickup_address": f"Bhaktapur, Lokanthali {suffix}-3",
                "preferred_time_slot": "evening",
                "condition": "clean",
                "latitude": "27.673500",
                "longitude": "85.361000",
            },
            {
                "category": categories["Aluminum"],
                "weight_kg": Decimal("4.75"),
                "pickup_address": f"Kathmandu, Kalopul {suffix}-4",
                "preferred_time_slot": "morning",
                "condition": "mixed",
                "latitude": "27.720000",
                "longitude": "85.344000",
            },
            {
                "category": categories["E-Waste (General)"],
                "weight_kg": Decimal("7.80"),
                "pickup_address": f"Kirtipur, Nayabazar {suffix}-5",
                "preferred_time_slot": "afternoon",
                "condition": "clean",
                "latitude": "27.672000",
                "longitude": "85.287000",
            },
        ]

        created_requests = []
        for item in requests_data:
            scrap_request = ScrapRequest.objects.create(
                user=user,
                category=item["category"],
                weight_kg=item["weight_kg"],
                pickup_address=item["pickup_address"],
                preferred_time_slot=item["preferred_time_slot"],
                condition=item["condition"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                status="pending",
            )
            created_requests.append(scrap_request)

            if image_path:
                with image_path.open("rb") as image_file:
                    ScrapImage.objects.create(
                        scrap=scrap_request,
                        image=File(image_file, name=f"{scrap_request.id}.png"),
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(created_requests)} recycle requests for {user.email}."
            )
        )
        for scrap_request in created_requests:
            self.stdout.write(f"- {scrap_request.id} ({scrap_request.category.material_type})")

    def _ensure_categories(self):
        data = {
            "Plastic (PET)": ("Clear PET bottles and containers.", Decimal("15.00")),
            "Paper (Cardboard)": ("Corrugated cardboard and paper packaging.", Decimal("12.00")),
            "Glass (Clear)": ("Clear glass jars and bottles.", Decimal("5.00")),
            "Aluminum": ("Aluminum cans and reusable metal pieces.", Decimal("85.00")),
            "E-Waste (General)": ("Mixed reusable or recyclable electronic waste.", Decimal("30.00")),
        }
        categories = {}
        for material_type, (description, rate_per_kg) in data.items():
            category, _ = ScrapCategory.objects.get_or_create(
                material_type=material_type,
                defaults={
                    "description": description,
                    "rate_per_kg": rate_per_kg,
                },
            )
            categories[material_type] = category
        return categories
