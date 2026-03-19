from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Organization, RoleApplication


class Command(BaseCommand):
    help = "Create Organization records for all already-approved RoleApplications that don't have one yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without saving anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        approved = (
            RoleApplication.objects.filter(status="approved")
            .select_related("user")
            .order_by("created_at")
        )

        if not approved.exists():
            self.stdout.write(self.style.WARNING("No approved applications found."))
            return

        created_count = 0
        skipped_count = 0

        for application in approved:
            already_exists = Organization.objects.filter(user=application.user).exists()

            if already_exists:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP  {application.user.email} — organization already exists."
                    )
                )
                skipped_count += 1
                continue

            self.stdout.write(
                f"  {'[DRY RUN] ' if dry_run else ''}CREATE  "
                f"{application.user.email} | {application.role_type} | {application.organization_name}"
            )

            if not dry_run:
                with transaction.atomic():
                    Organization.objects.create(
                        user=application.user,
                        role_application=application,
                        org_type=application.role_type,
                        name=application.organization_name,
                        registration_number=application.registration_number,
                        established_date=application.established_date,
                        address=application.address,
                        description=application.description,
                        is_verified=True,
                    )

            created_count += 1

        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DRY RUN] Would create {created_count} organization(s), skip {skipped_count}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Created {created_count} organization(s), skipped {skipped_count}."
                )
            )
