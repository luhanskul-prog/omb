
from django.core.management.base import BaseCommand
from fees.models import PaymentMethod


class Command(BaseCommand):

    help = "Create or update the M-Pesa online payment method."

    def handle(self, *args, **options):

        method, created = PaymentMethod.objects.update_or_create(
            code="MPESA",
            defaults={
                "name": "M-Pesa",
                "method_type": "MPESA",
                "is_enabled": True,
                "online_enabled": True,
                "available_to_parents": True,
                "available_to_students": True,
                "available_to_admin": True,
                "automatic_verification": True,
                "instructions": (
                    "Enter the M-Pesa number to receive the payment prompt. "
                    "Confirm the payment on the phone."
                ),
                "sort_order": 1,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    "M-Pesa payment method created successfully."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "M-Pesa payment method updated successfully."
                )
            )
