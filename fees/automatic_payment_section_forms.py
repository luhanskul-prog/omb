
from .automatic_payment_settings import AutomaticPaymentSettingsForm
from .models import AutomaticPaymentSettings


class MpesaOnlineSettingsForm(AutomaticPaymentSettingsForm):

    class Meta(AutomaticPaymentSettingsForm.Meta):
        model = AutomaticPaymentSettings

        fields = [
            "environment",
            "is_active",

            "mpesa_online_enabled",
            "mpesa_online_shortcode",
            "mpesa_online_account_reference",
            "mpesa_online_consumer_key",
            "mpesa_online_consumer_secret",
            "mpesa_online_passkey",
            "mpesa_online_callback_url",
        ]


class MpesaTillSettingsForm(AutomaticPaymentSettingsForm):

    class Meta(AutomaticPaymentSettingsForm.Meta):
        model = AutomaticPaymentSettings

        fields = [
            "environment",
            "is_active",

            "mpesa_till_enabled",
            "mpesa_till_number",
            "mpesa_till_shortcode",
            "mpesa_till_callback_url",
            "mpesa_till_consumer_key",
            "mpesa_till_consumer_secret",
            "mpesa_till_passkey",
        ]


class MpesaPaybillSettingsForm(AutomaticPaymentSettingsForm):

    class Meta(AutomaticPaymentSettingsForm.Meta):
        model = AutomaticPaymentSettings

        fields = [
            "environment",
            "is_active",

            "mpesa_paybill_enabled",
            "mpesa_paybill_number",
            "mpesa_paybill_account",
            "mpesa_paybill_shortcode",
            "mpesa_paybill_consumer_key",
            "mpesa_paybill_consumer_secret",
            "mpesa_paybill_passkey",
            "mpesa_paybill_validation_url",
            "mpesa_paybill_confirmation_url",
        ]


class BankSettingsForm(AutomaticPaymentSettingsForm):

    class Meta(AutomaticPaymentSettingsForm.Meta):
        model = AutomaticPaymentSettings

        fields = [
            "environment",
            "is_active",

            "bank_enabled",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
            "bank_account_type",
            "bank_branch",
            "bank_branch_code",
            "bank_currency",
            "bank_swift_bic",

            "bank_reference_mode",
            "bank_reference_prefix",
            "bank_manual_reference",

            "bank_api_url",
            "bank_authentication_method",
            "bank_client_id",
            "bank_client_secret",
            "bank_api_key",
            "bank_access_token_url",

            "bank_transaction_endpoint",
            "bank_account_validation_endpoint",
            "bank_statement_endpoint",
            "bank_balance_endpoint",

            "bank_webhook_url",
            "bank_webhook_secret",

            "bank_auto_reconciliation",
            "bank_auto_receipt",
            "bank_duplicate_protection",
            "bank_transaction_polling",
            "bank_polling_interval",
            "bank_minimum_payment",
            "bank_maximum_payment",
        ]
