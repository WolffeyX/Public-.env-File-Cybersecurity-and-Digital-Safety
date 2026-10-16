"""Milestone 3 tests: family alerts, escalation, reports (Owner C)."""

try:
    from tests.fakes import Clock, InMemoryStore, ev, make_deps
except ImportError:                      # if tests/ is not a package in your repo
    from fakes import Clock, InMemoryStore, ev, make_deps

from core import escalation, flows, reports
from core.messages import render
from core.types import AlertStage, Link, ReportReason, Role, Task, User

MAK = "wa:601"
CHILD = "wa:602"
SECOND = "wa:603"


def setup(with_second=False):
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)
    store.put_user(User(MAK, role=Role.PARENT, address_as="Mak"))
    store.put_user(User(CHILD, role=Role.PRIMARY))
    store.put_link(Link(MAK, CHILD, Role.PRIMARY, 1.0))
    if with_second:
        store.put_user(User(SECOND, role=Role.SECOND))
        store.put_link(Link(MAK, SECOND, Role.SECOND, 1.0))
    return clock, store, deps


def tap(clock, store, deps, user, button_id):
    return flows.handle_event(ev(user, "button", clock, button_id=button_id), store, deps)


def run(clock, store, deps, task):
    return flows.handle_event(
        ev(task.user_id, "task", clock, task=task.task, ref=task.ref), store, deps)


def check_and_claim(clock, store, deps, media, claim):
    """Mak forwards an image, the decode runs, Mak taps a claim. Returns (check_id, outputs)."""
    out = flows.handle_event(ev(MAK, "image", clock, media_ref=media), store, deps)
    check_id = out[1].ref
    run(clock, store, deps, out[1])
    return check_id, tap(clock, store, deps, MAK, f"claim:{claim}:{check_id}")


def messages_to(out, user):
    return [o for o in out if not isinstance(o, Task) and o.to == user]


def tasks_in(out):
    return [o for o in out if isinstance(o, Task)]


def stop_alert(with_second=False):
    clock, store, deps = setup(with_second)
    check_id, out = check_and_claim(clock, store, deps, "personal", "OFFICIAL")
    return clock, store, deps, f"{check_id}-stop", tasks_in(out)[0]


# ---------------------------------------------------------------- alerts

def test_s1_stop_alerts_the_child_with_an_ack_button_and_a_timer():
    clock, store, deps = setup()
    check_id, out = check_and_claim(clock, store, deps, "personal", "OFFICIAL")
    alert_id = f"{check_id}-stop"
    assert out[0].to == MAK                                  # parent is told first (FR-19)
    msg = messages_to(out, CHILD)[0]
    assert msg.text == render("a.child.stop", "ms", address_as="Mak",
                              claim_label=render("c.OFFICIAL", "ms"),
                              qr_desc=render("a.qr_personal", "ms"))
    assert "AMARAN: Telefon Mak sekarang." in msg.text
    assert [b.id for b in msg.buttons] == [f"ack:handle:{alert_id}"]
    assert tasks_in(out) == [Task("escalate", MAK, alert_id, 180)]
    alert = store.get_alert(alert_id, clock())
    assert alert.stage == AlertStage.PRIMARY_SENT and alert.notified == [CHILD]


def test_alert_is_written_in_the_recipients_language():
    clock, store, deps = setup()
    store.put_user(User(CHILD, role=Role.PRIMARY, lang="en"))
    _, out = check_and_claim(clock, store, deps, "personal", "OFFICIAL")
    assert messages_to(out, CHILD)[0].text == render(
        "a.child.stop", "en", address_as="Mak",
        claim_label=render("c.OFFICIAL", "en"), qr_desc=render("a.qr_personal", "en"))


def test_s2_blurry_image_alert_says_the_qr_could_not_be_read():
    clock, store, deps = setup()
    _, out = check_and_claim(clock, store, deps, "noqr", "OFFICIAL")
    assert render("a.qr_unreadable", "ms") in messages_to(out, CHILD)[0].text


def test_verify_never_alerts_the_child():
    clock, store, deps = setup()
    _, out = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    assert messages_to(out, CHILD) == [] and tasks_in(out) == []


def test_practice_check_never_alerts_the_child():
    clock, store, deps = setup()
    user = store.get_user(MAK)
    user.practice_pending = True
    store.put_user(user)
    _, out = check_and_claim(clock, store, deps, "personal", "OFFICIAL")
    assert messages_to(out, CHILD) == [] and tasks_in(out) == []


