from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
from students.models import Student


# ============================================================
# ACADEMIC YEAR
# ============================================================

class AcademicYear(models.Model):

    year = models.PositiveIntegerField(
        unique=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-year"]

    def __str__(self):
        return str(self.year)


# ============================================================
# TERM
# ============================================================

class Term(models.Model):

    name = models.CharField(
        max_length=50
    )

    order = models.PositiveIntegerField(
        default=1
    )

    # ------------------------------------------------------------
    # ACADEMIC YEAR
    # ------------------------------------------------------------

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="terms",
        null=True,
        blank=True
    )

    # ------------------------------------------------------------
    # ACADEMIC YEAR
    # ------------------------------------------------------------

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="terms",
        null=True,
        blank=True
    )

    # ------------------------------------------------------------
    # TERM DATES
    # ------------------------------------------------------------

    start_date = models.DateField(
        null=True,
        blank=True
    )

    end_date = models.DateField(
        null=True,
        blank=True
    )

    # ------------------------------------------------------------
    # TERM STATUS
    # ------------------------------------------------------------

    is_active = models.BooleanField(
        default=True
    )

    is_closed = models.BooleanField(
        default=False
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        if self.academic_year:
            return f"{self.academic_year.year} - {self.name}"
        return self.name


# ============================================================
# FEE RECORD
# ============================================================

class FeeRecord(models.Model):

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="fee_records"
    )

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="fee_records",
        null=True,
        blank=True
    )

    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="fee_records",
        null=True,
        blank=True
    )

    old_academic_year = models.CharField(
        max_length=20,
        default="2026",
        blank=True
    )

    old_term = models.CharField(
        max_length=20,
        default="1",
        blank=True
    )

    opening_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    amount_charged = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # --------------------------------------------------------
    # TOTAL PAID
    # --------------------------------------------------------

    @property
    def amount_paid(self):

        total = self.payments.aggregate(
            total=Sum("amount")
        )["total"]

        return total or 0

    # --------------------------------------------------------
    # BALANCE
    # --------------------------------------------------------

    @property
    def balance(self):

        return (
            self.opening_balance
            + self.amount_charged
            - self.amount_paid
        )

    # --------------------------------------------------------
    # CREATE FEE RECORD FOR TERM
    # --------------------------------------------------------

    @classmethod
    def create_for_term(
        cls,
        student,
        academic_year,
        term,
        amount_charged=0
    ):

        # ----------------------------------------------------
        # GET PREVIOUS TERM BALANCE
        # ----------------------------------------------------

        previous_record = (
            cls.objects
            .filter(
                student=student,
                academic_year=academic_year
            )
            .exclude(
                term=term
            )
            .select_related(
                "term"
            )
            .order_by(
                "-term__order",
                "-id"
            )
            .first()
        )

        opening_balance = 0

        if previous_record:
            opening_balance = previous_record.balance

        # ----------------------------------------------------
        # READ CURRENT FEE STRUCTURE
        # ----------------------------------------------------

        # FeeStructure is defined later in this module, so the
        # import is intentionally done at runtime.
        try:
            from .models import FeeStructure

            structured_total = (
                FeeStructure.objects
                .filter(
                    academic_year=academic_year,
                    term=term,
                    class_name=student.class_name,
                    is_active=True
                )
                .aggregate(
                    total=Sum("amount")
                )["total"]
            )

            # If a structure exists, it becomes the official
            # amount charged for this learner.
            if structured_total is not None:
                amount_charged = structured_total

        except Exception:
            # Keep the existing behaviour if the fee structure
            # is unavailable for any reason.
            pass

        # ----------------------------------------------------
        # CREATE FEE RECORD
        # ----------------------------------------------------

        return cls.objects.create(
            student=student,
            academic_year=academic_year,
            term=term,
            opening_balance=opening_balance,
            amount_charged=amount_charged,
            old_academic_year=str(
                academic_year.year
            ),
            old_term=str(
                term.order
            )
        )

    # --------------------------------------------------------
    # AUTOMATIC FEE STRUCTURE SYNC
    # --------------------------------------------------------

    def save(self, *args, **kwargs):

        # Fee Structure is the source of the current charge.
        # Match the learner's class, academic year and term.
        try:
            from .models import FeeStructure

            structured_total = (
                FeeStructure.objects
                .filter(
                    academic_year=self.academic_year,
                    term=self.term,
                    class_name=self.student.class_name,
                    is_active=True,
                )
                .aggregate(total=Sum("amount"))
                ["total"]
            )

            # Only replace the charge when a structure exists.
            if structured_total is not None:
                self.amount_charged = structured_total

        except Exception:
            # Do not prevent saving a FeeRecord if the structure
            # cannot be read during migrations or startup.
            pass

        super().save(*args, **kwargs)


    # --------------------------------------------------------
    # STRING
    # --------------------------------------------------------

    def __str__(self):

        year = (
            self.academic_year.year
            if self.academic_year
            else self.old_academic_year
        )

        term = (
            self.term.name
            if self.term
            else self.old_term
        )

        return (
            f"{self.student} - "
            f"{term} - "
            f"{year}"
        )


