"""Ingest and worker glue, tested with moto (fake AWS) and a stub channel. Owner B."""

import base64
import json
import os

import boto3
import pytest
from moto import mock_aws

from core.types import InboundEvent, Outbound, Task

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-1")
os.environ["SECRETS_JSON"] = json.dumps({"report_pepper": "p"})


class StubChannel:
    name = "tg"

    def __init__(self):
        self.sent = []

    def verify(self, headers, raw_body, query):
        return headers.get("x-telegram-bot-api-secret-token") == "good"

    def parse(self, raw_body):
        body = json.loads(raw_body)
        return [InboundEvent(channel="tg", user_id="tg:601", msg_id=body["id"], kind="text",
                             ts=1.0, text=body["text"])]

    def send(self, msg):
        self.sent.append(msg)

    def fetch_media(self, ref):
        return b""


@pytest.fixture
def aws(monkeypatch):
    with mock_aws():
        sqs = boto3.client("sqs")
        events = sqs.create_queue(QueueName="e.fifo", Attributes={"FifoQueue": "true"})["QueueUrl"]
        timers = sqs.create_queue(QueueName="t")["QueueUrl"]
        monkeypatch.setenv("EVENTS_QUEUE_URL", events)
        monkeypatch.setenv("TIMERS_QUEUE_URL", timers)
        stub = StubChannel()
        import handlers.ingest as ingest
        import handlers.worker as worker
        monkeypatch.setattr(ingest, "channel", lambda name: stub)
        monkeypatch.setattr(worker, "channel", lambda name: stub)
        ingest._sqs = worker._sqs = None
        yield sqs, events, timers, stub, ingest, worker


def http(method, path, body="", headers=None, query=None, b64=False):
    return {"requestContext": {"http": {"method": method}}, "rawPath": path,
            "headers": headers or {}, "queryStringParameters": query,
            "body": base64.b64encode(body.encode()).decode() if b64 else body,
            "isBase64Encoded": b64}


def test_unknown_path_is_404(aws):
    *_, ingest, _ = aws
    assert ingest.handler(http("POST", "/wa", "{}"), None)["statusCode"] == 404


def test_bad_signature_is_rejected_and_not_queued(aws):
    sqs, events, *_ , ingest, _ = aws
    r = ingest.handler(http("POST", "/tg", json.dumps({"id": "x", "text": "hi"}),
                            headers={"X-Telegram-Bot-Api-Secret-Token": "evil"}), None)
    assert r["statusCode"] == 401
    assert "Messages" not in sqs.receive_message(QueueUrl=events)


def test_base64_body_is_queued_with_user_group(aws):
    sqs, events, *_ , ingest, _ = aws
    r = ingest.handler(http("POST", "/tg", json.dumps({"id": "m1", "text": "Daftar"}),
                            headers={"X-Telegram-Bot-Api-Secret-Token": "good"}, b64=True), None)
    assert r["statusCode"] == 200
    msg = sqs.receive_message(QueueUrl=events, AttributeNames=["MessageGroupId"])["Messages"][0]
    assert json.loads(msg["Body"])["text"] == "Daftar"
    assert msg["Attributes"]["MessageGroupId"] == "tg:601"


def test_worker_sends_outbound_and_schedules_tasks(aws, monkeypatch):
    sqs, events, timers, stub, _, worker = aws
    import core.flows as flows
    monkeypatch.setattr(flows, "handle_event", lambda ev, store, deps: [
        Outbound(to="tg:601", text="hello"),
        Task("decode", "tg:601", "c1", 0),
        Task("reminder", "tg:601", "c1", 120),
    ])
    monkeypatch.setenv("STORE", "memory")
    body = json.dumps(InboundEvent("tg", "tg:601", "m9", "text", 1.0, text="x").__dict__)
    worker.handler({"Records": [{"body": body}]}, None)
    assert [m.text for m in stub.sent] == ["hello"]
    fifo = json.loads(sqs.receive_message(QueueUrl=events)["Messages"][0]["Body"])
    assert (fifo["kind"], fifo["task"], fifo["ref"]) == ("task", "decode", "c1")
    # delayed message is not visible yet (DelaySeconds=120)
    assert "Messages" not in sqs.receive_message(QueueUrl=timers)
