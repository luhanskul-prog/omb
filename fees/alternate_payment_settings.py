
from django import forms
from .models import AlternatePaymentSettings


class AlternatePaymentSettingsForm(forms.ModelForm):

    class Meta:
        model = AlternatePaymentSettings

        fields = [
            "paybill_number",
            "paybill_instructions",
            "till_number",
            "till_instructions",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
            "bank_branch",
            "bank_instructions",
        ]

        widgets = {

            "paybill_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 123456",
                }
            ),

            "paybill_instructions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),

            "till_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 1234567",
                }
            ),

            "till_instructions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),

            "bank_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Bank name",
                }
            ),

            "bank_account_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account name",
                }
            ),

            "bank_account_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account number",
                }
            ),

            "bank_branch": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Branch",
                }
            ),

            "bank_instructions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }
