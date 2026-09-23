from .models import AutomaticPaymentSettings


def get_till_readiness():
    config = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not config:
        return {
            "configured": False,
            "enabled": False,
            "ready": False,
            "missing": ["Automatic payment settings"],
        }

    missing = []

    if not config.mpesa_till_number:
        missing.append("Till Number")

    if not config.mpesa_till_shortcode:
        missing.append("Short Code")

    if not config.mpesa_till_consumer_key:
        missing.append("Consumer Key")

    if not config.mpesa_till_consumer_secret:
        missing.append("Consumer Secret")

    if not config.mpesa_till_passkey:
        missing.append("Passkey")

    if not config.mpesa_till_callback_url:
        missing.append("Callback URL")

    enabled = bool(
        config.is_active
        and config.mpesa_till_enabled
    )

    return {
        "configured": True,
        "enabled": enabled,
        "ready": enabled and not missing,
        "missing": missing,
        "till_number": config.mpesa_till_number or "",
        "shortcode": config.mpesa_till_shortcode or "",
        "callback_url": config.mpesa_till_callback_url or "",
    }
