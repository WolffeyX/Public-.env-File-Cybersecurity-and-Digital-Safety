"""Worker Lambda: SQS -> core.flows.handle_event -> send + schedule (Owner B). SDD 2.2, 10.

Triggered by BOTH queues (events FIFO and timers). Batch size 1.
Delivery is at-most-once by design: handle_event marks each msg_id as seen
before acting, so a retry never sends a senior the same verdict twice.
Failures are logged (CloudWatch alarm on "worker.error").
"""

from __future__ import annotations

import json
import os
import time
import uuid

from core.types import Deps, InboundEvent, Outbound, Task
from handlers.config import channel, log, secrets, short_hash

_store = None
_sqs = None


def store():
    global _store
    if _store is None:
        if os.environ.get("STORE") == "memory":
            from core.store import InMemoryStore
            _store = InMemoryStore()
        else:
            from core.store import DynamoStore
            _store = DynamoStore()
    return _store


def sqs():
    global _sqs
    if _sqs is None:
        import boto3
        _sqs = boto3.client("sqs")
    return _sqs


def new_id() -> str:
    """Time-sortable short id (fits Telegram's 64-byte button limit)."""
    return f"{int(time.time() * 1000):013d}{uuid.uuid4().hex[:8]}"


def make_deps() -> Deps:
    from core.classify import decode_and_classify
    pepper = secrets()["report_pepper"].encode()

    def fetch_media(user_id: str, media_ref: str) -> bytes:
        return channel(user_id.split(":", 1)[0]).fetch_media(media_ref)

    return Deps(fetch_media=fetch_media,
                decode_image=lambda b: decode_and_classify(b, pepper),
                now=time.time, new_id=new_id, pepper=pepper)


def schedule(task: Task) -> None:
    ev = InboundEvent(channel=task.user_id.split(":", 1)[0], user_id=task.user_id,
                      msg_id=f"task:{task.task}:{task.ref}:{new_id()}", kind="task",
                      ts=time.time(), task=task.task, ref=task.ref)
    body = json.dumps(ev.__dict__)
    if task.delay_s <= 0:
        sqs().send_message(QueueUrl=os.environ["EVENTS_QUEUE_URL"], MessageBody=body,
                           MessageGroupId=task.user_id, MessageDeduplicationId=ev.msg_id[:128])
    else:
        sqs().send_message(QueueUrl=os.environ["TIMERS_QUEUE_URL"], MessageBody=body,
                           DelaySeconds=min(task.delay_s, 900))


def dispatch(results: list[Outbound | Task]) -> None:
    for r in results:
        if isinstance(r, Outbound):
            channel(r.to.split(":", 1)[0]).send(r)
        elif isinstance(r, Task):
            schedule(r)


def handler(event, context):
    from core.flows import handle_event
    deps = make_deps()
    for record in event.get("Records", []):
        try:
            ev = InboundEvent(**json.loads(record["body"]))
        except Exception as e:                      # malformed message: drop it
            log("worker.bad_message", error=str(e))
            continue
        started = time.time()
        try:
            results = handle_event(ev, store(), deps)
            dispatch(results)
            log("worker.done", kind=ev.kind, task=ev.task, user=short_hash(ev.user_id),
                outputs=len(results), ms=int((time.time() - started) * 1000))
        except Exception as e:
            log("worker.error", kind=ev.kind, task=ev.task, user=short_hash(ev.user_id),
                error=type(e).__name__, detail=str(e)[:200])
    return {"ok": True}
