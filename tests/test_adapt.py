import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from bohrium_cangjie.adapt import AdaptError, adapt_path, adapt_skill_text
from bohrium_cangjie.install import install_path
from bohrium_cangjie.__main__ import main


WISP_SKILL = """---
name: causal-check
description: |
  当用户说"怎么证明A是B的上下游"时触发。
  提供过表达+敲除+回补的组合验证标准。
tags: [molecular, causal]
wisp:
  schema_version: 1
  domains: [general]
metadata:
  distill.generated-by: cangjie
license: Apache-2.0
---

# 因果验证

正文保持不动。
"""


class AdaptTests(unittest.TestCase):
    def test_block_scalar_becomes_bohrium_frontmatter(self) -> None:
        text, report = adapt_skill_text(WISP_SKILL, "causal-check")
        self.assertEqual(report.status, "adapted")
        self.assertEqual(report.stripped_keys, ["tags", "wisp", "metadata", "license"])
        self.assertTrue(text.startswith("---\nname: causal-check\n"))
        self.assertNotIn("description: |", text)
        self.assertNotIn("tags:", text)
        self.assertNotIn("wisp:", text)
        self.assertIn("怎么证明A是B的上下游", text)
        self.assertTrue(text.endswith("\n# 因果验证\n\n正文保持不动。\n"))
        self.assertFalse(text.encode("utf-8").startswith(b"\xef\xbb\xbf"))

    def test_name_follows_directory(self) -> None:
        raw = "---\nname: other-name\ndescription: 触发：蒸馏成 skill\n---\n\n# Body\n"
        text, report = adapt_skill_text(raw, "bohrium-ready")
        self.assertIn("name: bohrium-ready\n", text)
        self.assertTrue(any("directory name" in note for note in report.notes))

    def test_angle_brackets_and_length(self) -> None:
        raw = "---\nname: long-skill\ndescription: 使用 <实验> 并且 " + ("词" * 1100) + "\n---\n\n# Body\n"
        text, report = adapt_skill_text(raw, "long-skill")
        description = text.split("\n", 3)[2]
        self.assertNotIn("<", description)
        self.assertNotIn(">", description)
        self.assertLessEqual(report.description_chars, 1024)
        self.assertTrue(any("angle brackets" in note for note in report.notes))
        self.assertTrue(any("truncated" in note for note in report.notes))

    def test_invalid_directory_is_rejected(self) -> None:
        with self.assertRaises(AdaptError):
            adapt_skill_text("---\nname: Bad_Name\ndescription: 触发\n---\n\n# Body\n", "Bad_Name")

    def test_pack_roundtrip_and_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "dist" / "causal-check"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("\ufeff" + WISP_SKILL, encoding="utf-8")
            (source / "references").mkdir()
            (source / "references" / "card.md").write_text("卡片\n", encoding="utf-8")
            pack = root / "dist"
            (pack / "capability-destinations.json").write_text("{}\n", encoding="utf-8")
            second = pack / "router-entry"
            second.mkdir()
            (second / "SKILL.md").write_text(
                "---\nname: router-entry\ndescription: 来源路由。用户说蒸馏结果怎么用时触发。\n---\n\n# Router\n",
                encoding="utf-8",
            )

            out = root / "adapted"
            reports = adapt_path(pack, out)
            self.assertEqual([item.status for item in reports], ["adapted", "adapted"])
            rewritten = (out / "causal-check" / "SKILL.md").read_bytes()
            self.assertFalse(rewritten.startswith(b"\xef\xbb\xbf"))
            self.assertEqual((out / "causal-check" / "references" / "card.md").read_text(encoding="utf-8"), "卡片\n")
            self.assertEqual((out / "capability-destinations.json").read_text(encoding="utf-8"), "{}\n")

            home = root / "skills-root"
            installed = install_path(out, home)
            self.assertEqual([item.status for item in installed], ["installed", "installed"])
            again = install_path(out, home)
            self.assertEqual([item.status for item in again], ["unchanged", "unchanged"])
            (home / "causal-check" / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            conflict = install_path(out / "causal-check", home)
            self.assertEqual(conflict[0].status, "conflict")
            self.assertEqual((home / "causal-check" / "SKILL.md").read_text(encoding="utf-8"), "local edit\n")

            with redirect_stdout(io.StringIO()):
                code = main(["adapt", "--source", str(pack), "--out", str(root / "cli-out")])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
