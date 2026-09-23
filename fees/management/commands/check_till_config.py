from django.core.management.base import BaseCommand

from fees.till_readiness import get_till_readiness


class Command(BaseCommand):
    help = "Check M-Pesa Till automatic payment configuration."

    def handle(self, *args, **options):
        result = get_till_readiness()

        self.stdout.write("")
        self.stdout.write("=== M-PESA TILL CONFIGURATION ===")
        self.stdout.write(
            f"Configured: {result['configured']}"
        )
        self.stdout.write(
            f"Enabled: {result['enabled']}"
        )
        self.stdout.write(
            f"Ready: {result['ready']}"
        )

        if result.get("till_number"):
            self.stdout.write(
                f"Till Number: {result['till_number']}"
            )

        if result.get("shortcode"):
            self.stdout.write(
                f"Short Code: {result['shortcode']}"
            )

        if result.get("callback_url"):
            self.stdout.write(
                f"Callback URL: {result['callback_url']}"
            )

        missing = result.get("missing") or []

        if missing:
            self.stdout.write("")
            self.stdout.write("Missing:")
            for item in missing:
                self.stdout.write(f" - {item}")

        self.stdout.write("")

        if result["ready"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "TILL CONFIGURATION IS READY FOR CREDENTIAL TESTING."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "TILL CONFIGURATION IS NOT YET READY."
                )
            )
