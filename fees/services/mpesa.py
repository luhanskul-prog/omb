
import base64
from datetime import datetime
from typing import Any

import requests
from django.conf import settings


class MpesaError(Exception):
    """Raised when an M-Pesa/Daraja operation fails."""


def _base_url():
    environment = getattr(
        settings,
        "MPESA_ENVIRONMENT",
        "sandbox",
    ).lower()

    if environment == "production":
        return "https://api.safaricom.co.ke"

    return "https://sandbox.safaricom.co.ke"


def _require_setting(name):
    value = getattr(settings, name, "").strip()

    if not value:
        raise MpesaError(
            f"{name} is not configured."
        )

    return value


def get_access_token():
    consumer_key = _require_setting(
        "MPESA_CONSUMER_KEY"
    )

    consumer_secret = _require_setting(
        "MPESA_CONSUMER_SECRET"
    )

    url = (
        _base_url()
        + "/oauth/v1/generate?grant_type=client_credentials"
    )

    try:
        response = requests.get(
            url,
            auth=(
                consumer_key,
                consumer_secret,
            ),
            timeout=30,
        )
    except requests.RequestException as exc:
        raise MpesaError(
            f"Unable to contact Daraja: {exc}"
        ) from exc

    if response.status_code != 200:
        raise MpesaError(
            "Daraja OAuth failed: "
            f"HTTP {response.status_code}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise MpesaError(
            "Daraja returned an invalid OAuth response."
        ) from exc

    token = data.get("access_token")

    if not token:
        raise MpesaError(
            "Daraja OAuth response did not contain an access token."
        )

    return token


def generate_password(timestamp=None):
    shortcode = _require_setting(
        "MPESA_SHORTCODE"
    )

    passkey = _require_setting(
        "MPESA_PASSKEY"
    )

    if timestamp is None:
        timestamp = datetime.now().strftime(
            "%Y%m%d%H%M%S"
        )

    raw = (
        shortcode
        + passkey
        + timestamp
    )

    password = base64.b64encode(
        raw.encode("utf-8")
    ).decode("utf-8")

    return password, timestamp


def format_phone_number(phone):
    digits = "".join(
        character
        for character in str(phone)
        if character.isdigit()
    )

    if digits.startswith("254"):
        return digits

    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]

    if digits.startswith("7") and len(digits) == 9:
        return "254" + digits

    if digits.startswith("1") and len(digits) == 9:
        return "254" + digits

    raise MpesaError(
        "Invalid Kenyan M-Pesa phone number."
    )


def initiate_stk_push(
    *,
    phone_number,
    amount,
    account_reference,
    transaction_desc=None,
):
    token = get_access_token()

    shortcode = _require_setting(
        "MPESA_SHORTCODE"
    )

    callback_url = _require_setting(
        "MPESA_CALLBACK_URL"
    )

    password, timestamp = generate_password()

    phone = format_phone_number(
        phone_number
    )

    if transaction_desc is None:
        transaction_desc = getattr(
            settings,
            "MPESA_TRANSACTION_DESC",
            "School Fees Payment",
        )

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc,
    }

    url = (
        _base_url()
        + "/mpesa/stkpush/v1/processrequest"
    )

    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise MpesaError(
            f"Unable to contact Daraja STK endpoint: {exc}"
        ) from exc

    try:
        data: Any = response.json()
    except ValueError as exc:
        raise MpesaError(
            "Daraja returned an invalid STK response."
        ) from exc

    if response.status_code != 200:
        raise MpesaError(
            "Daraja STK request failed: "
            f"HTTP {response.status_code}"
        )

    return data


def query_stk_push(*, checkout_request_id):
    """
    Query the status of an existing Lipa na M-Pesa Online STK Push.
    Returns the raw Daraja response.
    """
    checkout_request_id = str(checkout_request_id or "").strip()

    if not checkout_request_id:
        raise MpesaError(
            "CheckoutRequestID is required for STK Query."
        )

    token = get_access_token()

    shortcode = _require_setting(
        "MPESA_SHORTCODE"
    )

    password, timestamp = generate_password()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }

    url = (
        _base_url()
        + "/mpesa/stkpushquery/v1/query"
    )

    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise MpesaError(
            f"Unable to contact Daraja STK Query endpoint: {exc}"
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise MpesaError(
            "Daraja returned an invalid STK Query response."
        ) from exc

    if response.status_code != 200:
        raise MpesaError(
            "Daraja STK Query failed: "
            f"HTTP {response.status_code}"
        )

    return data
