from django import forms
from .models import AutomaticPaymentSettings


KENYAN_BANKS = [
    ("", "Select Bank"),
    ("Co-operative Bank", "Co-operative Bank"),
    ("KCB Bank Kenya", "KCB Bank Kenya"),
    ("Equity Bank Kenya", "Equity Bank Kenya"),
    ("Absa Bank Kenya", "Absa Bank Kenya"),
    ("NCBA Bank Kenya", "NCBA Bank Kenya"),
    ("Standard Chartered Bank Kenya", "Standard Chartered Bank Kenya"),
    ("Stanbic Bank Kenya", "Stanbic Bank Kenya"),
    ("I&M Bank Kenya", "I&M Bank Kenya"),
    ("Diamond Trust Bank (DTB)", "Diamond Trust Bank (DTB)"),
    ("Family Bank", "Family Bank"),
    ("Prime Bank Kenya", "Prime Bank Kenya"),
    ("Bank of Africa Kenya", "Bank of Africa Kenya"),
    ("Ecobank Kenya", "Ecobank Kenya"),
    ("Sidian Bank", "Sidian Bank"),
    ("SBM Bank Kenya", "SBM Bank Kenya"),
    ("Kingdom Bank", "Kingdom Bank"),
    ("Access Bank Kenya", "Access Bank Kenya"),
    ("Citibank Kenya", "Citibank Kenya"),
    ("Gulf African Bank", "Gulf African Bank"),
    ("First Community Bank", "First Community Bank"),
    ("DIB Bank Kenya", "DIB Bank Kenya"),
    ("Consolidated Bank Kenya", "Consolidated Bank Kenya"),
    ("National Bank of Kenya", "National Bank of Kenya"),
    ("UBA Kenya", "UBA Kenya"),
    ("Bank of India Kenya", "Bank of India Kenya"),
    ("Bank of Baroda Kenya", "Bank of Baroda Kenya"),
    ("Development Bank of Kenya", "Development Bank of Kenya"),
    ("Guardian Bank", "Guardian Bank"),
    ("Middle East Bank Kenya", "Middle East Bank Kenya"),
    ("M-Oriental Bank", "M-Oriental Bank"),
    ("Victoria Commercial Bank", "Victoria Commercial Bank"),
    ("Other", "Other"),
]


class AutomaticPaymentSettingsForm(forms.ModelForm):

    bank_name = forms.ChoiceField(
        choices=KENYAN_BANKS,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = AutomaticPaymentSettings

        fields = [
            "environment",
            "is_active",

            "mpesa_online_enabled",
            "mpesa_online_shortcode",
            "mpesa_online_consumer_key",
            "mpesa_online_consumer_secret",
            "mpesa_online_passkey",
            "mpesa_online_callback_url",
            "mpesa_online_account_reference",

            "mpesa_till_enabled",
            "mpesa_till_number",
            "mpesa_till_shortcode",
            "mpesa_till_consumer_key",
            "mpesa_till_consumer_secret",
            "mpesa_till_passkey",
            "mpesa_till_callback_url",

            "mpesa_paybill_enabled",
            "mpesa_paybill_number",
            "mpesa_paybill_account",
            "mpesa_paybill_shortcode",
            "mpesa_paybill_consumer_key",
            "mpesa_paybill_consumer_secret",
            "mpesa_paybill_passkey",
            "mpesa_paybill_validation_url",
            "mpesa_paybill_confirmation_url",

            "bank_enabled",
            "bank_name",
            "bank_account_number",
            "bank_account_name",
            "bank_account_type",
            "bank_branch",
            "bank_branch_code",
            "bank_swift_bic",
            "bank_currency",

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

        widgets = {
            "environment": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "mpesa_online_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "mpesa_till_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "mpesa_paybill_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "bank_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "mpesa_online_consumer_secret": forms.PasswordInput(render_value=False, attrs={"class": "form-control"}),
            "mpesa_online_passkey": forms.PasswordInput(render_value=False, attrs={"class": "form-control"}),
            "mpesa_till_consumer_secret": forms.PasswordInput(render_value=False, attrs={"class": "form-control"}),
            "mpesa_till_passkey": forms.PasswordInput(render_value=False, attrs={"class": "form-control"}),
            "mpesa_paybill_consumer_secret": forms.PasswordInput(render_value=False, attrs={"class": "form-control"}),
            "mpesa_paybill_passkey": forms.PasswordInput(render_value=False, attrs={"class": "form-control"}),

            "bank_client_secret": forms.PasswordInput(render_value=False, attrs={"class": "form-control"}),
            "bank_api_key": forms.PasswordInput(render_value=False, attrs={"class": "form-control"}),
            "bank_webhook_secret": forms.PasswordInput(render_value=False, attrs={"class": "form-control"}),

            "bank_reference_mode": forms.Select(
                choices=[
                    ("ADMISSION", "Student Admission Number"),
                    ("MANUAL", "Manual Reference"),
                    ("ACCOUNT", "Configured Account/Reference"),
                ],
                attrs={"class": "form-select"}
            ),

            "bank_account_type": forms.Select(
                choices=[
                    ("Business", "Business"),
                    ("Current", "Current"),
                    ("Savings", "Savings"),
                    ("Other", "Other"),
                ],
                attrs={"class": "form-select"}
            ),

            "bank_currency": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "KES"}
            ),

            "bank_authentication_method": forms.Select(
                choices=[
                    ("OAuth2", "OAuth 2.0"),
                    ("API Key", "API Key"),
                    ("Basic", "Basic Authentication"),
                    ("Bearer Token", "Bearer Token"),
                    ("Custom", "Custom"),
                ],
                attrs={"class": "form-select"}
            ),

            "bank_polling_interval": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),

            "bank_minimum_payment": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),

            "bank_maximum_payment": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # M-Pesa Till credentials/configuration may be completed later.
        # Admin can save the configuration before Safaricom credentials are available.
        _till_optional_fields = [
            "mpesa_till_enabled",
            "mpesa_till_number",
            "mpesa_till_shortcode",
            "mpesa_till_consumer_key",
            "mpesa_till_consumer_secret",
            "mpesa_till_passkey",
            "mpesa_till_callback_url",
        ]

        for _field_name in _till_optional_fields:
            if _field_name in self.fields:
                self.fields[_field_name].required = False

        secret_fields = [
            "mpesa_online_consumer_secret",
            "mpesa_online_passkey",
            "mpesa_till_consumer_secret",
            "mpesa_till_passkey",
            "mpesa_paybill_consumer_secret",
            "mpesa_paybill_passkey",
            "bank_client_secret",
            "bank_api_key",
            "bank_webhook_secret",
        ]

        for name in secret_fields:
            if name in self.fields:
                self.fields[name].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)

        secret_fields = [
            "mpesa_online_consumer_secret",
            "mpesa_online_passkey",
            "mpesa_till_consumer_secret",
            "mpesa_till_passkey",
            "mpesa_paybill_consumer_secret",
            "mpesa_paybill_passkey",
            "bank_client_secret",
            "bank_api_key",
            "bank_webhook_secret",
        ]

        # Empty secret fields mean "keep the existing secret".
        if self.instance.pk:
            old = AutomaticPaymentSettings.objects.get(pk=self.instance.pk)

            for field in secret_fields:
                new_value = self.cleaned_data.get(field)
                if not new_value:
                    setattr(instance, field, getattr(old, field))

        if commit:
            instance.save()

        return instance
