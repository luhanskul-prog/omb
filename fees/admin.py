from django.contrib import admin
from django import forms
from django.db.models import Sum
from .models import AutomaticPaymentSettings, AcademicYear, Term, FeeRecord, FeePayment, FeeStructure, PaymentMethod


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "year",
    )

    ordering = (
        "-year",
    )


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "order",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "order",
    )


# ============================================================
# FEE STRUCTURE
# ============================================================

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):

    list_display = (
        "academic_year",
        "term",
        "class_name",
        "fee_item",
        "amount",
        "is_active",
    )

    list_filter = (
        "academic_year",
        "term",
        "is_active",
        "class_name",
    )

    search_fields = (
        "class_name",
        "fee_item",
    )

    ordering = (
        "-academic_year__year",
        "term__order",
        "class_name",
        "fee_item",
    )



class FeeRecordAdminForm(forms.ModelForm):

    class Meta:
        model = FeeRecord
        fields = (
            "student",
            "academic_year",
            "term",
            "opening_balance",
            "amount_charged",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Existing records should display their current amount.
        if self.instance and self.instance.pk:
            self.fields["amount_charged"].initial = self.instance.amount_charged

    def clean(self):

        cleaned_data = super().clean()

        student = cleaned_data.get("student")
        academic_year = cleaned_data.get("academic_year")
        term = cleaned_data.get("term")

        if not student or not academic_year or not term:
            return cleaned_data

        from .models import FeeStructure

        total = (
            FeeStructure.objects
            .filter(
                academic_year=academic_year,
                term=term,
                class_name=student.class_name,
                is_active=True,
            )
            .aggregate(total=Sum("amount"))
            ["total"]
        )

        if total is not None:
            cleaned_data["amount_charged"] = total

        return cleaned_data


@admin.register(FeeRecord)
class FeeRecordAdmin(admin.ModelAdmin):

    form = FeeRecordAdminForm


    actions = (
        "sync_fee_structure",
    )


    list_display = (
        "student",
        "academic_year",
        "term",
        "opening_balance",
        "amount_charged",
        "amount_paid_display",
        "balance_display",
    )

    list_filter = (
        "academic_year",
        "term",
    )

    search_fields = (
        "student__first_name",
        "student__middle_name",
        "student__last_name",
        "student__admission_no",
    )

    readonly_fields = (
        "amount_paid_display",
        "balance_display",
    )

    autocomplete_fields = (
        "student",
        "academic_year",
        "term",
    )


    @admin.action(description="Apply Fee Structure to selected records")
    def sync_fee_structure(self, request, queryset):

        updated = 0
        skipped = 0

        from django.db.models import Sum
        from .models import FeeStructure

        for record in queryset:

            if not record.academic_year or not record.term:
                skipped += 1
                continue

            total = (
                FeeStructure.objects
                .filter(
                    academic_year=record.academic_year,
                    term=record.term,
                    class_name=record.student.class_name,
                    is_active=True,
                )
                .aggregate(total=Sum("amount"))
                ["total"]
            )

            if total is not None:
                record.amount_charged = total
                record.save(update_fields=["amount_charged"])
                updated += 1
            else:
                skipped += 1

        if updated:
            self.message_user(
                request,
                f"{updated} fee record(s) updated from Fee Structure."
            )

        if skipped:
            self.message_user(
                request,
                f"{skipped} record(s) had no matching active Fee Structure.",
                level="WARNING"
            )

    def amount_paid_display(self, obj):
        return obj.amount_paid

    amount_paid_display.short_description = "Amount Paid"

    def balance_display(self, obj):
        return obj.balance

    balance_display.short_description = "Balance"


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):

    list_display = (
        "learner_display",
        "admission_display",
        "academic_year_display",
        "term_display",
        "amount",
        "payment_date",
        "receipt_number",
        "payment_method",
        "reference",
    )

    list_filter = (
        "payment_method",
        "payment_date",
        "fee_record__academic_year",
        "fee_record__term",
    )

    search_fields = (
        "fee_record__student__first_name",
        "fee_record__student__middle_name",
        "fee_record__student__last_name",
        "fee_record__student__admission_no",
        "receipt_number",
        "reference",
    )

    autocomplete_fields = (
        "fee_record",
    )

    ordering = (
        "-payment_date",
        "-id",
    )

    readonly_fields = (
        "receipt_number",
    )

    @admin.display(description="Learner")
    def learner_display(self, obj):
        student = obj.fee_record.student
        return str(student)

    @admin.display(description="Admission No.")
    def admission_display(self, obj):
        return obj.fee_record.student.admission_no

    @admin.display(description="Academic Year")
    def academic_year_display(self, obj):
        return obj.fee_record.academic_year

    @admin.display(description="Term")
    def term_display(self, obj):
        return obj.fee_record.term


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "method_type",
        "is_enabled",
        "online_enabled",
        "available_to_parents",
        "available_to_students",
        "automatic_verification",
        "sort_order",
    )

    list_filter = (
        "method_type",
        "is_enabled",
        "online_enabled",
        "automatic_verification",
    )

    search_fields = (
        "name",
        "code",
        "mpesa_paybill",
        "mpesa_till",
        "bank_name",
        "bank_account_number",
    )

    ordering = (
        "sort_order",
        "name",
    )


