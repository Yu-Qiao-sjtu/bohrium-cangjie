"""Rewrite a Wisp Cangjie skill tree into Bohrium desktop skills.

Cangjie ``compile_single.py`` / ``compile_pack.py`` emit a block-scalar
``description`` plus ``tags``, ``wisp`` and ``metadata``. SciX 0.10.17 keeps
only a single-line ``name`` and ``description``, and the ``name`` must equal
the skill directory. The instruction body is copied unchanged.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bohrium_cangjie.contract import FORBIDDEN_KEYS, is_skill_name, quote_scalar, sanitize_description


class AdaptError(ValueError):
    """The source skill cannot be made to satisfy the Bohrium contract."""


@dataclass
class SkillReport:
    name: str
    status: str
    source: str
    output: str
    stripped_keys: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    description_chars: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def split_frontmatter(raw: str) -> tuple[str, str, bool]:
    text = raw
    bom = text.startswith("\ufeff")
    if bom:
        text = text[1:]
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise AdaptError("missing opening frontmatter fence")
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n") == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1 :]), bom
    raise AdaptError("missing closing frontmatter fence")


def parse_frontmatter(frontmatter: str) -> dict[str, str]:
    """Read top-level scalars. Nested maps are recorded as empty and skipped."""
    lines = frontmatter.splitlines()
    data: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line[0] in " \t":
            raise AdaptError("frontmatter has an indented line outside a value")
        key, separator, rest = line.partition(":")
        if separator != ":" or not key.strip() or key != key.strip():
            raise AdaptError(f"frontmatter line is not a field: {line!r}")
        key = key.strip()
        if key in data:
            raise AdaptError(f"duplicate {key} frontmatter field")
        rest = rest.strip()
        if rest in {"|", "|-", "|+", ">", ">-", ">+"}:
            index += 1
            block: list[str] = []
            while index < len(lines):
                current = lines[index]
                if current.strip() == "":
                    following = index + 1
                    if following < len(lines) and lines[following][:1] in " \t":
                        block.append("")
                        index += 1
                        continue
                    break
                if current[:1] not in " \t":
                    break
                block.append(current.strip())
                index += 1
            data[key] = "\n".join(block).strip()
            continue
        if rest == "":
            index += 1
            while index < len(lines) and (not lines[index].strip() or lines[index][:1] in " \t"):
                index += 1
            data[key] = ""
            continue
        data[key] = _unquote(rest)
        index += 1
    return data


def render_skill(name: str, description: str, body: str) -> str:
    return f"---\nname: {name}\ndescription: {quote_scalar(description)}\n---\n{body}"


def adapt_skill_text(raw: str, directory_name: str) -> tuple[str, SkillReport]:
    if not is_skill_name(directory_name):
        raise AdaptError(
            f"directory name {directory_name!r} is not a lowercase kebab-case skill name shorter than 64 characters"
        )
    frontmatter, body, bom = split_frontmatter(raw)
    fields = parse_frontmatter(frontmatter)
    notes: list[str] = []
    if bom:
        notes.append("removed UTF-8 BOM")
    source_name = fields.get("name", "")
    if source_name != directory_name:
        notes.append(f"set name to the directory name {directory_name!r}")
    description_source = fields.get("description", "")
    if not description_source.strip():
        raise AdaptError("missing description frontmatter field")
    description, description_notes = sanitize_description(description_source)
    notes.extend(description_notes)
    if not description:
        raise AdaptError("description is empty after normalization")
    stripped = [key for key in fields if key not in {"name", "description"}]
    forbidden = sorted(set(stripped) & FORBIDDEN_KEYS)
    if forbidden:
        notes.append("removed invocation keys " + ", ".join(forbidden))
    text = render_skill(directory_name, description, body)
    if text.encode("utf-8").startswith(b"\xef\xbb\xbf"):
        raise AdaptError("refusing to write a BOM")
    report = SkillReport(
        name=directory_name,
        status="adapted",
        source="",
        output="",
        stripped_keys=stripped,
        notes=notes,
        description_chars=len(description),
    )
    return text, report


def adapt_path(source: Path, dest: Path) -> list[SkillReport]:
    source = source.resolve()
    dest = dest.resolve()
    _reject_symlink(source)
    if (source / "SKILL.md").is_file():
        return [adapt_directory(source, dest)]
    children = _skill_children(source)
    if not children:
        raise AdaptError(f"no SKILL.md found in {source}")
    if dest.exists():
        raise AdaptError(f"output already exists: {dest}")
    dest.mkdir(parents=True)
    reports: list[SkillReport] = []
    try:
        for child in children:
            reports.append(adapt_directory(child, dest / child.name))
        for entry in source.iterdir():
            if entry.name.startswith(".") or entry.name in {child.name for child in children}:
                continue
            _reject_symlink(entry)
            target = dest / entry.name
            if entry.is_file():
                shutil.copyfile(entry, target)
            elif entry.is_dir():
                _copy_tree(entry, target)
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    if any(item.status == "rejected" for item in reports):
        shutil.rmtree(dest)
        for item in reports:
            item.output = ""
            item.notes.append("pack output removed because a skill was rejected")
    return reports


def adapt_directory(source: Path, dest: Path) -> SkillReport:
    source = source.resolve()
    dest = dest.resolve()
    skill_file = source / "SKILL.md"
    if not skill_file.is_file():
        raise AdaptError(f"missing SKILL.md in {source}")
    _reject_symlink(source)
    _reject_symlink(skill_file)
    if dest.exists():
        raise AdaptError(f"output already exists: {dest}")
    try:
        raw = skill_file.read_text(encoding="utf-8")
    except UnicodeError as exc:
        return SkillReport(
            name=source.name,
            status="rejected",
            source=str(source),
            output=str(dest),
            notes=[f"SKILL.md is not UTF-8: {exc}"],
        )
    try:
        rewritten, report = adapt_skill_text(raw, source.name)
    except AdaptError as exc:
        return SkillReport(
            name=source.name,
            status="rejected",
            source=str(source),
            output=str(dest),
            notes=[str(exc)],
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        _copy_tree(source, dest)
        (dest / "SKILL.md").write_text(rewritten, encoding="utf-8", newline="\n")
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    report.source = str(source)
    report.output = str(dest)
    return report


def _skill_children(source: Path) -> list[Path]:
    children = []
    for entry in sorted(source.iterdir(), key=lambda item: item.name):
        if entry.name.startswith("."):
            continue
        _reject_symlink(entry)
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            children.append(entry)
    return children


def _copy_tree(source: Path, dest: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        blocked: set[str] = set()
        for name in names:
            if name.startswith("."):
                blocked.add(name)
                continue
            path = Path(directory) / name
            if path.is_symlink():
                raise AdaptError(f"refusing to copy symlink: {path}")
        return blocked

    shutil.copytree(source, dest, ignore=ignore, copy_function=shutil.copyfile)


def _reject_symlink(path: Path) -> None:
    if path.is_symlink() or os.path.islink(path):
        raise AdaptError(f"refusing to read symlink: {path}")


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        inner = value[1:-1]
        if value[0] == '"':
            return inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner.replace("''", "'")
    return value