def test_every_alert_is_within_450_characters_and_8_lines():
    for media, claim in [("personal", "OFFICIAL"), ("business", "OFFICIAL"),
                         ("noqr", "OFFICIAL"), ("url", "OFFICIAL"),
                         ("personal", "COURIER")]:
        clock, store, deps = setup()
        _, out = check_and_claim(clock, store, deps, media, claim)
        text = messages_to(out, CHILD)[0].text
        assert len(text) <= 450 and len(text.splitlines()) <= 8, (media, claim)
    clock, store, deps = setup()
    check_id, _ = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    text = messages_to(tap(clock, store, deps, MAK, f"paid:yes:{check_id}"), CHILD)[0].text
    assert len(text) <= 450 and len(text.splitlines()) <= 8


def test_s9_paid_button_alerts_the_child_urgently():
    clock, store, deps = setup()
    check_id, _ = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    out = tap(clock, store, deps, MAK, f"paid:yes:{check_id}")
    assert messages_to(out, MAK)[0].text == (
    render("p.paid", "ms") + "\n" + render("v.told_contact", "ms", address_as="Mak"))
    assert messages_to(out, CHILD)[0].text == render(
        "a.child.paid", "ms", address_as="Mak", claim_label=render("c.KNOWN_PERSON", "ms"))
    assert tasks_in(out)[0].task == "escalate"


def test_tapping_paid_twice_sends_only_one_alert():
    clock, store, deps = setup()
    check_id, _ = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    tap(clock, store, deps, MAK, f"paid:yes:{check_id}")
    again = tap(clock, store, deps, MAK, f"paid:yes:{check_id}")
    assert messages_to(again, CHILD) == [] and tasks_in(again) == []


def test_paid_after_the_check_expired_still_alerts_the_child():
    clock, store, deps = setup()
    check_id, _ = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    clock.advance(901)
    out = tap(clock, store, deps, MAK, f"paid:yes:{check_id}")
    assert messages_to(out, CHILD)[0].text == render(
        "a.child.paid", "ms", address_as="Mak", claim_label=render("c.unknown", "ms"))


# ------------------------------------------------------------------- ack

def test_ack_confirms_and_the_late_timer_does_nothing():
    clock, store, deps, alert_id, timer = stop_alert()
    out = tap(clock, store, deps, CHILD, f"ack:handle:{alert_id}")
    assert [o.text for o in out] == [render("a.ack_done", "ms")]
    alert = store.get_alert(alert_id, clock())
    assert alert.stage == AlertStage.ACKED and alert.acked_by == CHILD
    clock.advance(180)
    assert run(clock, store, deps, timer) == []


def test_double_tap_changes_nothing_the_second_time():
    clock, store, deps, alert_id, _ = stop_alert()
    tap(clock, store, deps, CHILD, f"ack:handle:{alert_id}")
    again = tap(clock, store, deps, CHILD, f"ack:handle:{alert_id}")
    assert [o.text for o in again] == [render("a.ack_done", "ms")]
    assert store.get_alert(alert_id, clock()).stage == AlertStage.ACKED


def test_someone_we_never_alerted_cannot_ack():
    clock, store, deps, alert_id, _ = stop_alert()
    assert escalation.on_ack(alert_id, "wa:999", store, deps) == []
    assert store.get_alert(alert_id, clock()).stage == AlertStage.PRIMARY_SENT


# ------------------------------------------------------------ escalation

def test_s8_no_ack_alerts_the_second_contact_then_tells_the_parent():
    clock, store, deps, alert_id, timer = stop_alert(with_second=True)
    clock.advance(180)
    out = run(clock, store, deps, timer)
    to_second = messages_to(out, SECOND)
    assert len(to_second) == 1 and "AMARAN" in to_second[0].text
    assert messages_to(out, CHILD) == []                      # the child is not messaged twice
    next_timer = tasks_in(out)[0]
    assert (next_timer.task, next_timer.delay_s) == ("escalate", 180)
    alert = store.get_alert(alert_id, clock())
    assert alert.stage == AlertStage.SECONDARY_SENT and alert.notified == [CHILD, SECOND]

    clock.advance(180)
    out = run(clock, store, deps, next_timer)
    assert [o.to for o in out] == [MAK]
    assert out[0].text == render("a.parent.unacked", "ms", address_as="Mak")
    assert store.get_alert(alert_id, clock()).stage == AlertStage.UNACKED
    assert run(clock, store, deps, next_timer) == []          # nothing after the chain ends


def test_no_second_contact_means_the_parent_is_told_after_180_seconds():
    clock, store, deps, alert_id, timer = stop_alert()
    clock.advance(180)
    out = run(clock, store, deps, timer)
    assert [o.to for o in out] == [MAK]
    assert out[0].text == render("a.parent.unacked", "ms", address_as="Mak")
    assert store.get_alert(alert_id, clock()).stage == AlertStage.UNACKED


def test_ack_at_60_seconds_means_the_second_contact_gets_nothing():
    clock, store, deps, alert_id, timer = stop_alert(with_second=True)
    clock.advance(60)
    tap(clock, store, deps, CHILD, f"ack:handle:{alert_id}")
    clock.advance(120)
    assert run(clock, store, deps, timer) == []


