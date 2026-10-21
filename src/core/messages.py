"""Message catalogue loader (Owner C). To change wording, edit the YAML files, not this code.

Usage:
    from core.messages import render, label
    render("q.who_asked", "ms", address_as="Mak")
    label("btn.claim_official", "ms")
"""

from __future__ import annotations

import functools
import string
from pathlib import Path

import yaml

MESSAGES_DIR = Path(__file__).resolve().parents[1] / "messages"
LANGS = ("ms", "en")
DEFAULT_LANG = "ms"


@functools.lru_cache(maxsize=None)
def catalogue(lang: str) -> dict[str, str]:
    if lang not in LANGS:
        lang = DEFAULT_LANG
    with open(MESSAGES_DIR / f"{lang}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def variables(text: str) -> set[str]:
    """Names of {placeholders} in a message."""
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def render(msg_id: str, lang: str, **params) -> str:
    """Fill in a message. Raises KeyError if the id or a variable is missing,
    so a broken message fails in tests instead of reaching a senior."""
    text = catalogue(lang)[msg_id]
    missing = variables(text) - params.keys()
    if missing:
        raise KeyError(f"{msg_id}: missing variables {sorted(missing)}")
    return text.format(**params)


def label(msg_id: str, lang: str) -> str:
    return catalogue(lang)[msg_id]