# ============================================================
# FEE PAYMENT
# ============================================================

class FeePayment(models.Model):

    fee_record = models.ForeignKey(
        FeeRecord,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_date = models.DateField()

    # --------------------------------------------------------
    # AUTOMATIC RECEIPT NUMBER
    # Example:
    #
    # LUH001RCP
    # LUH002RCP
    # LUH003RCP
    #
    # --------------------------------------------------------

    receipt_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        editable=False
    )

    payment_method = models.CharField(
        max_length=50,
        blank=True
    )

    reference = models.CharField(
        max_length=100,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # ========================================================
    # SAVE PAYMENT
    # ========================================================

    def save(
        self,
        *args,
        **kwargs
    ):

        # ----------------------------------------------------
        # Only generate receipt number for new payments
        # ----------------------------------------------------

        if not self.receipt_number:

            last_payment = (
                FeePayment.objects
                .filter(
                    receipt_number__startswith="LUH"
                )
                .order_by(
                    "-id"
                )
                .first()
            )

            if last_payment and last_payment.receipt_number:

                try:

                    number_part = (
                        last_payment
                        .receipt_number
                        .replace(
                            "LUH",
                            ""
                        )
                        .replace(
                            "RCP",
                            ""
                        )
                    )

                    next_number = (
                        int(number_part) + 1
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    next_number = 1

            else:

                next_number = 1

            self.receipt_number = (
                f"LUH{next_number:03d}RCP"
            )

        super().save(
            *args,
            **kwargs
        )

    # ========================================================
    # STRING
    # ========================================================

    def __str__(self):

        return (
            f"{self.receipt_number} - "
            f"{self.fee_record.student} - "
            f"{self.amount}"
        )



# ============================================================
# PAYMENT METHODS
# ============================================================

class PaymentMethod(models.Model):

    METHOD_TYPE_CHOICES = [
        ("MPESA", "M-Pesa"),
        ("BANK", "Bank Transfer"),
        ("OTHER", "Other"),
    ]

    code = models.CharField(
        max_length=30,
        unique=True,
        help_text="Internal code, e.g. MPESA, BANK",
    )

    name = models.CharField(
        max_length=100,
    )

    method_type = models.CharField(
        max_length=20,
        choices=METHOD_TYPE_CHOICES,
        default="MPESA",
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    online_enabled = models.BooleanField(
        default=True,
    )

    available_to_parents = models.BooleanField(
        default=True,
    )

    available_to_students = models.BooleanField(
        default=True,
    )

    available_to_admin = models.BooleanField(
        default=True,
    )

    automatic_verification = models.BooleanField(
        default=False,
        help_text="Automatically verify provider transactions.",
    )

    # --------------------------------------------------------
    # M-PESA
    # --------------------------------------------------------

    mpesa_paybill = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    mpesa_till = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    mpesa_shortcode = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    mpesa_account_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # --------------------------------------------------------
    # BANK
    # --------------------------------------------------------

    bank_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    bank_account_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    bank_account_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    bank_branch = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    # --------------------------------------------------------
    # GENERAL
    # --------------------------------------------------------

    instructions = models.TextField(
        blank=True,
        default="",
    )

    sort_order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


# ============================================================
# ONLINE PAYMENT
# ============================================================

class OnlinePayment(models.Model):

    STATUS_CHOICES = [
        ("INITIATED", "Initiated"),
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("VERIFIED", "Verified"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"),
        ("REVERSED", "Reversed"),
    ]

    PAYER_ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("PARENT", "Parent"),
        ("STUDENT", "Student"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("MPESA", "M-Pesa"),
        ("BANK", "Bank"),
        ("OTHER", "Other"),
    ]

    fee_record = models.ForeignKey(
        FeeRecord,
        on_delete=models.PROTECT,
        related_name="online_payments",
    )

    payer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="online_fee_payments",
    )

    payer_role = models.CharField(
        max_length=20,
        choices=PAYER_ROLE_CHOICES,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="MPESA",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="INITIATED",
        db_index=True,
    )

    # --------------------------------------------------------
    # PROVIDER IDENTIFIERS
    # --------------------------------------------------------

    merchant_request_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
        db_index=True,
    )

    checkout_request_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
        db_index=True,
    )

    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )

    phone_number = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    account_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # --------------------------------------------------------
    # PROVIDER RESPONSE
    # --------------------------------------------------------

    provider_response_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    provider_response_description = models.TextField(
        blank=True,
        default="",
    )

    provider_receipt = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    provider_raw_response = models.JSONField(
        blank=True,
        null=True,
    )

    # --------------------------------------------------------
    # VERIFICATION
    # --------------------------------------------------------

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verification_message = models.TextField(
        blank=True,
        default="",
    )

    fee_payment = models.OneToOneField(
        FeePayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="online_transaction",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "-created_at"]
            ),
            models.Index(
                fields=["payer", "-created_at"]
            ),
            models.Index(
                fields=["fee_record", "-created_at"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.fee_record.student} - "
            f"KSh {self.amount:,.2f} - "
            f"{self.status}"
        )

