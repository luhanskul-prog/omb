"""
Keeps legacy AlternatePaymentSettings synchronized with
AutomaticPaymentSettings.

AutomaticPaymentSettings remains the master configuration.

This compatibility layer exists so older payment/instruction
pages immediately display the current administrator configuration.
"""

from .models import AutomaticPaymentSettings, AlternatePaymentSettings


def sync_legacy_payment_settings():
    config = AutomaticPaymentSettings.objects.filter(pk=1).first()
    if not config:
        return False

    legacy, _ = AlternatePaymentSettings.objects.get_or_create(pk=1)

    changed = False

    values = {
        "paybill_number": str(
            getattr(config, "mpesa_paybill_number", "") or ""
        ).strip(),

        "till_number": str(
            getattr(config, "mpesa_till_number", "") or ""
        ).strip(),

        "bank_name": str(
            getattr(config, "bank_name", "") or ""
        ).strip(),

        "bank_account_number": str(
            getattr(config, "bank_account_number", "") or ""
        ).strip(),
    }

    for field, value in values.items():
        if getattr(legacy, field, "") != value:
            setattr(legacy, field, value)
            changed = True

    if changed:
        legacy.save(
            update_fields=[
                "paybill_number",
                "till_number",
                "bank_name",
                "bank_account_number",
            ]
        )

    return True


def sync_payment_configuration(sender=None, instance=None, **kwargs):
    if instance is not None and instance.__class__.__name__ != "AutomaticPaymentSettings":
        return

    try:
        sync_legacy_payment_settings()
    except Exception:
        # Never allow compatibility syncing to break payment saving.
        pass
