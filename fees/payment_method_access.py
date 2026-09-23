from .models import AutomaticPaymentSettings


METHOD_FLAGS = {
    "MPESA_ONLINE": "mpesa_online_enabled",
    "MPESA_TILL": "mpesa_till_enabled",
    "MPESA_PAYBILL": "mpesa_paybill_enabled",
    "BANK": "bank_enabled",
}


def get_automatic_payment_settings():
    return (
        AutomaticPaymentSettings.objects
        .filter(pk=1)
        .first()
    )


def is_automatic_payment_enabled(method=None):
    config = get_automatic_payment_settings()

    if not config or not config.is_active:
        return False

    if method is None:
        return True

    field_name = METHOD_FLAGS.get(str(method).upper())

    if not field_name:
        return False

    return bool(getattr(config, field_name, False))


def require_automatic_payment(method):
    config = get_automatic_payment_settings()

    if not config:
        raise RuntimeError(
            "Automatic payments are not configured."
        )

    if not config.is_active:
        raise RuntimeError(
            "Automatic payments are currently disabled "
            "by the school administrator."
        )

    field_name = METHOD_FLAGS.get(str(method).upper())

    if not field_name:
        raise RuntimeError(
            "This automatic payment method is not supported."
        )

    if not getattr(config, field_name, False):
        raise RuntimeError(
            "This automatic payment method is currently "
            "disabled by the school administrator."
        )

    return config
