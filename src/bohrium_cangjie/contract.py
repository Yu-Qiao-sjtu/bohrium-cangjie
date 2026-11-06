"""Limits used when adapting a skill for the Bohrium desktop."""

from __future__ import annotations

import re
import unicodedata

DESCRIPTION_MAX_CHARS = 1024
CATALOG_PREVIEW_CHARS = 500
NAME_MAX_CHARS = 63
FORBIDDEN_KEYS = frozenset({
    "disableModelInvocation",
    "modelInvocable",
    "userInvocable",
})
USER_SKILL_DIRNAME = ".bohrium"
USER_SKILL_LEAF = "skills"


def is_skill_name(name: str) -> bool:
    """Match ``^[\\p{L}\\p{N}]+(?:-[\\p{L}\\p{N}]+)*$``, lowercase, length < 64."""
    if not name or len(name) > NAME_MAX_CHARS or name != name.lower():
        return False
    parts = name.split("-")
    return all(_is_name_part(part) for part in parts)


def _is_name_part(part: str) -> bool:
    if not part:
        return False
    return all(_is_letter_or_number(char) for char in part)


def _is_letter_or_number(char: str) -> bool:
    category = unicodedata.category(char)
    return category.startswith("L") or category.startswith("N")


def quote_scalar(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError("description must be a single line")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def sanitize_description(value: str) -> tuple[str, list[str]]:
    """Collapse whitespace and satisfy the desktop description rules."""
    notes: list[str] = []
    text = value.replace("<", "＜").replace(">", "＞")
    if text != value:
        notes.append("replaced angle brackets so the desktop scanner accepts the description")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > DESCRIPTION_MAX_CHARS:
        text = text[: DESCRIPTION_MAX_CHARS - 3].rstrip() + "..."
        notes.append(f"truncated description to {DESCRIPTION_MAX_CHARS} characters")
    if len(text) > CATALOG_PREVIEW_CHARS:
        notes.append(
            f"description is {len(text)} characters; the skill catalog preview keeps {CATALOG_PREVIEW_CHARS}"
        )
    return text, notes
