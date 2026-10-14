"""Settings and secrets for the Lambda handlers (Owner B).

Secrets live in SSM Parameter Store under SSM_PREFIX (default /semak/dev):
  wa_token  wa_phone_number_id  wa_app_secret  wa_verify_token
  tg_token  tg_secret  report_pepper
Missing parameters are allowed (e.g. no Telegram yet): they come back as "".
"""

from __future__ import annotations

import functools
import hashlib
import json
import os

PARAM_NAMES = ("wa_token", "wa_phone_number_id", "wa_app_secret", "wa_verify_token",
               "tg_token", "tg_secret", "report_pepper")


@functools.lru_cache(maxsize=1)
def secrets() -> dict[str, str]:
    """Read all parameters once per cold start."""
    if os.environ.get("SECRETS_JSON"):                 # tests and local runs
        return json.loads(os.environ["SECRETS_JSON"])
    import boto3
    prefix = os.environ.get("SSM_PREFIX", "/semak/dev").rstrip("/")
    ssm = boto3.client("ssm")
    found: dict[str, str] = {}
    paginator = ssm.get_paginator("get_parameters_by_path")
    for page in paginator.paginate(Path=prefix, WithDecryption=True):
        for p in page["Parameters"]:
            found[p["Name"].rsplit("/", 1)[-1]] = p["Value"]
    return {name: found.get(name, "") for name in PARAM_NAMES}


@functools.lru_cache(maxsize=None)
def channel(name: str):
    """The Channel object for "wa" or "tg"."""
    s = secrets()
    if name == "wa":
        from channels.whatsapp import WhatsAppChannel
        return WhatsAppChannel(s["wa_token"], s["wa_phone_number_id"],
                               s["wa_app_secret"], s["wa_verify_token"],
                               os.environ.get("WA_API_VERSION", "v21.0"))
    if name == "tg":
        from channels.telegram import TelegramChannel
        return TelegramChannel(s["tg_token"], s["tg_secret"])
    raise ValueError(f"unknown channel {name}")


def log(event: str, **fields) -> None:
    """One JSON line per log. Never pass names, payloads or phone numbers (DR-09)."""
    print(json.dumps({"event": event, **fields}, default=str))


def short_hash(value: str) -> str:
    """First 8 hex chars of a SHA-256, for logging user ids safely."""
    return hashlib.sha256(value.encode()).hexdigest()[:8]