# ============================================================
# FEE STRUCTURE
# ============================================================

class FeeStructure(models.Model):

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="fee_structures"
    )

    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="fee_structures"
    )

    class_name = models.CharField(
        max_length=100
    )

    fee_item = models.CharField(
        max_length=150
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "-academic_year__year",
            "term__order",
            "class_name",
            "fee_item",
        ]

    def __str__(self):
        return (
            f"{self.academic_year.year} - "
            f"{self.term.name} - "
            f"{self.class_name} - "
            f"{self.fee_item}"
        )
from django.db import models
from django.conf import settings


class AlternatePayment(models.Model):
    METHOD_CHOICES = (
        ("paybill", "M-Pesa PayBill"),
        ("till", "M-Pesa Till"),
        ("bank", "Bank Payment"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("VERIFIED", "Verified"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="alternate_payments",
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    payment_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
    )

    reference = models.CharField(
        max_length=40,
        unique=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    external_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.reference} - {self.student.admission_no} - KSh {self.amount}"

    class Meta:
        ordering = ["-created_at"]


class AlternatePaymentSettings(models.Model):
    """
    Configuration for manual/alternate school fee payments.
    Independent from the existing M-Pesa STK integration.
    """

    paybill_number = models.CharField(
        max_length=50,
        blank=True,
        default=""
    )

    paybill_instructions = models.TextField(
        blank=True,
        default="Use the learner's admission number as the account/reference."
    )

    till_number = models.CharField(
        max_length=50,
        blank=True,
        default=""
    )

    till_instructions = models.TextField(
        blank=True,
        default="Keep the M-Pesa transaction message for verification."
    )

    bank_name = models.CharField(
        max_length=150,
        blank=True,
        default=""
    )

    bank_account_name = models.CharField(
        max_length=150,
        blank=True,
        default=""
    )

    bank_account_number = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    bank_branch = models.CharField(
        max_length=150,
        blank=True,
        default=""
    )

    bank_instructions = models.TextField(
        blank=True,
        default="Use the learner's admission number as the payment reference."
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alternate Payment Settings"
        verbose_name_plural = "Alternate Payment Settings"

    def __str__(self):
        return "Alternate Payment Settings"


class TillPaymentIntent(models.Model):
    """
    Pending automatic payment intent for M-Pesa Till payments.

    A Till payment normally does not carry the learner admission
    number. The intent therefore links the learner to the expected
    phone number and amount before the customer pays.
    """

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("VERIFIED", "Verified"),
        ("EXPIRED", "Expired"),
        ("UNMATCHED", "Unmatched"),
        ("CANCELLED", "Cancelled"),
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="till_payment_intents",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    phone_number = models.CharField(
        max_length=30,
    )

    till_number = models.CharField(
        max_length=50,
        default="7642636",
    )

    online_payment = models.OneToOneField(
        "OnlinePayment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="till_payment_intent",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    transaction_time = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["phone_number", "amount", "status"]
            ),
            models.Index(
                fields=["transaction_id"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.student.admission_no} - "
            f"KSh {self.amount} - {self.status}"
        )


class AutomaticPaymentSettings(models.Model):

    ENVIRONMENT_CHOICES = (
        ("sandbox", "Sandbox"),
        ("production", "Production"),
    )

    environment = models.CharField(
        max_length=20,
        choices=ENVIRONMENT_CHOICES,
        default="sandbox",
    )

    is_active = models.BooleanField(default=True)

    # M-PESA ONLINE
    mpesa_online_enabled = models.BooleanField(default=True)
    mpesa_online_shortcode = models.CharField(max_length=50, blank=True, default="")
    mpesa_online_consumer_key = models.CharField(max_length=255, blank=True, default="")
    mpesa_online_consumer_secret = models.CharField(max_length=255, blank=True, default="")
    mpesa_online_passkey = models.CharField(max_length=255, blank=True, default="")
    mpesa_online_callback_url = models.URLField(blank=True, default="")
    mpesa_online_account_reference = models.CharField(
        max_length=100,
        blank=True,
        default="SCHOOLFEES",
    )

    # M-PESA TILL
    mpesa_till_enabled = models.BooleanField(default=True)
    mpesa_till_number = models.CharField(max_length=50, blank=True, default="")
    mpesa_till_shortcode = models.CharField(max_length=50, blank=True, default="")
    mpesa_till_consumer_key = models.CharField(max_length=255, blank=True, default="")
    mpesa_till_consumer_secret = models.CharField(max_length=255, blank=True, default="")
    mpesa_till_passkey = models.CharField(max_length=255, blank=True, default="")
    mpesa_till_callback_url = models.URLField(blank=True, default="")

    # M-PESA PAYBILL
    mpesa_paybill_enabled = models.BooleanField(default=True)
    mpesa_paybill_number = models.CharField(max_length=50, blank=True, default="")
    mpesa_paybill_account = models.CharField(max_length=100, blank=True, default="")
    mpesa_paybill_shortcode = models.CharField(max_length=50, blank=True, default="")
    mpesa_paybill_consumer_key = models.CharField(max_length=255, blank=True, default="")
    mpesa_paybill_consumer_secret = models.CharField(max_length=255, blank=True, default="")
    mpesa_paybill_passkey = models.CharField(max_length=255, blank=True, default="")
    mpesa_paybill_validation_url = models.URLField(blank=True, default="")
    mpesa_paybill_confirmation_url = models.URLField(blank=True, default="")

    # BANK
    bank_enabled = models.BooleanField(default=True)
    bank_name = models.CharField(max_length=200, blank=True, default="")
    bank_account_number = models.CharField(max_length=100, blank=True, default="")
    bank_account_name = models.CharField(max_length=200, blank=True, default="")
    bank_api_url = models.URLField(blank=True, default="")
    bank_client_id = models.CharField(max_length=255, blank=True, default="")
    bank_client_secret = models.CharField(max_length=255, blank=True, default="")
    # BANK PAYMENT / AUTOMATIC VERIFICATION
    bank_account_type = models.CharField(
        max_length=50,
        blank=True,
        default="Business",
    )
    bank_branch = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )
    bank_branch_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )
    bank_swift_bic = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )
    bank_currency = models.CharField(
        max_length=20,
        blank=True,
        default="KES",
    )

    bank_reference_mode = models.CharField(
        max_length=50,
        choices=[
            ("ADMISSION", "Student Admission Number"),
            ("MANUAL", "Manual Reference"),
            ("ACCOUNT", "Configured Account/Reference"),
        ],
        default="ADMISSION",
    )
    bank_reference_prefix = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )
    bank_manual_reference = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    bank_api_key = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )
    bank_authentication_method = models.CharField(
        max_length=100,
        blank=True,
        default="OAuth2",
    )
    bank_access_token_url = models.URLField(
        blank=True,
        default="",
    )
    bank_transaction_endpoint = models.URLField(
        blank=True,
        default="",
    )
    bank_account_validation_endpoint = models.URLField(
        blank=True,
        default="",
    )
    bank_statement_endpoint = models.URLField(
        blank=True,
        default="",
    )
    bank_balance_endpoint = models.URLField(
        blank=True,
        default="",
    )

    bank_webhook_url = models.URLField(
        blank=True,
        default="",
    )
    bank_webhook_secret = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    bank_auto_reconciliation = models.BooleanField(default=True)
    bank_auto_receipt = models.BooleanField(default=True)
    bank_duplicate_protection = models.BooleanField(default=True)
    bank_transaction_polling = models.BooleanField(default=False)

    bank_polling_interval = models.PositiveIntegerField(
        default=5,
        help_text="Polling interval in minutes.",
    )

    bank_minimum_payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    bank_maximum_payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    bank_last_sync = models.DateTimeField(
        null=True,
        blank=True,
    )
    bank_last_transaction_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )
    bank_verification_status = models.CharField(
        max_length=50,
        blank=True,
        default="NOT_CONFIGURED",
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Automatic Payment Settings"
        verbose_name_plural = "Automatic Payment Settings"

    def __str__(self):
        return "Automatic Payment Settings"


# =========================================================
# AUTOMATIC BANK PAYMENT TRANSACTIONS
# =========================================================

class BankTransaction(models.Model):

    STATUS_CHOICES = [
        ("AWAITING_PAYMENT", "Awaiting Payment"),
        ("PENDING", "Pending Verification"),
        ("VERIFIED", "Verified"),
        ("UNMATCHED", "Unmatched"),
        ("REJECTED", "Rejected"),
        ("DUPLICATE", "Duplicate"),
        ("ERROR", "Verification Error"),
    ]

    bank_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    bank_account_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    transaction_id = models.CharField(
        max_length=200,
        unique=True,
    )

    reference = models.CharField(
        max_length=300,
        blank=True,
        default="",
        db_index=True,
    )

    payer_name = models.CharField(
        max_length=300,
        blank=True,
        default="",
    )

    payer_account = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=20,
        default="KES",
    )

    transaction_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bank_transactions",
    )

    fee_record = models.ForeignKey(
        "FeeRecord",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bank_transactions",
    )

    fee_payment = models.OneToOneField(
        "FeePayment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bank_transaction",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="PENDING",
        db_index=True,
    )

    verification_message = models.TextField(
        blank=True,
        default="",
    )

    raw_payload = models.JSONField(
        default=dict,
        blank=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_id} - {self.amount} - {self.status}"


