"""Milestone 1 tests: setup and linking (Owner C)."""

from types import SimpleNamespace

from core import flows
from core.messages import label, render
from core.store import InMemoryStore
from core.types import InboundEvent, Role, User


class TinyStore:
    """Just enough store for helper tests."""
    def __init__(self):
        self.users = {}

    def get_user(self, user_id):
        return self.users.get(user_id)

    def put_user(self, user):
        self.users[user.user_id] = user


DEPS = SimpleNamespace(now=lambda: 1000.0)


def make_event(kind="text", text=None, button_id=None, msg_id="m1", user="sim:anak"):
    return InboundEvent(channel="sim", user_id=user, msg_id=msg_id,
                        kind=kind, ts=1000.0, text=text, button_id=button_id)


# ---- Step 1: helpers ----

def test_get_or_create_user_makes_a_blank_user_once():
    store = TinyStore()
    first = flows.get_or_create_user("wa:601", store, DEPS)
    assert first.role == Role.NONE
    assert first.created_at == 1000.0
    again = flows.get_or_create_user("wa:601", store, DEPS)
    assert again is first


def test_lang_of_defaults_to_bm():
    assert flows.lang_of(User("wa:1")) == "ms"
    assert flows.lang_of(User("wa:1", lang="en")) == "en"
    assert flows.lang_of(User("wa:1", lang="xx")) == "ms"


def test_addr_uses_chosen_name_or_default():
    assert flows.addr(User("wa:1", address_as="Ayah")) == "Ayah"
    assert flows.addr(User("wa:1")) == render("s.default_address", "ms")


def test_btn_takes_label_from_catalogue():
    b = flows.btn("lang:ms:-", "btn.lang_ms", "ms")
    assert b.id == "lang:ms:-"
    assert b.label == label("btn.lang_ms", "ms")


# ---- Step 2: first contact and language buttons ----

def test_first_message_gets_language_choice_then_welcome():
    store = InMemoryStore()
    out = flows.handle_event(make_event(text="Daftar"), store, DEPS)
    assert len(out) == 2
    assert out[0].text == render("s.choose_lang", "ms")
    assert [b.id for b in out[0].buttons] == ["lang:ms:-", "lang:en:-"]
    assert out[1].text == render("s.welcome", "ms")


def test_duplicate_first_message_gets_one_greeting():
    store = InMemoryStore()
    flows.handle_event(make_event(text="hi", msg_id="same"), store, DEPS)
    again = flows.handle_event(make_event(text="hi", msg_id="same"), store, DEPS)
    assert again == []


def test_choosing_english_saves_language_and_confirms():
    store = InMemoryStore()
    flows.handle_event(make_event(text="hi", msg_id="m1"), store, DEPS)
    out = flows.handle_event(
        make_event(kind="button", button_id="lang:en:-", msg_id="m2"), store, DEPS)
    user = store.get_user("sim:anak")
    assert user.lang == "en" and user.lang_chosen is True
    assert out[0].text == render("s.lang_changed", "en")

# ---- Step 3: route_text ----
import itertools
import re

_ids = itertools.count(1)


def say(store, user, text):
    """One user types one line. Every call gets a fresh msg_id."""
    return flows.handle_event(
        make_event(text=text, user=user, msg_id=f"t{next(_ids)}"), store, DEPS)


def get_code(store):
    """Child registers and asks for a code. Returns the code."""
    say(store, "sim:anak", "hi")                   # first contact greeting
    say(store, "sim:anak", "Daftar")
    out = say(store, "sim:anak", "mak")
    return re.search(r"Kod anda: (\w{6})", out[0].text).group(1)


def test_daftar_asks_for_name_then_gives_code():
    store = InMemoryStore()
    say(store, "sim:anak", "hi")
    out = say(store, "sim:anak", "Daftar")
    assert out[0].text == render("s.ask_address", "ms")
    assert store.get_user("sim:anak").role == Role.PRIMARY
    out = say(store, "sim:anak", "mak")
    code = re.search(r"Kod anda: (\w{6})", out[0].text).group(1)
    pc = store.peek_pair_code(code, 1000.0)
    assert pc.target_role == Role.PARENT and pc.address_as == "Mak"


def test_generated_codes_never_use_lookalike_characters():
    store = InMemoryStore()
    for _ in range(200):
        code = flows.new_pair_code(store, 1000.0)
        assert len(code) == 6
        assert set(code) <= set(flows.CODE_ALPHABET)
        assert not set(code) & set("0O1I")


def test_parent_sends_code_and_gets_consent_button():
    store = InMemoryStore()
    code = get_code(store)
    say(store, "sim:mak", "hi")
    out = say(store, "sim:mak", code.lower())       # lowercase must work too
    assert out[0].text == render("s.consent", "ms", address_as="Mak")
    assert out[0].buttons[0].id == f"consent:yes:{code}"


