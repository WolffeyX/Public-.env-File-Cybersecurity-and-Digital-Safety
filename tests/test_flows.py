
from core.flows import handle_event
from core.store import InMemoryStore
from core.types import InboundEvent
from tests.fakes import Clock, make_deps


def make_event(clock, user="sim:anak", kind="text", **kwargs):
    return InboundEvent(
        channel=user.split(":")[0],
        user_id=user,
        msg_id=kwargs.pop("msg_id", "test-message-1"),
        kind=kind,
        ts=clock(),
        **kwargs,
    )


def test_first_contact_returns_language_choice_and_welcome():
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)

    result = handle_event(
        make_event(clock),
        store,
        deps,
    )

    assert len(result) == 1
    assert all(message.to == "sim:anak" for message in result)
    assert store.get_user("sim:anak") is not None


def test_duplicate_event_is_ignored():
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)

    event = make_event(clock)

    first_result = handle_event(event, store, deps)
    second_result = handle_event(event, store, deps)

    assert len(first_result) == 1
    assert second_result == []


def test_help_command_returns_a_message():
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)

    handle_event(make_event(clock), store, deps)

    event = make_event(
        clock,
        msg_id="test-message-2",
        text="help",
    )
    result = handle_event(event, store, deps)

    assert len(result) == 1
    assert result[0].to == "sim:anak"
    assert result[0].text


def test_register_command_asks_for_parent_address():
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)

    handle_event(make_event(clock), store, deps)

    result = handle_event(
        make_event(clock, msg_id="register-1", text="daftar"),
        store,
        deps,
    )

    assert len(result) == 1
    assert store.get_user("sim:anak").role.value == "primary"
    assert result[0].text


def test_language_button_changes_language_to_english():
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)

    handle_event(make_event(clock), store, deps)

    result = handle_event(
        make_event(
            clock,
            kind="button",
            msg_id="language-1",
            button_id="lang:en:-",
        ),
        store,
        deps,
    )

    assert store.get_user("sim:anak").lang == "en"
    assert store.get_user("sim:anak").lang_chosen is True
    assert len(result) == 1


def test_unknown_text_returns_help():
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)

    handle_event(make_event(clock), store, deps)

    result = handle_event(
        make_event(clock, msg_id="unknown-1", text="something random"),
        store,
        deps,
    )

    assert len(result) == 1
    assert result[0].text


def test_primary_contact_can_generate_pairing_code():
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)

    handle_event(make_event(clock), store, deps)

    handle_event(
        make_event(clock, msg_id="register-pair-1", text="daftar"),
        store,
        deps,
    )

    handle_event(
        make_event(clock, msg_id="address-pair-1", text="Mak"),
        store,
        deps,
    )

    result = handle_event(
        make_event(
            clock,
            msg_id="parent-code-1",
            user="sim:mak",
            text="hello",
        ),
        store,
        deps,
    )

    assert store.get_user("sim:anak").address_as == "Mak"
    assert len(result) == 1



def test_parent_can_consent_to_pairing():
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)

    handle_event(make_event(clock), store, deps)

    handle_event(
        make_event(clock, msg_id="register-pair-2", text="daftar"),
        store,
        deps,
    )

    code_result = handle_event(
        make_event(clock, msg_id="address-pair-2", text="Mak"),
        store,
        deps,
    )

    # The address-answer message contains the generated pairing code.
    assert len(code_result) == 1
    code_text = code_result[0].text
    pair_code = next(
        part for part in code_text.split()
        if len(part) == 6 and part.isalnum()
    )

    handle_event(
        make_event(clock, user="sim:mak", msg_id="parent-first-2"),
        store,
        deps,
    )

    handle_event(
        make_event(
            clock,
            user="sim:mak",
            msg_id="parent-enter-code-2",
            text=pair_code,
        ),
        store,
        deps,
    )

    result = handle_event(
        make_event(
            clock,
            user="sim:mak",
            kind="button",
            msg_id="parent-consent-2",
            button_id=f"consent:yes:{pair_code}",
        ),
        store,
        deps,
    )

    assert store.get_user("sim:mak").role.value == "parent"
    assert store.get_user("sim:mak").consent_at is not None
    assert result


def test_pairing_code_cannot_be_reused_after_consent():
    clock = Clock()
    store = InMemoryStore()
    deps = make_deps(clock)

    # Register the child and generate a pairing code.
    handle_event(make_event(clock), store, deps)
    handle_event(
        make_event(clock, msg_id="reuse-register", text="daftar"),
        store,
        deps,
    )
    result = handle_event(
        make_event(clock, msg_id="reuse-address", text="Mak"),
        store,
        deps,
    )

    code_text = result[0].text
    pair_code = next(
        part for part in code_text.split()
        if len(part) == 6 and part.isalnum()
    )

    # First parent enters the code and consents.
    handle_event(
        make_event(clock, user="sim:mak", msg_id="reuse-parent-first"),
        store,
        deps,
    )
    handle_event(
        make_event(
            clock, user="sim:mak",
            msg_id="reuse-parent-code", text=pair_code,
        ),
        store,
        deps,
    )
    handle_event(
        make_event(
            clock, user="sim:mak", kind="button",
            msg_id="reuse-parent-consent",
            button_id=f"consent:yes:{pair_code}",
        ),
        store,
        deps,
    )

    # A different user must not be able to reuse that code.
    handle_event(
        make_event(clock, user="sim:other", msg_id="reuse-other-first"),
        store,
        deps,
    )
    result = handle_event(
        make_event(
            clock, user="sim:other",
            msg_id="reuse-other-code", text=pair_code,
        ),
        store,
        deps,
    )

    assert len(result) == 1
    assert store.get_user("sim:other").role.value == "none"
    assert result[0].text
