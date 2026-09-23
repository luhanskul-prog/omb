
from __future__ import annotations

import base64
import json
from datetime import datetime
from decimal import Decimal

import requests
from django.utils import timezone

from .models import AutomaticPaymentSettings


BANK_PROFILES = {
    "CO-OPERATIVE BANK": {
        "code": "COOP",
        "display_name": "Co-operative Bank",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "ACCOUNT_VALIDATION",
            "INSTANT_TRANSACTION_NOTIFICATION",
        ],
        "requires_bank_credentials": True,
    },

    "KCB BANK KENYA": {
        "code": "KCB",
        "display_name": "KCB Bank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "ACCOUNT_VALIDATION",
            "INSTANT_PAYMENT_NOTIFICATION",
        ],
        "requires_bank_credentials": True,
    },

    "EQUITY BANK KENYA": {
        "code": "EQUITY",
        "display_name": "Equity Bank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "ACCOUNT_VALIDATION",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "NCBA BANK KENYA": {
        "code": "NCBA",
        "display_name": "NCBA Bank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "ACCOUNT_VALIDATION",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "ABSA BANK KENYA": {
        "code": "ABSA",
        "display_name": "Absa Bank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "ACCOUNT_VALIDATION",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "STANDARD CHARTERED BANK KENYA": {
        "code": "SCB",
        "display_name": "Standard Chartered Bank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "ACCOUNT_VALIDATION",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "STANBIC BANK KENYA": {
        "code": "STANBIC",
        "display_name": "Stanbic Bank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "ACCOUNT_VALIDATION",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "I&M BANK KENYA": {
        "code": "IM",
        "display_name": "I&M Bank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "ACCOUNT_VALIDATION",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "DIAMOND TRUST BANK (DTB)": {
        "code": "DTB",
        "display_name": "Diamond Trust Bank",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "ACCOUNT_VALIDATION",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "FAMILY BANK": {
        "code": "FAMILY",
        "display_name": "Family Bank",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "PRIME BANK KENYA": {
        "code": "PRIME",
        "display_name": "Prime Bank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "BANK OF AFRICA KENYA": {
        "code": "BOA",
        "display_name": "Bank of Africa Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "ECOBANK KENYA": {
        "code": "ECOBANK",
        "display_name": "Ecobank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "SIDIAN BANK": {
        "code": "SIDIAN",
        "display_name": "Sidian Bank",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "SBM BANK KENYA": {
        "code": "SBM",
        "display_name": "SBM Bank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "KINGDOM BANK": {
        "code": "KINGDOM",
        "display_name": "Kingdom Bank",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "ACCESS BANK KENYA": {
        "code": "ACCESS",
        "display_name": "Access Bank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },

    "CITIBANK KENYA": {
        "code": "CITI",
        "display_name": "Citibank Kenya",
        "auth": ["OAUTH 2.0", "API KEY", "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
    },
}


def normalize_bank_name(name):
    value = (name or "").strip().upper()

    aliases = {
        "CO-OP BANK": "CO-OPERATIVE BANK",
        "COOPERATIVE BANK": "CO-OPERATIVE BANK",
        "CO-OPERATIVE BANK OF KENYA": "CO-OPERATIVE BANK",
        "KCB": "KCB BANK KENYA",
        "EQUITY": "EQUITY BANK KENYA",
        "NCBA": "NCBA BANK KENYA",
        "ABSA": "ABSA BANK KENYA",
        "STANBIC": "STANBIC BANK KENYA",
        "I&M": "I&M BANK KENYA",
        "DTB": "DIAMOND TRUST BANK (DTB)",
    }

    return aliases.get(value, value)


def get_bank_profile(settings=None):
    if settings is None:
        settings = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not settings:
        return None

    bank_name = normalize_bank_name(settings.bank_name)

    profile = BANK_PROFILES.get(bank_name)

    if profile:
        result = dict(profile)
        result["configured"] = True
        result["bank_name"] = settings.bank_name
        return result

    return {
        "code": "CUSTOM",
        "display_name": settings.bank_name or "Other Bank",
        "auth": ["OAUTH 2.0", "API KEY", "BASIC AUTHENTICATION",
                 "BEARER TOKEN", "CUSTOM"],
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "WEBHOOK",
        ],
        "requires_bank_credentials": True,
        "configured": True,
        "bank_name": settings.bank_name,
    }



def normalize_authentication_method(value):
    value = (value or "").strip().upper()

    aliases = {
        "OAUTH2": "OAUTH 2.0",
        "OAUTH 2": "OAUTH 2.0",
        "OAUTH": "OAUTH 2.0",
        "OAUTH 2.0": "OAUTH 2.0",

        "APIKEY": "API KEY",
        "API-KEY": "API KEY",
        "API KEY": "API KEY",

        "BASIC": "BASIC AUTHENTICATION",
        "BASIC AUTH": "BASIC AUTHENTICATION",
        "BASIC AUTHENTICATION": "BASIC AUTHENTICATION",

        "BEARER": "BEARER TOKEN",
        "BEARER TOKEN": "BEARER TOKEN",

        "CUSTOM": "CUSTOM",
    }

    return aliases.get(value, value)


def required_configuration(settings):
    missing = []

    if not settings.bank_name:
        missing.append("Bank")

    if not settings.bank_account_number:
        missing.append("Account Number")

    if not settings.bank_transaction_endpoint:
        missing.append("Transaction Endpoint")

    auth = (
        getattr(settings, "bank_authentication_method", "") or ""
    ).upper()

    if auth == "OAUTH 2.0":
        if not settings.bank_client_id:
            missing.append("Client ID")
        if not settings.bank_client_secret:
            missing.append("Client Secret")
        if not settings.bank_access_token_url:
            missing.append("Access Token URL")

    elif auth == "API KEY":
        if not settings.bank_api_key:
            missing.append("API Key")

    elif auth == "BASIC AUTHENTICATION":
        if not settings.bank_client_id:
            missing.append("Username / Client ID")
        if not settings.bank_client_secret:
            missing.append("Password / Secret")

    elif auth == "BEARER TOKEN":
        if not settings.bank_api_key and not settings.bank_client_secret:
            missing.append("Bearer Token")

    return missing


def _json_headers(settings, token=None):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    auth = (
        getattr(settings, "bank_authentication_method", "") or ""
    ).upper()

    if auth == "BEARER TOKEN" and token:
        headers["Authorization"] = f"Bearer {token}"

    elif auth == "API KEY" and settings.bank_api_key:
        headers["X-API-Key"] = settings.bank_api_key

    return headers


def _get_oauth_token(settings):
    response = requests.post(
        settings.bank_access_token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.bank_client_id,
            "client_secret": settings.bank_client_secret,
        },
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    token = (
        data.get("access_token")
        or data.get("token")
        or data.get("accessToken")
    )

    if not token:
        raise RuntimeError(
            "Bank OAuth response did not contain an access token."
        )

    return token


def build_request_headers(settings):
    auth = (
        getattr(settings, "bank_authentication_method", "") or ""
    ).upper()

    token = None

    if auth == "OAUTH 2.0":
        token = _get_oauth_token(settings)

    return _json_headers(settings, token)


def fetch_transactions_from_configured_bank(settings=None):
    if settings is None:
        settings = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not settings:
        raise RuntimeError("Bank automatic payment settings are missing.")

    missing = required_configuration(settings)

    if missing:
        raise RuntimeError(
            "Bank integration is incomplete: " + ", ".join(missing)
        )

    profile = get_bank_profile(settings)

    headers = build_request_headers(settings)

    auth = (
        getattr(settings, "bank_authentication_method", "") or ""
    ).upper()

    kwargs = {
        "headers": headers,
        "timeout": 45,
    }

    if auth == "BASIC AUTHENTICATION":
        kwargs["auth"] = (
            settings.bank_client_id,
            settings.bank_client_secret,
        )

    endpoint = settings.bank_transaction_endpoint

    response = requests.get(endpoint, **kwargs)

    if response.status_code >= 400:
        raise RuntimeError(
            f"{profile['display_name']} transaction API returned "
            f"HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    try:
        data = response.json()
    except Exception:
        raise RuntimeError(
            f"{profile['display_name']} transaction API returned "
            "a non-JSON response."
        )

    return {
        "bank": profile["display_name"],
        "bank_code": profile["code"],
        "capabilities": profile["capabilities"],
        "payload": data,
        "raw_response": response.text,
    }


def get_bank_integration_status(settings=None):
    if settings is None:
        settings = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not settings:
        return {
            "status": "NOT_CONFIGURED",
            "label": "Not Configured",
            "message": "Bank settings do not exist.",
        }

    if not settings.is_active:
        return {
            "status": "DISABLED",
            "label": "Disabled",
            "message": "Automatic payments are disabled.",
        }

    if not settings.bank_enabled:
        return {
            "status": "DISABLED",
            "label": "Bank Disabled",
            "message": "Bank automatic verification is disabled.",
        }

    missing = required_configuration(settings)

    if missing:
        return {
            "status": "NOT_CONFIGURED",
            "label": "Not Configured",
            "message": "Missing: " + ", ".join(missing),
        }

    existing = getattr(settings, "bank_verification_status", "") or ""

    if existing.startswith("CONNECTION OK"):
        return {
            "status": "CONNECTED",
            "label": "Connected",
            "message": existing,
        }

    if existing.startswith("CONNECTION FAILED"):
        return {
            "status": "FAILED",
            "label": "Connection Failed",
            "message": existing,
        }

    return {
        "status": "CONFIGURED",
        "label": "Configuration Complete",
        "message": "Credentials and required endpoints are configured.",
    }


def get_bank_endpoint(settings, endpoint_type="transactions"):
    field_map = {
        "transactions": "bank_transaction_endpoint",
        "transaction": "bank_transaction_endpoint",
        "validation": "bank_account_validation_endpoint",
        "statement": "bank_statement_endpoint",
        "balance": "bank_balance_endpoint",
        "webhook": "bank_webhook_url",
        "api": "bank_api_url",
    }

    field = field_map.get(endpoint_type)

    if not field:
        raise ValueError(
            f"Unsupported bank endpoint type: {endpoint_type}"
        )

    value = (getattr(settings, field, "") or "").strip()

    # Backward compatibility with configurations that used
    # bank_api_url as the transaction endpoint.
    if endpoint_type in ("transactions", "transaction") and not value:
        value = (getattr(settings, "bank_api_url", "") or "").strip()

    return value



def bank_supports(settings, capability):
    profile = get_bank_profile(settings)

    capabilities = [
        str(item).upper()
        for item in profile.get("capabilities", [])
    ]

    return str(capability).upper() in capabilities


def get_supported_banks():
    return [
        {
            "name": name,
            "code": profile.get("code"),
            "display_name": profile.get("display_name"),
            "capabilities": profile.get("capabilities", []),
        }
        for name, profile in BANK_PROFILES.items()
    ]


def get_supported_bank_codes():
    return {
        profile.get("code"): name
        for name, profile in BANK_PROFILES.items()
    }


def get_safe_bank_configuration(settings):
    profile = get_bank_profile(settings)

    return {
        "bank": profile.get("display_name"),
        "bank_code": profile.get("code"),
        "environment": getattr(settings, "environment", ""),
        "enabled": bool(getattr(settings, "bank_enabled", False)),
        "automatic_payments_enabled": bool(
            getattr(settings, "is_active", False)
        ),
        "account_number": getattr(
            settings, "bank_account_number", ""
        ),
        "account_name": getattr(
            settings, "bank_account_name", ""
        ),
        "account_type": getattr(
            settings, "bank_account_type", ""
        ),
        "currency": getattr(
            settings, "bank_currency", ""
        ),
        "authentication_method": normalize_authentication_method(
            getattr(settings, "bank_authentication_method", "")
        ),
        "transaction_endpoint_configured": bool(
            get_bank_endpoint(settings, "transactions")
        ),
        "validation_endpoint_configured": bool(
            get_bank_endpoint(settings, "validation")
        ),
        "statement_endpoint_configured": bool(
            get_bank_endpoint(settings, "statement")
        ),
        "balance_endpoint_configured": bool(
            get_bank_endpoint(settings, "balance")
        ),
        "webhook_configured": bool(
            get_bank_endpoint(settings, "webhook")
        ),
        "integration_status": get_bank_integration_status(settings),
    }



def get_generic_bank_profile(bank_name):
    name = (bank_name or "").strip()

    return {
        "code": "CUSTOM",
        "display_name": name or "Custom Bank",
        "capabilities": [
            "ACCOUNT_TRANSACTIONS",
            "ACCOUNT_STATEMENT",
            "ACCOUNT_VALIDATION",
            "WEBHOOK",
        ],
    }