class MpesaPaybillTransaction(models.Model):
    STATUS_CHOICES = [
        ("RECEIVED", "Received"),
        ("VALIDATED", "Validated"),
        ("VERIFIED", "Verified"),
        ("REJECTED", "Rejected"),
        ("DUPLICATE", "Duplicate"),
        ("ERROR", "Error"),
    ]

    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )
    transaction_time = models.CharField(
        max_length=100,
        blank=True,
    )
    transaction_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    business_short_code = models.CharField(
        max_length=50,
        blank=True,
    )
    bill_ref_number = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
    )
    invoice_number = models.CharField(
        max_length=150,
        blank=True,
    )
    org_account_balance = models.CharField(
        max_length=100,
        blank=True,
    )
    third_party_trans_id = models.CharField(
        max_length=150,
        blank=True,
    )

    msisdn = models.CharField(
        max_length=30,
        blank=True,
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
    )
    middle_name = models.CharField(
        max_length=100,
        blank=True,
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
    )

    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mpesa_paybill_transactions",
    )
    fee_record = models.ForeignKey(
        "fees.FeeRecord",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mpesa_paybill_transactions",
    )
    fee_payment = models.OneToOneField(
        "fees.FeePayment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mpesa_paybill_transaction",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="RECEIVED",
        db_index=True,
    )

    validation_response = models.JSONField(
        default=dict,
        blank=True,
    )
    raw_payload = models.JSONField(
        default=dict,
        blank=True,
    )
    verification_message = models.TextField(
        blank=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["bill_ref_number", "status"],
            ),
            models.Index(
                fields=["status", "created_at"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.transaction_id} - "
            f"{self.transaction_amount} - "
            f"{self.status}"
        )
