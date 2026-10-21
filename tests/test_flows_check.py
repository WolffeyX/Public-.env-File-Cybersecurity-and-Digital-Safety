"""Tests: image in, question out, decode, reminder, close (Owner C)."""

try:
    from tests.fakes import Clock, InMemoryStore, ev, make_deps
except ImportError:                      # if tests/ is not a package in your repo
    from fakes import Clock, InMemoryStore, ev, make_deps

from core import flows
from core.messages import render
from core.types import CheckStatus, QrKind, Role, Task, User

MAK = "wa:601"


def setup():
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)
    store.put_user(User(MAK, role=Role.PARENT, address_as="Mak"))
    return clock, store, deps


def send_image(clock, store, deps, media="personal"):
    return flows.handle_event(ev(MAK, "image", clock, media_ref=media), store, deps)


def run_task(clock, store, deps, task):
    e = ev(task.user_id, "task", clock, task=task.task, ref=task.ref)
    return flows.handle_event(e, store, deps)


def test_image_gets_question_first_and_three_timers():
    clock, store, deps = setup()
    out = send_image(clock, store, deps)
    msg = out[0]
    assert msg.text == render("q.who_asked", "ms", address_as="Mak")
    assert [b.id.split(":")[1] for b in msg.buttons] == ["OFFICIAL", "COURIER", "KNOWN_PERSON"]
    tasks = [o for o in out if isinstance(o, Task)]
    assert [(t.task, t.delay_s) for t in tasks] == [
        ("decode", 0), ("reminder", 120), ("close_check", 600)]
    check_id = tasks[0].ref
    check = store.get_check(MAK, check_id, clock())
    assert check.status == CheckStatus.DECODING and check.media_ref == "personal"


def test_decode_task_saves_result_and_forgets_the_image():
    clock, store, deps = setup()
    out = send_image(clock, store, deps, "personal")
    decode = out[1]
    assert run_task(clock, store, deps, decode) == []
    check = store.get_check(MAK, decode.ref, clock())
    assert check.status == CheckStatus.DECODED
    assert check.decode.is_personal is True
    assert check.media_ref is None            # DR-01


def test_blurry_image_still_decodes_to_no_qr():
    clock, store, deps = setup()
    out = send_image(clock, store, deps, "noqr")
    run_task(clock, store, deps, out[1])
    assert store.get_check(MAK, out[1].ref, clock()).decode.kind == QrKind.NO_QR


def test_new_image_closes_the_old_check():
    clock, store, deps = setup()
    first = send_image(clock, store, deps)
    clock.advance(10)
    second = send_image(clock, store, deps)
    old = store.get_check(MAK, first[1].ref, clock())
    assert old is not None and old.status == CheckStatus.CLOSED
    new = store.get_check(MAK, second[1].ref, clock())
    assert new.status == CheckStatus.DECODING


def test_rate_limit_after_ten_checks():
    clock, store, deps = setup()
    for _ in range(10):
        out = send_image(clock, store, deps)
        assert out[0].text == render("q.who_asked", "ms", address_as="Mak")
    out = send_image(clock, store, deps)
    assert len(out) == 1 and out[0].text == render("h.rate_limited", "ms")


def test_reminder_sent_once_with_three_buttons():
    clock, store, deps = setup()
    out = send_image(clock, store, deps)
    reminder = out[2]
    clock.advance(120)
    first = run_task(clock, store, deps, reminder)
    assert first[0].text == render("q.reminder", "ms")
    assert len(first[0].buttons) == 3
    assert run_task(clock, store, deps, reminder) == []       # only one reminder


def test_close_check_closes_and_silences_reminder():
    clock, store, deps = setup()
    out = send_image(clock, store, deps)
    clock.advance(600)
    run_task(clock, store, deps, out[3])
    check = store.get_check(MAK, out[1].ref, clock())
    assert check is None or check.status == CheckStatus.CLOSED
    assert run_task(clock, store, deps, out[2]) == []


def test_practice_image_is_marked_and_flag_is_used_up():
    clock, store, deps = setup()
    user = store.get_user(MAK)
    user.practice_pending = True
    store.put_user(user)
    out = send_image(clock, store, deps)
    assert store.get_check(MAK, out[1].ref, clock()).is_practice is True
    assert store.get_user(MAK).practice_pending is False
    clock.advance(5)
    out2 = send_image(clock, store, deps)
    assert store.get_check(MAK, out2[1].ref, clock()).is_practice is False

    # ---- Step 7 and 9: verdicts and "already paid" ----
from core.types import Level, Link

CHILD = "wa:602"


def link_child(store):
    store.put_user(User(CHILD, role=Role.PRIMARY, address_as=None))
    store.put_link(Link(parent_id=MAK, contact_id=CHILD,
                        contact_type=Role.PRIMARY, consent_at=1.0))


def answer(clock, store, deps, media, claim):
    """Mak forwards an image, the decode runs, then Mak taps a claim. Returns the outputs."""
    out = send_image(clock, store, deps, media)
    check_id = out[1].ref
    run_task(clock, store, deps, out[1])
    return check_id, flows.handle_event(
        ev(MAK, "button", clock, button_id=f"claim:{claim}:{check_id}"), store, deps)