@admin.register(AutomaticPaymentSettings)
class AutomaticPaymentSettingsAdmin(admin.ModelAdmin):

    list_display = (
        "environment",
        "is_active",
        "mpesa_online_enabled",
        "mpesa_till_enabled",
        "mpesa_paybill_enabled",
        "bank_enabled",
        "updated_at",
    )

    fieldsets = (
        (
            "General",
            {
                "fields": (
                    "environment",
                    "is_active",
                )
            },
        ),
        (
            "M-Pesa Online",
            {
                "fields": (
                    "mpesa_online_enabled",
                    "mpesa_online_shortcode",
                    "mpesa_online_consumer_key",
                    "mpesa_online_consumer_secret",
                    "mpesa_online_passkey",
                    "mpesa_online_callback_url",
                    "mpesa_online_account_reference",
                )
            },
        ),
        (
            "M-Pesa Till",
            {
                "fields": (
                    "mpesa_till_enabled",
                    "mpesa_till_number",
                    "mpesa_till_shortcode",
                    "mpesa_till_consumer_key",
                    "mpesa_till_consumer_secret",
                    "mpesa_till_passkey",
                    "mpesa_till_callback_url",
                )
            },
        ),
        (
            "M-Pesa Paybill",
            {
                "fields": (
                    "mpesa_paybill_enabled",
                    "mpesa_paybill_number",
                    "mpesa_paybill_account",
                    "mpesa_paybill_shortcode",
                    "mpesa_paybill_consumer_key",
                    "mpesa_paybill_consumer_secret",
                    "mpesa_paybill_passkey",
                    "mpesa_paybill_validation_url",
                    "mpesa_paybill_confirmation_url",
                )
            },
        ),
        (
            "Bank",
            {
                "fields": (
                    "bank_enabled",
                    "bank_name",
                    "bank_account_number",
                    "bank_account_name",
                    "bank_api_url",
                    "bank_client_id",
                    "bank_client_secret",
                )
            },
        ),
    )


from .models import BankTransaction

@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "transaction_id",
        "amount",
        "reference",
        "student",
        "status",
        "created_at",
        "verified_at",
    )

    list_filter = (
        "status",
        "bank_name",
        "currency",
    )

    search_fields = (
        "transaction_id",
        "reference",
        "payer_name",
        "student__admission_no",
        "student__first_name",
        "student__last_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "verified_at",
        "raw_payload",
    )



from .models import MpesaPaybillTransaction

try:
    admin.site.register(
        MpesaPaybillTransaction,
        MpesaPaybillTransactionAdmin,
    )
except NameError:
    @admin.register(MpesaPaybillTransaction)
    class MpesaPaybillTransactionAdmin(admin.ModelAdmin):
        list_display = (
            "transaction_id",
            "transaction_amount",
            "bill_ref_number",
            "student",
            "status",
            "fee_payment",
            "created_at",
        )
        list_filter = (
            "status",
            "created_at",
        )
        search_fields = (
            "transaction_id",
            "bill_ref_number",
            "msisdn",
            "first_name",
            "last_name",
            "student__admission_no",
        )
        readonly_fields = (
            "transaction_id",
            "transaction_time",
            "transaction_amount",
            "business_short_code",
            "bill_ref_number",
            "invoice_number",
            "org_account_balance",
            "third_party_trans_id",
            "msisdn",
            "first_name",
            "middle_name",
            "last_name",
            "student",
            "fee_record",
            "fee_payment",
            "status",
            "validation_response",
            "raw_payload",
            "verification_message",
            "verified_at",
            "created_at",
            "updated_at",
        )
