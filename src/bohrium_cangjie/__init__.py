"""Adapt Wisp Cangjie compiled skills to the Bohrium desktop contract."""

from bohrium_cangjie.adapt import AdaptError, SkillReport, adapt_path, adapt_skill_text
from bohrium_cangjie.install import InstallReport, install_path

__all__ = [
    "AdaptError",
    "InstallReport",
    "SkillReport",
    "adapt_path",
    "adapt_skill_text",
    "install_path",
]
__version__ = "0.1.0"
