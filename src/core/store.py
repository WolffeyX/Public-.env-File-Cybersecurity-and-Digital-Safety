"""Data storage (Owner C).

InMemoryStore: COMPLETE. Use it in tests and in the local chat simulator.
               It is also the reference: DynamoStore must behave the same way.
DynamoStore:   COMPLETE. Single-table design, SDD section 3.2. Tested with moto.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import os

from core.types import (
    Alert, AlertStage, AlertType, Check, CheckStatus, Claim, DecodeResult, Level, Link,
    PairCode, ReportReason, Role, User,
)


class InMemoryStore:
    """Dict-based store. Not shared between processes. Good for tests."""

    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.pairs: dict[str, PairCode] = {}
        self.links: dict[tuple[str, Role], Link] = {}
        self.checks: dict[str, Check] = {}
        self.alerts: dict[str, Alert] = {}
        self.reports: dict[tuple[str, str], ReportReason] = {}
        self.seen: dict[str, float] = {}

    # users ------------------------------------------------------------
    def get_user(self, user_id):
        u = self.users.get(user_id)
        return copy.deepcopy(u) if u else None

    def put_user(self, user):
        self.users[user.user_id] = copy.deepcopy(user)

    def delete_user_everything(self, user_id):
        others = []
        for key, link in list(self.links.items()):
            if link.parent_id == user_id:
                others.append(link.contact_id)
                del self.links[key]
            elif link.contact_id == user_id:
                others.append(link.parent_id)
                del self.links[key]
        self.users.pop(user_id, None)
        return others

    # pairing ----------------------------------------------------------
    def put_pair_code(self, pc):
        self.pairs[pc.code] = copy.deepcopy(pc)

    def peek_pair_code(self, code, now):
        pc = self.pairs.get(code)
        if pc is None or pc.expires_at <= now:
            return None
        return copy.deepcopy(pc)

    def consume_pair_code(self, code, now):
        pc = self.peek_pair_code(code, now)
        if pc is not None:
            del self.pairs[code]
        return pc

    # links ------------------------------------------------------------
    def put_link(self, link):
        self.links[(link.parent_id, link.contact_type)] = copy.deepcopy(link)

    def get_links(self, parent_id):
        return [copy.deepcopy(l) for (p, _), l in self.links.items() if p == parent_id]

    def find_parent_of(self, contact_id):
        for link in self.links.values():
            if link.contact_id == contact_id:
                return link.parent_id
        return None

    def delete_link(self, parent_id, contact_type):
        self.links.pop((parent_id, contact_type), None)

    # checks -----------------------------------------------------------
    def put_check(self, check):
        self.checks[check.check_id] = copy.deepcopy(check)

    def get_check(self, parent_id, check_id, now):
        c = self.checks.get(check_id)
        if c is None or c.parent_id != parent_id or c.expires_at <= now:
            return None
        return copy.deepcopy(c)

    def get_open_check(self, parent_id, now):
        open_checks = [
            c for c in self.checks.values()
            if c.parent_id == parent_id and c.expires_at > now
            and c.status in (CheckStatus.DECODING, CheckStatus.DECODED)
        ]
        if not open_checks:
            return None
        return copy.deepcopy(max(open_checks, key=lambda c: c.created_at))

    # alerts -----------------------------------------------------------
    def put_alert(self, alert):
        self.alerts[alert.alert_id] = copy.deepcopy(alert)

    def get_alert(self, alert_id, now):
        a = self.alerts.get(alert_id)
        if a is None or a.expires_at <= now:
            return None
        return copy.deepcopy(a)

    def transition_alert(self, alert_id, from_stage, to_stage, acked_by=None, notified_add=None):
        a = self.alerts.get(alert_id)
        if a is None or a.stage != from_stage:
            return False
        a.stage = to_stage
        if acked_by:
            a.acked_by = acked_by
        if notified_add and notified_add not in a.notified:
            a.notified.append(notified_add)
        return True

    # reports ----------------------------------------------------------
    def add_report(self, report_key, reporter_hash, reason, now):
        k = (report_key, reporter_hash)
        if k in self.reports:
            return False
        self.reports[k] = reason
        return True

    def count_scam_reports(self, report_key):
        return sum(1 for (rk, _), r in self.reports.items()
                   if rk == report_key and r == ReportReason.SCAM_PATTERN)

    # duplicates and rate limit ---------------------------------------
    def mark_seen(self, msg_id, now):
        if msg_id in self.seen:
            return False
        self.seen[msg_id] = now
        return True

    def count_recent_checks(self, parent_id, since):
        return sum(1 for c in self.checks.values()
                   if c.parent_id == parent_id and c.created_at >= since)


class DynamoStore:
    """Production store on one DynamoDB table (SDD section 3.2, 3.3).
    COMPLETE and tested with moto in tests/test_store.py (same tests as InMemoryStore).

    Keys:
      User      PK=USER#<user_id>        SK=PROFILE
      Link      PK=USER#<parent_id>      SK=LINK#PRIMARY | LINK#SECOND
                GSI1PK=USER#<contact_id> GSI1SK=LINK#<parent_id>
      PairCode  PK=PAIR#<code>           SK=PAIR                ttl
      Check     PK=USER#<parent_id>      SK=CHECK#<check_id>    ttl
      Alert     PK=ALERT#<alert_id>      SK=STATE   stage       ttl
      Report    PK=REPORT#<report_key>   SK=REP#<reporter_hash> reason
      Seen      PK=DEDUP#<msg_id>        SK=-                   ttl
    Each record is stored as JSON in the "data" attribute, plus the few
    attributes that conditions and queries need. TTL deletion can be late,
    so every read also compares expires_at with `now`.
    """

    def __init__(self, table_name: str | None = None, resource=None) -> None:
        import boto3
        from boto3.dynamodb.conditions import Attr, Key
        self.Key, self.Attr = Key, Attr
        self.table = (resource or boto3.resource("dynamodb")).Table(
            table_name or os.environ["TABLE_NAME"])
        self.errors = self.table.meta.client.exceptions

    # helpers -----------------------------------------------------------
    @staticmethod
    def _dump(obj) -> str:
        return json.dumps(dataclasses.asdict(obj), default=lambda o: o.value)

    def _put(self, pk, sk, obj, ttl=None, condition=None, **extra) -> bool:
        item = {"PK": pk, "SK": sk, "data": self._dump(obj), **extra}
        if ttl is not None:
            item["ttl"] = int(ttl)
        kwargs = {"Item": item}
        if condition is not None:
            kwargs["ConditionExpression"] = condition
        try:
            self.table.put_item(**kwargs)
            return True
        except self.errors.ConditionalCheckFailedException:
            return False

    def _get(self, pk, sk):
        item = self.table.get_item(Key={"PK": pk, "SK": sk}, ConsistentRead=True).get("Item")
        return json.loads(item["data"]) if item else None

    def _query(self, pk, prefix, forward=True):
        items, kwargs = [], {
            "KeyConditionExpression": self.Key("PK").eq(pk) & self.Key("SK").begins_with(prefix),
            "ScanIndexForward": forward, "ConsistentRead": True}
        while True:
            page = self.table.query(**kwargs)
            items += page["Items"]
            if "LastEvaluatedKey" not in page:
                return items
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    @staticmethod
    def _link_sk(role: Role) -> str:
        return f"LINK#{role.value.upper()}"

    # users -------------------------------------------------------------
    def get_user(self, user_id):
        d = self._get(f"USER#{user_id}", "PROFILE")
        if d is None:
            return None
        d["role"] = Role(d["role"])
        return User(**d)

    def put_user(self, user):
        self._put(f"USER#{user.user_id}", "PROFILE", user)

    def delete_user_everything(self, user_id):
        own = self._query(f"USER#{user_id}", "LINK#")
        as_contact = self.table.query(
            IndexName="GSI1", KeyConditionExpression=self.Key("GSI1PK").eq(f"USER#{user_id}"))["Items"]
        keys = [{"PK": f"USER#{user_id}", "SK": "PROFILE"}]
        keys += [{"PK": i["PK"], "SK": i["SK"]} for i in own + as_contact]
        others = [json.loads(i["data"])["contact_id"] for i in own]
        others += [json.loads(i["data"])["parent_id"] for i in as_contact]
        client = self.table.meta.client
        for start in range(0, len(keys), 25):            # transaction limit
            client.transact_write_items(TransactItems=[
                {"Delete": {"TableName": self.table.name, "Key": k}} for k in keys[start:start + 25]])
        return others

    # pairing -----------------------------------------------------------
    def put_pair_code(self, pc):
        self._put(f"PAIR#{pc.code}", "PAIR", pc, ttl=pc.expires_at)

    @staticmethod
    def _pair(d):
        d["target_role"] = Role(d["target_role"])
        return PairCode(**d)

    def peek_pair_code(self, code, now):
        d = self._get(f"PAIR#{code}", "PAIR")
        if d is None or d["expires_at"] <= now:
            return None
        return self._pair(d)

    def consume_pair_code(self, code, now):
        try:
            old = self.table.delete_item(
                Key={"PK": f"PAIR#{code}", "SK": "PAIR"}, ReturnValues="ALL_OLD",
                ConditionExpression="attribute_exists(PK)").get("Attributes")
        except self.errors.ConditionalCheckFailedException:
            return None
        d = json.loads(old["data"])
        return None if d["expires_at"] <= now else self._pair(d)

    # links -------------------------------------------------------------
    def put_link(self, link):
        self._put(f"USER#{link.parent_id}", self._link_sk(link.contact_type), link,
                  GSI1PK=f"USER#{link.contact_id}", GSI1SK=f"LINK#{link.parent_id}")

    @staticmethod
    def _link(d):
        d["contact_type"] = Role(d["contact_type"])
        return Link(**d)

    def get_links(self, parent_id):
        return [self._link(json.loads(i["data"])) for i in self._query(f"USER#{parent_id}", "LINK#")]

    def find_parent_of(self, contact_id):
        items = self.table.query(
            IndexName="GSI1", KeyConditionExpression=self.Key("GSI1PK").eq(f"USER#{contact_id}"),
            Limit=1)["Items"]
        return json.loads(items[0]["data"])["parent_id"] if items else None

    def delete_link(self, parent_id, contact_type):
        self.table.delete_item(Key={"PK": f"USER#{parent_id}", "SK": self._link_sk(contact_type)})

    # checks ------------------------------------------------------------
    def put_check(self, check):
        self._put(f"USER#{check.parent_id}", f"CHECK#{check.check_id}", check, ttl=check.expires_at)

    @staticmethod
    def _check(d):
        d["status"] = CheckStatus(d["status"])
        d["decode"] = DecodeResult.from_dict(d["decode"]) if d.get("decode") else None
        d["claim"] = Claim(d["claim"]) if d.get("claim") else None
        d["verdict_level"] = Level(d["verdict_level"]) if d.get("verdict_level") else None
        return Check(**d)

    def get_check(self, parent_id, check_id, now):
        d = self._get(f"USER#{parent_id}", f"CHECK#{check_id}")
        if d is None or d["expires_at"] <= now:
            return None
        return self._check(d)

    def _checks(self, parent_id):
        return [self._check(json.loads(i["data"])) for i in self._query(f"USER#{parent_id}", "CHECK#")]

    def get_open_check(self, parent_id, now):
        open_checks = [c for c in self._checks(parent_id) if c.expires_at > now
                       and c.status in (CheckStatus.DECODING, CheckStatus.DECODED)]
        return max(open_checks, key=lambda c: c.created_at) if open_checks else None

    def count_recent_checks(self, parent_id, since):
        return sum(1 for c in self._checks(parent_id) if c.created_at >= since)

    # alerts ------------------------------------------------------------
    def put_alert(self, alert):
        self._put(f"ALERT#{alert.alert_id}", "STATE", alert, ttl=alert.expires_at,
                  stage=alert.stage.value)

    @staticmethod
    def _alert(d):
        d["type"] = AlertType(d["type"])
        d["stage"] = AlertStage(d["stage"])
        return Alert(**d)

    def get_alert(self, alert_id, now):
        d = self._get(f"ALERT#{alert_id}", "STATE")
        if d is None or d["expires_at"] <= now:
            return None
        return self._alert(d)

    def transition_alert(self, alert_id, from_stage, to_stage, acked_by=None, notified_add=None):
        d = self._get(f"ALERT#{alert_id}", "STATE")
        if d is None or d["stage"] != from_stage.value:
            return False
        a = self._alert(d)
        a.stage = to_stage
        if acked_by:
            a.acked_by = acked_by
        if notified_add and notified_add not in a.notified:
            a.notified.append(notified_add)
        return self._put(f"ALERT#{alert_id}", "STATE", a, ttl=a.expires_at, stage=to_stage.value,
                         condition=self.Attr("stage").eq(from_stage.value))

    # reports -----------------------------------------------------------
    def add_report(self, report_key, reporter_hash, reason, now):
        item = {"PK": f"REPORT#{report_key}", "SK": f"REP#{reporter_hash}",
                "reason": reason.value, "data": json.dumps({"created_at": now})}
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
            return True
        except self.errors.ConditionalCheckFailedException:
            return False

    def count_scam_reports(self, report_key):
        return sum(1 for i in self._query(f"REPORT#{report_key}", "REP#")
                   if i.get("reason") == ReportReason.SCAM_PATTERN.value)

    # duplicates --------------------------------------------------------
    def mark_seen(self, msg_id, now):
        try:
            self.table.put_item(Item={"PK": f"DEDUP#{msg_id}", "SK": "-", "ttl": int(now) + 86400},
                                ConditionExpression="attribute_not_exists(PK)")
            return True
        except self.errors.ConditionalCheckFailedException:
            return False
