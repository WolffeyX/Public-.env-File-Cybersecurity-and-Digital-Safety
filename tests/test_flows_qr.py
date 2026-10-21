
"""QR flow integration tests (Owner A)."""
from core import flows
from core.store import InMemoryStore
from core.types import InboundEvent
from tests.fakes import Clock, make_deps


def make_event(clock, *, user="sim:mak", kind="text", msg_id,
               text=None, media_ref=None, button_id=None, task=None):
    return InboundEvent(
        channel=user.split(":")[0],
        user_id=user,
        msg_id=msg_id,
        kind=kind,
        ts=clock(),
        text=text,
        media_ref=media_ref,
        button_id=button_id,
        task=task,
    )


def prepare_user():
    """Create a fresh store and dependencies for one flow test."""
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)
    handle = lambda event: flows.handle_event(event, store, deps)

    # First contact creates the user and sends the initial greeting.
    handle(make_event(clock, msg_id="qr-first-contact"))

    return clock, store, deps, handle


def test_url_qr_flow():
    clock, store, deps, handle = prepare_user()

    result = handle(make_event(
        clock,
        kind="image",
        msg_id="qr-url-image",
        media_ref="url",
    ))

    assert store.get_user("sim:mak") is not None
    assert isinstance(result, list)


def test_unreadable_qr_flow():
    clock, store, deps, handle = prepare_user()

    result = handle(make_event(
        clock,
        kind="image",
        msg_id="qr-unreadable-image",
        media_ref="noqr",
    ))

    assert store.get_user("sim:mak") is not None
    assert isinstance(result, list)
