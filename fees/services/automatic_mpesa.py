import base64
from datetime import datetime
import requests

from django.conf import settings

from ..models import AutomaticPaymentSettings


class AutomaticMpesaError(Exception):
    pass


def get_config():
    config = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not config:
        raise AutomaticMpesaError(
            "Automatic M-Pesa settings have not been configured."
        )

    if not config.is_active:
        raise AutomaticMpesaError(
            "Automatic payments are currently disabled."
        )

    return config


def _get_credentials(method):
    config = get_config()

    method = str(method).upper()

    if method == "MPESA_PAYBILL":
        shortcode = config.mpesa_paybill_shortcode
        consumer_key = config.mpesa_paybill_consumer_key
        consumer_secret = config.mpesa_paybill_consumer_secret
        passkey = config.mpesa_paybill_passkey
        callback_url = config.mpesa_paybill_confirmation_url

        if not callback_url:
            callback_url = config.mpesa_online_callback_url

        till_number = ""

        transaction_type = "CustomerPayBillOnline"
        party_b = shortcode

    elif method == "MPESA_ONLINE":
        shortcode = config.mpesa_online_shortcode
        consumer_key = config.mpesa_online_consumer_key
        consumer_secret = config.mpesa_online_consumer_secret
        passkey = config.mpesa_online_passkey
        callback_url = config.mpesa_online_callback_url

        till_number = ""

        transaction_type = "CustomerPayBillOnline"
        party_b = shortcode

    elif method == "MPESA_TILL":
        # ----------------------------------------------------
        # Till is completely database-driven.
        # Nothing here depends on ALTERNATE_MPESA_TILL.
        # ----------------------------------------------------
        till_number = str(
            config.mpesa_till_number or ""
        ).strip()

        shortcode = (
            config.mpesa_till_shortcode
            or till_number
        )

        consumer_key = config.mpesa_till_consumer_key
        consumer_secret = config.mpesa_till_consumer_secret
        passkey = config.mpesa_till_passkey
        callback_url = config.mpesa_till_callback_url

        # Buy Goods / Till STK request
        transaction_type = "CustomerBuyGoodsOnline"
        party_b = till_number

    else:
        raise AutomaticMpesaError(
            "This automatic M-Pesa payment method is not supported."
        )

    missing = []

    if not shortcode:
        missing.append("Short Code")
    if not consumer_key:
        missing.append("Consumer Key")
    if not consumer_secret:
        missing.append("Consumer Secret")
    if not passkey:
        missing.append("Passkey")
    if not callback_url:
        missing.append("Callback URL")

    if method == "MPESA_TILL" and not till_number:
        missing.append("Till Number")

    if missing:
        raise AutomaticMpesaError(
            f"{method} automatic payment is not fully configured. "
            "Missing: " + ", ".join(missing)
        )

    return {
        "shortcode": shortcode,
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
        "passkey": passkey,
        "callback_url": callback_url,
        "environment": config.environment or "sandbox",
        "transaction_type": transaction_type,
        "party_b": party_b,
        "till_number": till_number,
    }


def _base_url(environment):
    if str(environment).lower() == "production":
        return "https://api.safaricom.co.ke"
    return "https://sandbox.safaricom.co.ke"


def _access_token(credentials):
    url = _base_url(credentials["environment"]) + "/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        auth=(
            credentials["consumer_key"],
            credentials["consumer_secret"],
        ),
        timeout=30,
    )

    if response.status_code != 200:
        raise AutomaticMpesaError(
            f"M-Pesa authentication failed: HTTP {response.status_code}"
        )

    data = response.json()
    token = data.get("access_token")

    if not token:
        raise AutomaticMpesaError(
            "M-Pesa authentication succeeded but no access token was returned."
        )

    return token


def _format_phone(phone):
    phone = str(phone).strip()

    if phone.startswith("+254"):
        return phone[1:]

    if phone.startswith("254"):
        return phone

    if phone.startswith("0"):
        return "254" + phone[1:]

    return phone


def initiate_automatic_stk_push(
    *,
    phone_number,
    amount,
    method="MPESA_ONLINE",
    account_reference="SCHOOLFEES",
    transaction_desc="School Fees Payment",
):
    credentials = _get_credentials(method)

    token = _access_token(credentials)

    shortcode = str(credentials["shortcode"])

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password_raw = (
        shortcode
        + credentials["passkey"]
        + timestamp
    )

    password = base64.b64encode(
        password_raw.encode("utf-8")
    ).decode("utf-8")

    phone = _format_phone(phone_number)

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": credentials["transaction_type"],
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": credentials["party_b"],
        "PhoneNumber": phone,
        "CallBackURL": credentials["callback_url"],
        "AccountReference": str(account_reference)[:12],
        "TransactionDesc": str(transaction_desc)[:13],
    }

    url = (
        _base_url(credentials["environment"])
        + "/mpesa/stkpush/v1/processrequest"
    )

    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    try:
        data = response.json()
    except Exception:
        data = {
            "ResponseDescription": response.text
        }

    if response.status_code not in (200, 201):
        raise AutomaticMpesaError(
            data.get(
                "errorMessage",
                data.get(
                    "ResponseDescription",
                    f"M-Pesa STK request failed: HTTP {response.status_code}",
                ),
            )
        )

    if data.get("ResponseCode") not in (None, "0", 0):
        raise AutomaticMpesaError(
            data.get(
                "ResponseDescription",
                "M-Pesa rejected the STK request.",
            )
        )

    return data