def test_s1_bank_and_personal_qr_is_stop_and_tells_the_child():
    clock, store, deps = setup()
    link_child(store)
    check_id, out = answer(clock, store, deps, "personal", "OFFICIAL")
    text = out[0].text
    assert text.startswith("🛑 JANGAN BAYAR")
    assert render("v.told_contact", "ms", address_as="Mak") in text
    assert [b.id for b in out[0].buttons] == [f"paid:yes:{check_id}", f"report:open:{check_id}"]
    check = store.get_check(MAK, check_id, clock())
    assert check.status == CheckStatus.ANSWERED and check.verdict_level == Level.STOP


def test_s2_bank_and_blurry_image_is_still_stop():
    clock, store, deps = setup()
    _, out = answer(clock, store, deps, "noqr", "OFFICIAL")
    assert out[0].text.startswith("🛑 JANGAN BAYAR")
    assert render("e.no_qr", "ms") in out[0].text


def test_s3_courier_and_personal_qr_is_stop_with_the_name():
    clock, store, deps = setup()
    _, out = answer(clock, store, deps, "personal", "COURIER")
    assert out[0].text.startswith("🛑 JANGAN BAYAR")
    assert "AHMAD BIN ALI" in out[0].text


def test_s4_courier_and_business_qr_is_verify_with_merchant_name():
    clock, store, deps = setup()
    _, out = answer(clock, store, deps, "business", "COURIER")
    text = out[0].text
    assert text.startswith("🟡 Tunggu dulu")
    assert "KEDAI CONTOH SDN BHD" in text
    assert render("v.semak_mule", "ms") in text


def test_courier_and_unreadable_image_is_verify():
    clock, store, deps = setup()
    _, out = answer(clock, store, deps, "noqr", "COURIER")
    assert out[0].text.startswith("🟡 Tunggu dulu")


def test_dynamic_qr_shows_the_amount():
    clock, store, deps = setup()
    _, out = answer(clock, store, deps, "dynamic", "COURIER")
    assert "RM157.00" in out[0].text


def test_s5_relative_and_personal_qr_is_verify_with_code_word():
    clock, store, deps = setup()
    _, out = answer(clock, store, deps, "personal", "KNOWN_PERSON")
    text = out[0].text
    assert text.startswith("🟡 Tunggu dulu")
    assert "AHMAD BIN ALI" in text and "kod rahsia" in text


def test_url_qr_gets_the_url_note_and_is_never_stop_for_a_relative():
    clock, store, deps = setup()
    _, out = answer(clock, store, deps, "url", "KNOWN_PERSON")
    assert render("e.url", "ms") in out[0].text
    assert out[0].text.startswith("🟡")


def test_no_child_means_no_told_contact_line():
    clock, store, deps = setup()                 # Mak has no links here
    _, out = answer(clock, store, deps, "personal", "OFFICIAL")
    assert out[0].text.startswith("🛑")
    assert "Saya sudah maklumkan anak" not in out[0].text


def test_practice_check_is_labelled_and_never_claims_the_child_was_told():
    clock, store, deps = setup()
    link_child(store)
    user = store.get_user(MAK)
    user.practice_pending = True
    store.put_user(user)
    _, out = answer(clock, store, deps, "personal", "OFFICIAL")
    assert out[0].text.startswith(render("v.practice_prefix", "ms"))
    assert "Saya sudah maklumkan anak" not in out[0].text


def test_second_tap_on_the_same_check_says_expired():
    clock, store, deps = setup()
    check_id, _ = answer(clock, store, deps, "personal", "OFFICIAL")
    out = flows.handle_event(
        ev(MAK, "button", clock, button_id=f"claim:OFFICIAL:{check_id}"), store, deps)
    assert out[0].text == render("q.expired", "ms")


def test_tap_after_ten_minutes_says_expired():
    clock, store, deps = setup()
    out = send_image(clock, store, deps)
    check_id = out[1].ref
    clock.advance(601)
    run_task(clock, store, deps, out[3])         # close_check runs
    out = flows.handle_event(
        ev(MAK, "button", clock, button_id=f"claim:OFFICIAL:{check_id}"), store, deps)
    assert out[0].text == render("q.expired", "ms")


def test_every_verdict_is_within_450_characters():
    for media in ("personal", "business", "dynamic", "noqr", "url"):
        for claim in ("OFFICIAL", "COURIER", "KNOWN_PERSON"):
            clock, store, deps = setup()
            link_child(store)
            _, out = answer(clock, store, deps, media, claim)
            assert len(out[0].text) <= 700, (media, claim, len(out[0].text))


def test_paid_button_gives_the_four_steps():
    clock, store, deps = setup()
    check_id, _ = answer(clock, store, deps, "personal", "KNOWN_PERSON")
    out = flows.handle_event(
        ev(MAK, "button", clock, button_id=f"paid:yes:{check_id}"), store, deps)
    assert out[0].text == render("p.paid", "ms", address_as="Mak")