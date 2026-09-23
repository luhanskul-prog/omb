
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import OnlinePayment, FeePayment


def _can_view_payment(request, payment):
    user = request.user

    if user.is_staff or user.is_superuser:
        return True

    if payment.payer_id == user.id:
        return True

    # Allow a linked parent account to view payments belonging
    # to that parent's children.
    try:
        profile = getattr(user, "profile", None)
        if profile and getattr(profile, "role", "") == "PARENT":
            student = payment.fee_record.student
            children = profile.children.all()
            return children.filter(pk=student.pk).exists()
    except Exception:
        pass

    return False


def _branding():
    try:
        from accounts.models import SchoolBranding
        return SchoolBranding.objects.filter(is_active=True).first()
    except Exception:
        return None


def _payment_context(payment):
    fee_record = payment.fee_record
    student = fee_record.student
    branding = _branding()

    return {
        "payment": payment,
        "fee_record": fee_record,
        "student": student,
        "branding": branding,
        "school_name": (
            getattr(branding, "school_name", None)
            or "School"
        ),
        "motto": getattr(branding, "motto", "") if branding else "",
        "logo": getattr(branding, "logo", None) if branding else None,
        "phone": getattr(branding, "phone", "") if branding else "",
        "email": getattr(branding, "email", "") if branding else "",
        "website": getattr(branding, "website", "") if branding else "",
        "address": getattr(branding, "physical_address", "") if branding else "",
    }



@login_required
@require_GET
def online_payment_stk_query(request, payment_id):
    """
    Server-side STK Query fallback.

    This NEVER creates a FeePayment directly.
    The official callback remains responsible for the final
    M-Pesa receipt and FeePayment creation.
    """
    payment = get_object_or_404(
        OnlinePayment.objects.select_related(
            "fee_record",
            "fee_record__student",
            "fee_record__term",
        ),
        pk=payment_id,
    )

    if not _can_view_payment(request, payment):
        raise Http404()

    if payment.status in (
        "VERIFIED",
        "FAILED",
        "CANCELLED",
        "CANCELED",
    ):
        return JsonResponse({
            "id": payment.id,
            "status": payment.status,
            "message": payment.verification_message or "",
            "mpesa_receipt": payment.provider_receipt or "",
        })

    if not payment.checkout_request_id:
        return JsonResponse({
            "id": payment.id,
            "status": payment.status,
            "message": "M-Pesa CheckoutRequestID is not available yet.",
        })

    try:
        from .services.mpesa import query_stk_push

        result = query_stk_push(
            checkout_request_id=payment.checkout_request_id
        )

        result_code = str(
            result.get("ResultCode", "")
        ).strip()

        result_desc = str(
            result.get("ResultDesc", "")
        ).strip()

        # Keep the provider response for diagnostics.
        payment.provider_response_code = result_code
        payment.provider_response_description = result_desc
        payment.provider_raw_response = result

        # ResultCode 0 means the STK transaction was completed
        # successfully at the query layer. We still wait for the
        # official callback because that contains the M-Pesa receipt.
        if result_code == "0":
            payment.verification_message = (
                "M-Pesa confirms the transaction was completed. "
                "Waiting for the official callback and M-Pesa receipt."
            )

            payment.save(
                update_fields=[
                    "provider_response_code",
                    "provider_response_description",
                    "provider_raw_response",
                    "verification_message",
                    "updated_at",
                ]
            )

            return JsonResponse({
                "id": payment.id,
                "status": payment.status,
                "query_status": "SUCCESS",
                "message": payment.verification_message,
                "mpesa_receipt": payment.provider_receipt or "",
            })

        # ResultCode 4999 means the transaction is still being
        # processed. It MUST remain PROCESSING until the official
        # callback provides the final result.
        if result_code == "4999":
            payment.status = "PROCESSING"
            payment.verification_message = (
                result_desc
                or "M-Pesa transaction is still being processed. "
                   "Waiting for the official callback."
            )

            payment.save(
                update_fields=[
                    "provider_response_code",
                    "provider_response_description",
                    "provider_raw_response",
                    "status",
                    "verification_message",
                    "updated_at",
                ]
            )

            return JsonResponse({
                "id": payment.id,
                "status": payment.status,
                "query_status": "PROCESSING",
                "message": payment.verification_message,
                "mpesa_receipt": payment.provider_receipt or "",
            })

        # Other non-success query results represent unsuccessful
        # STK states.
        payment.status = "FAILED"
        payment.verification_message = (
            result_desc
            or "M-Pesa payment was not completed."
        )

        payment.save(
            update_fields=[
                "provider_response_code",
                "provider_response_description",
                "provider_raw_response",
                "status",
                "verification_message",
                "updated_at",
            ]
        )

        return JsonResponse({
            "id": payment.id,
            "status": payment.status,
            "query_status": "FAILED",
            "message": payment.verification_message,
            "mpesa_receipt": payment.provider_receipt or "",
        })

    except Exception as exc:
        return JsonResponse({
            "id": payment.id,
            "status": payment.status,
            "query_status": "ERROR",
            "message": str(exc),
            "mpesa_receipt": payment.provider_receipt or "",
        }, status=500)


