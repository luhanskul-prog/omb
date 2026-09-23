from django.apps import AppConfig


class FeesConfig(AppConfig):
    name = 'fees'

    def ready(self):
        from .models import AutomaticPaymentSettings
        from django.db.models.signals import post_save
        from .payment_config_sync import sync_payment_configuration
        post_save.connect(
            sync_payment_configuration,
            sender=AutomaticPaymentSettings,
            dispatch_uid="fees.automatic_payment_settings_sync",
        )
