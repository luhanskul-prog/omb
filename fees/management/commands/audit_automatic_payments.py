from django.core.management.base import BaseCommand

from fees.models import AutomaticPaymentSettings


class Command(BaseCommand):
    help = "Audit automatic payment configuration."

    def handle(self, *args, **options):
        config = AutomaticPaymentSettings.objects.filter(
            pk=1
        ).first()

        if not config:
            self.stdout.write(
                self.style.ERROR(
                    "AutomaticPaymentSettings pk=1 does not exist."
                )
            )
            return

        self.stdout.write("")
        self.stdout.write(
            "=== AUTOMATIC PAYMENT CONFIGURATION ==="
        )

        fields = [
            ("Master Active", "is_active"),
            ("Online Enabled", "mpesa_online_enabled"),
            ("Online Short Code", "mpesa_online_shortcode"),
            ("Online Callback", "mpesa_online_callback_url"),

            ("Till Enabled", "mpesa_till_enabled"),
            ("Till Number", "mpesa_till_number"),
            ("Till Short Code", "mpesa_till_shortcode"),
            ("Till Callback", "mpesa_till_callback_url"),
            ("Till Consumer Key", "mpesa_till_consumer_key"),
            ("Till Consumer Secret", "mpesa_till_consumer_secret"),
            ("Till Passkey", "mpesa_till_passkey"),

            ("PayBill Enabled", "mpesa_paybill_enabled"),
            ("PayBill Number", "mpesa_paybill_number"),
            ("PayBill Account", "mpesa_paybill_account"),

            ("Bank Enabled", "bank_enabled"),
            ("Bank", "bank_name"),
            ("Bank Account", "bank_account_number"),
        ]

        secret_names = {
            "mpesa_till_consumer_key",
            "mpesa_till_consumer_secret",
            "mpesa_till_passkey",
        }

        for label, field in fields:
            value = getattr(config, field, "")

            if field in secret_names:
                value = (
                    "SET"
                    if str(value or "").strip()
                    else "MISSING"
                )

            self.stdout.write(
                f"{label}: {value}"
            )

        self.stdout.write("")
