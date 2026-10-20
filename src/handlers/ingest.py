"""Ingest Lambda: API Gateway -> verify -> SQS FIFO (Owner B). SDD 2.2, 4.4.

Must answer fast: no decoding or database work here.
Route: POST /tg.
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
import os

from handlers.config import channel, log

_sqs = None


def sqs():
    global _sqs
    if _sqs is None:
        import boto3
        _sqs = boto3.client("sqs")
    return _sqs


def _resp(status: int, body: str = "") -> dict:
    return {"statusCode": status, "headers": {"content-type": "text/plain"}, "body": body}


def handler(event, context):
    method = event["requestContext"]["http"]["method"]
    path = event.get("rawPath", "")
    name = "tg" if path.endswith("/tg") else None
    if name is None:
        return _resp(404)

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    query = event.get("queryStringParameters") or {}
    raw = event.get("body") or ""
    raw_body = base64.b64decode(raw) if event.get("isBase64Encoded") else raw.encode()
    ch = channel(name)

    if method != "POST":
        return _resp(405)
    if not ch.verify(headers, raw_body, query):
        log("ingest.rejected", channel=name)
        return _resp(401)

    events = ch.parse(raw_body)
    for ev in events:
        sqs().send_message(
            QueueUrl=os.environ["EVENTS_QUEUE_URL"],
            MessageBody=json.dumps(dataclasses.asdict(ev)),
            MessageGroupId=ev.user_id,
            MessageDeduplicationId=hashlib.sha256(ev.msg_id.encode()).hexdigest(),
        )
    log("ingest.queued", channel=name, count=len(events))
    return _resp(200, "ok")