@login_required
def upgraded_online_payment_status(request, payment_id):
    payment = get_object_or_404(
        OnlinePayment.objects.select_related(
            "fee_record",
            "fee_record__student",
            "fee_record__term",
            "fee_payment",
        ),
        pk=payment_id,
    )

    if not _can_view_payment(request, payment):
        raise Http404()

    context = _payment_context(payment)

    fee_payment = payment.fee_payment

    balance = getattr(payment.fee_record, "balance", None)

    data = {
        "id": payment.id,
        "status": payment.status,
        "amount": str(payment.amount),
        "checkout_request_id": payment.checkout_request_id or "",
        "transaction_reference": payment.transaction_reference or "",
        "mpesa_receipt": payment.provider_receipt or "",
        "fee_payment_id": payment.fee_payment_id,
        "school_receipt": (
            fee_payment.receipt_number
            if fee_payment else ""
        ),
        "balance": str(balance) if balance is not None else "",
        "verified_at": (
            payment.verified_at.isoformat()
            if payment.verified_at else ""
        ),
        "message": payment.verification_message or "",
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(data)

    html = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Payment Status - {{ school_name }}</title>
<style>
*{box-sizing:border-box}
body{
    margin:0;
    font-family:Arial,Helvetica,sans-serif;
    background:#f3f6fb;
    color:#172033;
}
.container{
    max-width:900px;
    margin:35px auto;
    padding:20px;
}
.card{
    background:white;
    border-radius:18px;
    box-shadow:0 8px 30px rgba(0,0,0,.09);
    overflow:hidden;
}
.header{
    background:#073b9b;
    color:white;
    padding:28px;
    text-align:center;
}
.header img{
    max-height:75px;
    max-width:180px;
    background:white;
    padding:5px;
    border-radius:8px;
}
.header h1{margin:12px 0 4px;font-size:25px}
.header p{margin:0;opacity:.9}
.body{padding:30px}
.status{
    text-align:center;
    padding:20px;
}
.icon{
    width:78px;
    height:78px;
    border-radius:50%;
    margin:auto;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:42px;
    font-weight:bold;
}
.success .icon{background:#d9f7e5;color:#138a45}
.processing .icon{background:#fff2cc;color:#a66a00}
.failed .icon{background:#ffe0e0;color:#b42318}
.status h2{margin:15px 0 7px}
.grid{
    display:grid;
    grid-template-columns:repeat(2,1fr);
    gap:14px;
    margin-top:25px;
}
.item{
    border:1px solid #e1e6ef;
    border-radius:10px;
    padding:15px;
}
.label{
    font-size:12px;
    color:#697386;
    text-transform:uppercase;
    margin-bottom:5px;
}
.value{
    font-size:17px;
    font-weight:600;
    word-break:break-word;
}
.actions{
    display:flex;
    gap:12px;
    justify-content:center;
    flex-wrap:wrap;
    margin-top:28px;
}
.btn{
    border:0;
    border-radius:9px;
    padding:13px 20px;
    text-decoration:none;
    cursor:pointer;
    font-weight:bold;
    font-size:14px;
}
.primary{background:#073b9b;color:white}
.secondary{background:#e9eef7;color:#172033}
.footer{
    text-align:center;
    color:#697386;
    font-size:13px;
    padding:20px;
    border-top:1px solid #edf0f5;
}
.spinner{
    width:24px;height:24px;
    border:3px solid #ddd;
    border-top-color:#073b9b;
    border-radius:50%;
    animation:spin 1s linear infinite;
    display:inline-block;
    vertical-align:middle;
    margin-right:8px;
}
@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:650px){
    .grid{grid-template-columns:1fr}
    .container{margin:10px auto;padding:10px}
    .body{padding:18px}
}
</style>
</head>
<body>

<div class="container">
<div class="card">

<div class="header">
{% if logo %}
<img src="{{ logo.url }}" alt="School Logo">
{% endif %}
<h1>{{ school_name }}</h1>
{% if motto %}<p>{{ motto }}</p>{% endif %}
</div>

<div class="body">

<div id="paymentStatus" class="status processing">
<div class="icon" id="statusIcon">⌛</div>
<h2 id="statusTitle">Checking payment...</h2>
<p id="statusMessage">Please wait while we confirm your M-Pesa payment.</p>
</div>

<div class="grid">
<div class="item">
<div class="label">Student</div>
<div class="value">{{ student }}</div>
</div>

<div class="item">
<div class="label">Amount</div>
<div class="value">KSh <span id="amount">{{ payment.amount }}</span></div>
</div>

<div class="item">
<div class="label">M-Pesa Receipt</div>
<div class="value" id="mpesaReceipt">—</div>
</div>

<div class="item">
<div class="label">School Receipt</div>
<div class="value" id="schoolReceipt">—</div>
</div>

<div class="item">
<div class="label">Payment Method</div>
<div class="value">Online M-Pesa</div>
</div>

<div class="item">
<div class="label">Current Balance</div>
<div class="value">KSh <span id="balance">—</span></div>
</div>
</div>

<div class="actions" id="actions">
<button class="btn secondary" onclick="refreshPayment()">Refresh Status</button>
</div>

</div>

<div class="footer">
{% if phone %}{{ phone }}{% endif %}
{% if email %} · {{ email }}{% endif %}
{% if address %}<br>{{ address }}{% endif %}
</div>

</div>
</div>

<script>
const PAYMENT_ID = {{ payment.id }};
let timer = null;
let queryTimer = null;
let attempts = 0;
let queryAttempts = 0;

function setText(id, value){
    document.getElementById(id).textContent =
        value || "—";
}

function render(data){
    setText("amount", data.amount);
    setText("mpesaReceipt", data.mpesa_receipt);
    setText("schoolReceipt", data.school_receipt);
    setText("balance", data.balance);

    const box = document.getElementById("paymentStatus");
    const icon = document.getElementById("statusIcon");
    const title = document.getElementById("statusTitle");
    const message = document.getElementById("statusMessage");
    const actions = document.getElementById("actions");

    box.className = "status";

    if (data.status === "VERIFIED"){
        box.classList.add("success");
        icon.textContent = "✓";
        title.textContent = "Payment Successful";
        message.textContent =
            "Your M-Pesa payment has been confirmed successfully.";

        actions.innerHTML = `
            <a class="btn primary"
               href="/fees/online/receipt/${PAYMENT_ID}/">
               View / Print Receipt
            </a>
            <a class="btn secondary"
               href="/fees/online/receipt/${PAYMENT_ID}/pdf/">
               Download PDF Receipt
            </a>
        `;

        stopTimers();
        return;
    }

    if(
        data.status === "FAILED" ||
        data.status === "CANCELLED" ||
        data.status === "CANCELED"
    ){
        box.classList.add("failed");
        icon.textContent = "!";
        title.textContent = "Payment Not Completed";
        message.textContent =
            data.message || "The M-Pesa payment was not completed.";

        actions.innerHTML = `
            <button class="btn secondary"
                    onclick="refreshPayment()">
                Check Again
            </button>
        `;

        stopTimers();
        return;
    }

    box.classList.add("processing");
    icon.innerHTML = '<span class="spinner"></span>';
    title.textContent = "Payment Processing";
    message.textContent =
        data.message ||
        "Waiting for M-Pesa payment confirmation.";

    actions.innerHTML = `
        <button class="btn secondary"
                onclick="refreshPayment()">
            Refresh Status
        </button>
    `;
}


async function queryMpesa(){
    try{
        queryAttempts++;

        const response = await fetch(
            `/fees/online/status/${PAYMENT_ID}/query/`,
            {
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                cache: "no-store"
            }
        );

        if(!response.ok) return;

        const data = await response.json();

        if(data.status === "VERIFIED"){
            render(data);
            stopTimers();
            return;
        }

        if(
            data.status === "FAILED" ||
            data.status === "CANCELLED" ||
            data.status === "CANCELED"
        ){
            render(data);
            stopTimers();
            return;
        }

        if(data.query_status === "SUCCESS"){
            const message =
                data.message ||
                "M-Pesa confirms the transaction. Waiting for the official receipt.";

            document.getElementById("statusMessage").textContent =
                message;
        }

    }catch(error){
        console.error("STK Query error:", error);
    }
}

function stopTimers(){
    if(timer) clearInterval(timer);
    if(queryTimer) clearInterval(queryTimer);
    timer = null;
    queryTimer = null;
}

async function refreshPayment(){
    try{
        const response = await fetch(
            `/fees/online/status/${PAYMENT_ID}/`,
            {
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                cache: "no-store"
            }
        );

        if(!response.ok) return;

        const data = await response.json();
        render(data);

        attempts++;

        if(
            data.status === "VERIFIED" ||
            data.status === "FAILED" ||
            data.status === "CANCELLED" ||
            data.status === "CANCELED"
        ){
            if(timer) clearInterval(timer);
        }
    }catch(error){
        console.error(error);
    }
}

refreshPayment();

/*
   Database status is checked every 3 seconds.

   Daraja STK Query is deliberately slower so we do not hammer
   Safaricom with requests.
*/
timer = setInterval(refreshPayment, 3000);

setTimeout(() => {
    queryMpesa();
    queryTimer = setInterval(queryMpesa, 15000);
}, 15000);
</script>

</body>
</html>
"""

    from django.template import engines
    template = engines["django"].from_string(html)
    return HttpResponse(template.render(context, request))


@login_required

def online_payment_receipt(request, payment_id):
    """
    Online M-Pesa payments use the SAME receipt generated by the
    normal FeePayment receipt system.

    This deliberately does not create a second receipt design.
    """
    from django.shortcuts import redirect

    payment = get_object_or_404(
        OnlinePayment.objects.select_related(
            "fee_record",
            "fee_record__student",
            "fee_record__term",
            "fee_payment",
        ),
        pk=payment_id,
    )

    if not _can_view_payment(request, payment):
        raise Http404()

    if payment.status != "VERIFIED" or not payment.fee_payment_id:
        return HttpResponse(
            "Receipt is not available until the M-Pesa payment is verified.",
            status=409,
        )

    # Use the exact existing ERP receipt page.
    return redirect(
        "fees:print_receipt",
        payment.fee_payment_id,
    )


@login_required
def online_payment_receipt_pdf(request, payment_id):
    """
    Online M-Pesa PDF downloads use the SAME existing ERP receipt
    download/print system instead of generating a second PDF design.
    """
    from django.shortcuts import redirect
    from django.urls import reverse, NoReverseMatch

    payment = get_object_or_404(
        OnlinePayment.objects.select_related(
            "fee_record",
            "fee_record__student",
            "fee_record__term",
            "fee_payment",
        ),
        pk=payment_id,
    )

    if not _can_view_payment(request, payment):
        raise Http404()

    if payment.status != "VERIFIED" or not payment.fee_payment_id:
        return HttpResponse(
            "Receipt is not available until the M-Pesa payment is verified.",
            status=409,
        )

    fee_payment_id = payment.fee_payment_id

    # Try the existing ERP receipt/download route names.
    route_names = [
        "fees:download_receipt",
        "fees:receipt_pdf",
        "fees:print_receipt_pdf",
        "fees:print_receipt",
    ]

    for route_name in route_names:
        try:
            url = reverse(
                route_name,
                args=[fee_payment_id],
            )

            # Preserve the user's requested download mode where
            # the existing route supports it.
            if route_name != "fees:print_receipt":
                return redirect(url)

        except NoReverseMatch:
            continue

    # Guaranteed fallback to the existing receipt page.
    return redirect(
        "fees:print_receipt",
        fee_payment_id,
    )
