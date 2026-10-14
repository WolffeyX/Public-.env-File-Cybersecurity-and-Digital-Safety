"""Every test runs against BOTH stores, so DynamoStore must behave like InMemoryStore."""

import os

import boto3
import pytest
from moto import mock_aws

from core.store import DynamoStore, InMemoryStore
from core.types import (Alert, AlertStage, AlertType, Check, CheckStatus, Claim, DecodeResult,
                        Level, Link, PairCode, QrKind, ReportReason, Role, User)

os.environ.setdefault("AWS_DEFAULT_REGION", "ap-southeast-1")


def make_table(name="semak-test"):
    """Same shape as Table in template.yaml."""
    ddb = boto3.resource("dynamodb")
    ddb.create_table(
        TableName=name, BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"}
                              for a in ("PK", "SK", "GSI1PK", "GSI1SK")],
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"},
                   {"AttributeName": "SK", "KeyType": "RANGE"}],
        GlobalSecondaryIndexes=[{
            "IndexName": "GSI1",
            "KeySchema": [{"AttributeName": "GSI1PK", "KeyType": "HASH"},
                          {"AttributeName": "GSI1SK", "KeyType": "RANGE"}],
            "Projection": {"ProjectionType": "ALL"}}])
    return ddb


@pytest.fixture(params=["memory", "dynamo"])
def store(request):
    if request.param == "memory":
        yield InMemoryStore()
    else:
        with mock_aws():
            yield DynamoStore("semak-test", make_table())


def test_user_round_trip(store):
    store.put_user(User("wa:p", Role.PARENT, lang="en", address_as="Mak", consent_at=5.5))
    u = store.get_user("wa:p")
    assert (u.role, u.lang, u.address_as, u.consent_at) == (Role.PARENT, "en", "Mak", 5.5)
    assert store.get_user("wa:nobody") is None


def test_pair_code_single_use_and_expiry(store):
    store.put_pair_code(PairCode("ABC234", "wa:1", Role.PARENT, "Mak", expires_at=100))
    assert store.peek_pair_code("ABC234", now=50).address_as == "Mak"
    assert store.consume_pair_code("ABC234", now=50).owner_id == "wa:1"
    assert store.consume_pair_code("ABC234", now=50) is None
    store.put_pair_code(PairCode("ZZZ999", "wa:1", Role.PARENT, "Mak", expires_at=100))
    assert store.consume_pair_code("ZZZ999", now=101) is None


def test_links_lookup_and_delete_everything(store):
    store.put_user(User("wa:p", Role.PARENT))
    store.put_link(Link("wa:p", "wa:c", Role.PRIMARY, 1))
    store.put_link(Link("wa:p", "wa:s", Role.SECOND, 1))
    assert {l.contact_type for l in store.get_links("wa:p")} == {Role.PRIMARY, Role.SECOND}
    assert store.find_parent_of("wa:s") == "wa:p"
    assert sorted(store.delete_user_everything("wa:p")) == ["wa:c", "wa:s"]
    assert store.get_links("wa:p") == [] and store.get_user("wa:p") is None
    assert store.find_parent_of("wa:s") is None


def test_contact_leaving_removes_only_their_link(store):
    store.put_link(Link("wa:p", "wa:c", Role.PRIMARY, 1))
    store.put_link(Link("wa:p", "wa:s", Role.SECOND, 1))
    assert store.delete_user_everything("wa:s") == ["wa:p"]
    assert [l.contact_id for l in store.get_links("wa:p")] == ["wa:c"]


def test_delete_link(store):
    store.put_link(Link("wa:p", "wa:s", Role.SECOND, 1))
    store.delete_link("wa:p", Role.SECOND)
    assert store.get_links("wa:p") == []


def test_check_round_trip_and_open_check(store):
    d = DecodeResult(kind=QrKind.PAYMENT_DUITNOW, is_personal=True, payee_name="A", report_key="k")
    store.put_check(Check("c1", "wa:p", CheckStatus.DECODING, created_at=10, expires_at=1000))
    store.put_check(Check("c2", "wa:p", CheckStatus.DECODED, created_at=20, expires_at=1000,
                          decode=d, claim=Claim.COURIER, verdict_level=Level.STOP))
    c2 = store.get_check("wa:p", "c2", now=30)
    assert (c2.decode, c2.claim, c2.verdict_level) == (d, Claim.COURIER, Level.STOP)
    assert store.get_open_check("wa:p", now=30).check_id == "c2"
    assert store.get_open_check("wa:p", now=2000) is None
    assert store.get_check("wa:p", "c2", now=2000) is None
    assert store.count_recent_checks("wa:p", since=15) == 1


def test_answered_check_is_not_open(store):
    store.put_check(Check("c1", "wa:p", CheckStatus.ANSWERED, created_at=10, expires_at=1000))
    assert store.get_open_check("wa:p", now=30) is None


def test_alert_transition_is_conditional(store):
    store.put_alert(Alert("a1", "wa:p", "c1", AlertType.STOP, AlertStage.PRIMARY_SENT, 0, 10**10,
                          notified=["wa:c"]))
    assert store.transition_alert("a1", AlertStage.PRIMARY_SENT, AlertStage.SECONDARY_SENT,
                                  notified_add="wa:s")
    assert not store.transition_alert("a1", AlertStage.PRIMARY_SENT, AlertStage.ACKED)
    assert store.transition_alert("a1", AlertStage.SECONDARY_SENT, AlertStage.ACKED, acked_by="wa:s")
    a = store.get_alert("a1", now=1)
    assert (a.stage, a.acked_by, a.notified) == (AlertStage.ACKED, "wa:s", ["wa:c", "wa:s"])


def test_reports_one_per_user_and_only_scam_counts(store):
    assert store.add_report("k", "r1", ReportReason.SCAM_PATTERN, 0)
    assert not store.add_report("k", "r1", ReportReason.SCAM_PATTERN, 0)
    assert store.add_report("k", "r2", ReportReason.DISPUTE, 0)
    assert store.add_report("k", "r3", ReportReason.SCAM_PATTERN, 0)
    assert store.count_scam_reports("k") == 2
    assert store.count_scam_reports("other") == 0


def test_mark_seen(store):
    assert store.mark_seen("m1", 0) and not store.mark_seen("m1", 0)