def test_unknown_code_is_rejected():
    store = InMemoryStore()
    say(store, "sim:mak", "hi")
    out = say(store, "sim:mak", "ZZZZZZ")
    assert out[0].text == render("s.code_invalid", "ms")


def test_six_letter_commands_are_not_mistaken_for_codes():
    store = InMemoryStore()
    say(store, "sim:mak", "hi")
    out = say(store, "sim:mak", "BAHASA")
    assert out[0].text == render("s.choose_lang", "ms")
    assert len(out[0].buttons) == 2


def test_berhenti_asks_for_confirmation():
    store = InMemoryStore()
    say(store, "sim:mak", "hi")
    out = say(store, "sim:mak", "berhenti")
    assert out[0].text == render("h.stop_confirm", "ms")
    assert out[0].buttons[0].id == "stop:confirm:-"


def test_other_text_gets_help():
    store = InMemoryStore()
    say(store, "sim:mak", "hi")
    out = say(store, "sim:mak", "hello there")
    assert out[0].text == render("h.help", "ms")

# ---- Step 4: consent, stop, second contact ----

def press(store, user, button_id):
    """One user taps one button."""
    return flows.handle_event(
        make_event(kind="button", button_id=button_id, user=user,
                   msg_id=f"b{next(_ids)}"), store, DEPS)


def link_pair(store):
    """Anak registers, Mak sends the code and taps Setuju. Returns (code, outputs)."""
    code = get_code(store)
    say(store, "sim:mak", "hi")
    say(store, "sim:mak", code)
    return code, press(store, "sim:mak", f"consent:yes:{code}")


def test_consent_links_parent_and_child():
    store = InMemoryStore()
    code, out = link_pair(store)
    assert [o.to for o in out] == ["sim:mak", "sim:anak", "sim:mak"]
    assert out[0].text == render("s.linked_parent", "ms", address_as="Mak")
    assert out[1].text == render("s.linked_child", "ms", address_as="Mak")
    assert out[2].text == render("s.practice_invite", "ms")
    mak = store.get_user("sim:mak")
    assert mak.role == Role.PARENT and mak.address_as == "Mak"
    assert mak.consent_at == 1000.0 and mak.practice_pending is True
    links = store.get_links("sim:mak")
    assert len(links) == 1 and links[0].contact_id == "sim:anak"
    assert links[0].contact_type == Role.PRIMARY
    assert store.find_parent_of("sim:anak") == "sim:mak"


def test_pairing_code_works_only_once():
    store = InMemoryStore()
    code, _ = link_pair(store)
    say(store, "sim:other", "hi")
    out = press(store, "sim:other", f"consent:yes:{code}")
    assert out[0].text == render("s.code_invalid", "ms")
    assert store.get_user("sim:other").role == Role.NONE


def test_berhenti_confirm_deletes_user_and_tells_contact():
    store = InMemoryStore()
    link_pair(store)
    out = press(store, "sim:mak", "stop:confirm:-")
    assert out[0].to == "sim:mak" and out[0].text == render("h.stopped", "ms")
    assert any(o.to == "sim:anak" and o.text == render("h.contact_left", "ms")
               for o in out)
    assert store.get_user("sim:mak") is None
    assert store.get_links("sim:mak") == []


def test_tambah_adds_one_second_contact_only():
    store = InMemoryStore()
    link_pair(store)
    out = say(store, "sim:anak", "Tambah")
    code2 = re.search(r"Kod untuk ahli keluarga kedua: (\w{6})", out[0].text).group(1)

    say(store, "sim:adik", "hi")
    out = say(store, "sim:adik", code2)
    assert out[0].text == render("s.second_invite", "ms", address_as="Mak")
    out = press(store, "sim:adik", f"accept2:yes:{code2}")
    assert out[0].to == "sim:adik"
    assert out[0].text == render("s.second_linked", "ms", address_as="Mak")
    assert out[1].to == "sim:anak"
    assert out[1].text == render("s.second_linked_primary", "ms", address_as="Mak")
    kinds = {l.contact_type for l in store.get_links("sim:mak")}
    assert kinds == {Role.PRIMARY, Role.SECOND}

    out = say(store, "sim:anak", "Tambah")           # a third link is refused
    assert out[0].text == render("s.second_exists", "ms", address_as="Mak")


def test_tambah_by_someone_who_is_not_a_linked_primary_is_refused():
    store = InMemoryStore()
    say(store, "sim:random", "hi")
    out = say(store, "sim:random", "Tambah")
    assert out[0].text == render("s.not_primary", "ms")