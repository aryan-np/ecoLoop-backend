from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from donations.models import (
    DonationCategory,
    DonationCondition,
    DonationImage,
    DonationRequest,
)
from ecoLoop.management_seed_utils import get_seed_image_path, get_user_from_authorization


class Command(BaseCommand):
    help = "Create 5 sample donation requests for the user resolved from an authorization token."

    def add_arguments(self, parser):
        parser.add_argument(
            "--authorization",
            type=str,
            required=True,
            help="JWT access token or 'Bearer <token>' for the donation owner.",
        )

    def handle(self, *args, **options):
        user = get_user_from_authorization(options["authorization"])
        image_path = get_seed_image_path()
        suffix = timezone.now().strftime("%Y%m%d%H%M%S")

        categories = self._ensure_categories()
        conditions = self._ensure_conditions()

        requests_data = [
            {
                "category": categories["Clothes"],
                "condition": conditions["Good"],
                "quantity": f"Winter clothes bundle {suffix}-1",
                "notes": "Clean jackets, sweaters, and trousers ready for donation.",
                "pickup_address": "Kathmandu, New Baneshwor",
                "latitude": "27.688000",
                "longitude": "85.336000",
            },
            {
                "category": categories["Books"],
                "condition": conditions["Usable"],
                "quantity": f"School books set {suffix}-2",
                "notes": "Mixed secondary-level textbooks and notebooks.",
                "pickup_address": "Lalitpur, Satdobato",
                "latitude": "27.657000",
                "longitude": "85.324000",
            },
            {
                "category": categories["Electronics"],
                "condition": conditions["Need Maintenance"],
                "quantity": f"Small electronics box {suffix}-3",
                "notes": "Contains an old router, keyboard, and working speakers.",
                "pickup_address": "Bhaktapur, Suryabinayak",
                "latitude": "27.673000",
                "longitude": "85.429000",
            },
            {
                "category": categories["Household Items"],
                "condition": conditions["Good"],
                "quantity": f"Kitchen utensils set {suffix}-4",
                "notes": "Steel plates, bowls, and cooking utensils in good condition.",
                "pickup_address": "Kathmandu, Kalimati",
                "latitude": "27.694500",
                "longitude": "85.301000",
            },
            {
                "category": categories["Other"],
                "condition": conditions["Usable"],
                "quantity": f"Children toys pack {suffix}-5",
                "notes": "Soft toys and educational games suitable for donation.",
                "pickup_address": "Kirtipur, Chobhar",
                "latitude": "27.658000",
                "longitude": "85.292000",
            },
        ]

        created_requests = []
        for item in requests_data:
            donation_request = DonationRequest.objects.create(
                user=user,
                category=item["category"],
                condition=item["condition"],
                quantity=item["quantity"],
                notes=item["notes"],
                pickup_address=item["pickup_address"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                status="pending",
            )
            created_requests.append(donation_request)

            if image_path:
                with image_path.open("rb") as image_file:
                    DonationImage.objects.create(
                        donation=donation_request,
                        image=File(image_file, name=f"{donation_request.id}.png"),
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(created_requests)} donation requests for {user.email}."
            )
        )
        for donation_request in created_requests:
            self.stdout.write(f"- {donation_request.id} ({donation_request.quantity})")

    def _ensure_categories(self):
        data = {
            "Clothes": "Clothing items, shoes, and accessories.",
            "Books": "Books and educational materials.",
            "Electronics": "Electronic devices and reusable gadgets.",
            "Household Items": "Furniture, kitchenware, and home essentials.",
            "Other": "Miscellaneous reusable donation items.",
        }
        categories = {}
        for name, description in data.items():
            category, _ = DonationCategory.objects.get_or_create(
                name=name,
                defaults={"description": description},
            )
            categories[name] = category
        return categories

    def _ensure_conditions(self):
        data = {
            "Good": "In good reusable condition.",
            "Usable": "Usable with minor wear.",
            "Need Maintenance": "Needs small repair or servicing.",
        }
        conditions = {}
        for name, description in data.items():
            condition, _ = DonationCondition.objects.get_or_create(
                name=name,
                defaults={"description": description},
            )
            conditions[name] = condition
        return conditions
