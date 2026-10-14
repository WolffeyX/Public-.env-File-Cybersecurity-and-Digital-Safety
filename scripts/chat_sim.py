"""Local chat simulator: test the whole bot with no AWS and no WhatsApp.

Run from the repo root (inside your venv):
    python scripts/chat_sim.py

Commands (each line is one user action):
    @anak  Daftar                 user "anak" types text
    @mak   img path/to/qr.png     user "mak" forwards an image
    @mak   img personal           fake image: personal | business | dynamic | noqr | url
                                  (works before Owner A's decoder is ready)
    @mak   tap 1                  tap button number 1 of the last message that user got
    timers                        run every delayed task now (reminders, escalation)
    quit
"""

from __future__ import annotations

import itertools
import os
import shlex
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.flows import handle_event                      # noqa: E402
from core.store import InMemoryStore                     # noqa: E402
from core.types import Deps, InboundEvent, Outbound, Task  # noqa: E402
from tests.fakes import BUSINESS, DYNAMIC, NO_QR, PERSONAL, URL  # noqa: E402

FAKES = {"personal": PERSONAL, "business": BUSINESS, "dynamic": DYNAMIC, "noqr": NO_QR, "url": URL}
PEPPER = b"local-sim-pepper"
ids = itertools.count(1)


def decode_image(data: bytes):
    key = data.decode(errors="ignore")
    if key in FAKES:
        return FAKES[key]
    try:
        from core.classify import decode_and_classify
        return decode_and_classify(data, PEPPER)
    except NotImplementedError:
        print("  (decoder not built yet, using NO_QR; try `img personal`)")
        return NO_QR


def fetch_media(user_id: str, ref: str) -> bytes:
    return ref.encode() if ref in FAKES else open(ref, "rb").read()


def main() -> None:
    store = InMemoryStore()
    deps = Deps(fetch_media=fetch_media, decode_image=decode_image, now=time.time,
                new_id=lambda: f"{next(ids):06d}", pepper=PEPPER)
    last_buttons: dict[str, list] = {}
    delayed: list[Task] = []
    queue: list[InboundEvent] = []

    def run(event: InboundEvent) -> None:
        queue.append(event)
        while queue:
            e = queue.pop(0)
            try:
                results = handle_event(e, store, deps)
            except NotImplementedError as err:
                print(f"  [not built yet] {err}")
                return
            for r in results:
                if isinstance(r, Outbound):
                    print(f"\n  ➜ to {r.to}:\n    " + r.text.replace("\n", "\n    "))
                    for i, b in enumerate(r.buttons, 1):
                        print(f"    [{i}] {b.label}   ({b.id})")
                    if r.buttons:
                        last_buttons[r.to] = r.buttons
                elif isinstance(r, Task):
                    task_ev = InboundEvent("sim", r.user_id, f"task{next(ids)}", "task",
                                           time.time(), task=r.task, ref=r.ref)
                    if r.delay_s == 0:
                        queue.append(task_ev)
                    else:
                        print(f"  (scheduled '{r.task}' in {r.delay_s}s; type `timers` to run)")
                        delayed.append(task_ev)

    print(__doc__)
    while True:
        try:
            line = input("\n> ").strip()
        except EOFError:
            break
        if not line:
            continue
        if line == "quit":
            break
        if line == "timers":
            pending, delayed[:] = list(delayed), []
            for t in pending:
                run(t)
            continue
        if not line.startswith("@"):
            print("start with @name, e.g. @mak img personal")
            continue
        who, _, rest = line[1:].partition(" ")
        user = f"sim:{who}"
        parts = shlex.split(rest)
        base = dict(channel="sim", user_id=user, msg_id=f"m{next(ids)}", ts=time.time())
        if parts and parts[0] == "img":
            run(InboundEvent(kind="image", media_ref=parts[1], **base))
        elif parts and parts[0] == "tap":
            btns = last_buttons.get(user, [])
            n = int(parts[1]) - 1
            if not 0 <= n < len(btns):
                print("no such button")
                continue
            run(InboundEvent(kind="button", button_id=btns[n].id, **base))
        else:
            run(InboundEvent(kind="text", text=rest, **base))


if __name__ == "__main__":
    main()