def test_second_contact_acks_and_the_child_is_told_someone_is_handling_it():
    clock, store, deps, alert_id, timer = stop_alert(with_second=True)
    clock.advance(180)
    run(clock, store, deps, timer)
    out = tap(clock, store, deps, SECOND, f"ack:handle:{alert_id}")
    assert messages_to(out, SECOND)[0].text == render("a.ack_done", "ms")
    assert messages_to(out, CHILD)[0].text == render("a.ack_other", "ms", address_as="Mak")
    assert store.get_alert(alert_id, clock()).acked_by == SECOND


# --------------------------------------------------------------- reports

def test_report_flow_stores_one_scam_report_per_person():
    clock, store, deps = setup()
    check_id, _ = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    out = tap(clock, store, deps, MAK, f"report:open:{check_id}")
    assert [b.id for b in out[0].buttons] == [
        f"report:scam_pattern:{check_id}", f"report:dispute:{check_id}",
        f"report:other:{check_id}"]
    out = tap(clock, store, deps, MAK, f"report:scam_pattern:{check_id}")
    assert out[0].text == render("r.thanks", "ms")
    assert store.count_scam_reports("k-personal") == 1
    out = tap(clock, store, deps, MAK, f"report:scam_pattern:{check_id}")
    assert out[0].text == render("r.already_reported", "ms")
    assert store.count_scam_reports("k-personal") == 1


def test_s12_dynamic_qr_cannot_be_reported():
    clock, store, deps = setup()
    check_id, _ = check_and_claim(clock, store, deps, "dynamic", "COURIER")
    out = tap(clock, store, deps, MAK, f"report:open:{check_id}")
    assert out[0].text == render("r.not_reportable", "ms") and out[0].buttons == []
    out = tap(clock, store, deps, MAK, f"report:scam_pattern:{check_id}")
    assert out[0].text == render("r.not_reportable", "ms")


def test_dispute_report_is_stored_but_does_not_count():
    clock, store, deps = setup()
    check_id, _ = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    out = tap(clock, store, deps, MAK, f"report:dispute:{check_id}")
    assert out[0].text == render("r.thanks", "ms")
    assert store.count_scam_reports("k-personal") == 0


def test_one_report_adds_the_few_wording():
    clock, store, deps = setup()
    store.add_report("k-personal", reports.reporter_hash("wa:700", deps.pepper),
                     ReportReason.SCAM_PATTERN, clock())
    _, out = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    assert render("ev.few", "ms", n=1) in out[0].text


def test_s11_three_reporters_change_the_wording_but_never_the_verdict():
    clock, store, deps = setup()
    for i in range(3):
        store.add_report("k-personal", reports.reporter_hash(f"wa:70{i}", deps.pepper),
                         ReportReason.SCAM_PATTERN, clock())
    _, out = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    assert out[0].text.startswith("🟡")                       # still VERIFY
    assert render("ev.many", "ms") in out[0].text and len(out[0].text) <= 450
    clock.advance(5)
    _, out = check_and_claim(clock, store, deps, "personal", "OFFICIAL")
    assert out[0].text.startswith("🛑")                       # STOP does not depend on reports


def test_report_on_a_practice_check_is_not_stored():
    clock, store, deps = setup()
    user = store.get_user(MAK)
    user.practice_pending = True
    store.put_user(user)
    check_id, _ = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    out = tap(clock, store, deps, MAK, f"report:scam_pattern:{check_id}")
    assert out[0].text == render("r.thanks", "ms")
    assert store.count_scam_reports("k-personal") == 0


def test_report_after_the_check_expired_says_expired():
    clock, store, deps = setup()
    check_id, _ = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    clock.advance(901)
    out = tap(clock, store, deps, MAK, f"report:open:{check_id}")
    assert out[0].text == render("q.expired", "ms")

def test_paid_message_does_not_claim_the_child_was_told_when_nobody_was():
    clock, store, deps = setup()
    store.delete_link(MAK, Role.PRIMARY)              # Mak has no linked contact
    check_id, _ = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    out = tap(clock, store, deps, MAK, f"paid:yes:{check_id}")
    assert messages_to(out, MAK)[0].text == render("p.paid", "ms")
    assert messages_to(out, CHILD) == [] and tasks_in(out) == []


def test_paid_on_a_practice_check_says_nothing_about_telling_the_child():
    clock, store, deps = setup()
    user = store.get_user(MAK)
    user.practice_pending = True
    store.put_user(user)
    check_id, _ = check_and_claim(clock, store, deps, "personal", "KNOWN_PERSON")
    out = tap(clock, store, deps, MAK, f"paid:yes:{check_id}")
    assert messages_to(out, MAK)[0].text == render("p.paid", "ms")
    assert messages_to(out, CHILD) == []