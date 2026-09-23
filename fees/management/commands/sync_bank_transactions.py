
from django.core.management.base import BaseCommand

from fees.bank_service import (
    fetch_bank_transactions,
    import_bank_api_response,
)


class Command(BaseCommand):

    help = "Fetch and automatically reconcile bank transactions."

    def handle(self, *args, **options):

        self.stdout.write(
            "Starting bank transaction synchronization..."
        )

        try:

            payload = fetch_bank_transactions()

            imported = import_bank_api_response(
                payload
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Synchronization complete. "
                    f"{len(imported)} new transaction(s) processed."
                )
            )

        except Exception as exc:

            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "BANK SYNCHRONIZATION NOT COMPLETED"
                )
            )
            self.stdout.write("")
            self.stdout.write(
                f"Reason: {exc}"
            )
            self.stdout.write("")
            self.stdout.write(
                "Open Fees Dashboard → "
                "Activate Automatic Payments → "
                "Bank Automatic Payment & Verification."
            )
            self.stdout.write("")
            self.stdout.write(
                "Configure the bank transaction/API endpoint "
                "provided by your bank."
            )
            self.stdout.write("")

            return
