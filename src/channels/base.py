"""Helpers shared by all channels."""

from __future__ import annotations


def split_user_id(user_id: str) -> tuple[str, str]:
    """"wa:60123456789" -> ("wa", "60123456789")"""
    channel, _, raw = user_id.partition(":")
    return channel, raw


def make_user_id(channel: str, raw_id: str | int) -> str:
    return f"{channel}:{raw_id}"
