"""Copy adapted skill directories into a Bohrium skill root.

An existing directory with the same bytes is left untouched. A different
directory is reported as a conflict and is not overwritten.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bohrium_cangjie.adapt import AdaptError, _copy_tree, _reject_symlink, _skill_children
from bohrium_cangjie.contract import is_skill_name


@dataclass
class InstallReport:
    name: str
    status: str
    source: str
    output: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def install_path(source: Path, root: Path) -> list[InstallReport]:
    source = source.resolve()
    root = root.resolve()
    _reject_symlink(source)
    root.mkdir(parents=True, exist_ok=True)
    if (source / "SKILL.md").is_file():
        skills = [source]
    else:
        skills = _skill_children(source)
        if not skills:
            raise AdaptError(f"no SKILL.md found in {source}")
    return [install_directory(skill, root / skill.name) for skill in skills]


def install_directory(source: Path, dest: Path) -> InstallReport:
    source = source.resolve()
    dest = dest.resolve()
    if not (source / "SKILL.md").is_file():
        raise AdaptError(f"missing SKILL.md in {source}")
    if not is_skill_name(source.name):
        return InstallReport(
            name=source.name,
            status="rejected",
            source=str(source),
            output=str(dest),
            notes=["directory name is not a lowercase kebab-case skill name shorter than 64 characters"],
        )
    report = InstallReport(name=source.name, status="installed", source=str(source), output=str(dest))
    if dest.exists():
        _reject_symlink(dest)
        if _tree_digest(source) == _tree_digest(dest):
            report.status = "unchanged"
            return report
        report.status = "conflict"
        report.notes.append("destination exists with different content and was left in place")
        return report
    staging = _staging_dir(dest)
    if staging.exists():
        shutil.rmtree(staging)
    try:
        _copy_tree(source, staging)
        os.replace(staging, dest)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def _staging_dir(dest: Path) -> Path:
    parent = dest.parent
    parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.mkdtemp(prefix=f".staging-{dest.name}-", dir=parent)
    os.rmdir(handle)
    return Path(handle)


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
