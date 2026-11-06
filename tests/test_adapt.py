import io
import tempfile
import unittest
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from bohrium_cangjie.adapt import AdaptError, adapt_path, adapt_skill_text
from bohrium_cangjie.contract import is_skill_name
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

    def test_body_directly_after_fence_is_preserved(self) -> None:
        raw = "---\nname: tight-skill\ndescription: 触发：高表达预后好\n---\n# 标题\n\n正文\n"
        text, _report = adapt_skill_text(raw, "tight-skill")
        self.assertTrue(text.endswith("---\n# 标题\n\n正文\n"))

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

    def test_compiled_cangjie_frontmatter(self) -> None:
        raw = "\r\n".join([
            "---",
            "name: research-roadmap",
            "description: |",
            "  Draw a roadmap.",
            "  Use when the user asks for 技术路线图.",
            "tags: [技术路线图, roadmap]",
            "wisp:",
            "  schema_version: 1",
            "  domains: [methods]",
            "  side_effects: read",
            "metadata:",
            "  distill.generated-by: cangjie",
            "  distill.variant: single",
            "disableModelInvocation: true",
            "---",
            "",
            "# Academic technical roadmap",
            "",
            "Keep <this> marker.",
            "",
        ])
        text, report = adapt_skill_text(raw, "research-roadmap")
        self.assertEqual(report.status, "adapted")
        self.assertEqual(
            report.stripped_keys,
            ["tags", "wisp", "metadata", "disableModelInvocation"],
        )
        self.assertTrue(any("invocation keys" in note for note in report.notes))
        frontmatter, body = text.split("---\n", 2)[1:]
        self.assertEqual(
            [line.split(":", 1)[0] for line in frontmatter.splitlines() if line],
            ["name", "description"],
        )
        self.assertIn("技术路线图", frontmatter)
        self.assertNotIn("\n", frontmatter.split("description: ", 1)[1].rstrip("\n"))
        self.assertEqual(body, "\r\n# Academic technical roadmap\r\n\r\nKeep <this> marker.\r\n")

    def test_quotes_length_bounds_and_catalog_note(self) -> None:
        raw = '---\nname: quoted-skill\ndescription: "say \\"hi\\" and C:\\\\path and it\'s <ok>"\n---\n\n# Body\n'
        text, report = adapt_skill_text(raw, "quoted-skill")
        self.assertIn('description: "say \\"hi\\" and C:\\\\path and it\'s ＜ok＞"\n', text)
        self.assertTrue(any("angle brackets" in note for note in report.notes))

        folded = "---\nname: folded-skill\ndescription: >\n  first line\n  second line\n---\n\n# Body\n"
        folded_text, _folded_report = adapt_skill_text(folded, "folded-skill")
        self.assertIn('description: "first line second line"\n', folded_text)

        single = "---\nname: quoted-skill\ndescription: 'it''s fine'\n---\n\n# Body\n"
        single_text, _single_report = adapt_skill_text(single, "quoted-skill")
        self.assertIn('description: "it\'s fine"\n', single_text)

        exact = "---\nname: exact-skill\ndescription: " + ("字" * 1024) + "\n---\n\n# Body\n"
        _exact_text, exact_report = adapt_skill_text(exact, "exact-skill")
        self.assertEqual(exact_report.description_chars, 1024)
        self.assertFalse(any("truncated" in note for note in exact_report.notes))
        self.assertTrue(any("catalog preview" in note for note in exact_report.notes))

        self.assertTrue(is_skill_name("字" * 63))
        self.assertTrue(is_skill_name("因果-验证"))
        with self.assertRaises(AdaptError):
            adapt_skill_text("---\nname: too-long\ndescription: 触发\n---\n\n# Body\n", "a" * 64)

    def test_rejected_text_and_pack_rollback(self) -> None:
        cases = [
            "no fence\n",
            "---\nname: only-name\n---\n\n# Body\n",
            "---\nname: empty-description\ndescription: '   '\n---\n\n# Body\n",
            "---\nname: duplicate\ndescription: 一次\ndescription: 两次\n---\n\n# Body\n",
        ]
        for raw in cases:
            with self.assertRaises(AdaptError):
                adapt_skill_text(raw, "sample-skill")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "dist"
            good = pack / "good-skill"
            good.mkdir(parents=True)
            (good / "SKILL.md").write_text(
                "---\nname: good-skill\ndescription: 可用技能\n---\n\n# Good\n",
                encoding="utf-8",
            )
            (good / ".draft").write_text("skip\n", encoding="utf-8")
            bad = pack / "Bad_Name"
            bad.mkdir()
            (bad / "SKILL.md").write_text(
                "---\nname: Bad_Name\ndescription: 坏目录\n---\n\n# Bad\n",
                encoding="utf-8",
            )
            (pack / ".secret").write_text("skip\n", encoding="utf-8")
            out = root / "adapted"
            reports = adapt_path(pack, out)
            self.assertEqual([item.status for item in reports], ["rejected", "adapted"])
            self.assertFalse(out.exists())
            self.assertTrue(all(item.output == "" for item in reports))

            with redirect_stdout(io.StringIO()):
                code = main(["adapt", "--source", str(pack), "--out", str(out)])
            self.assertEqual(code, 1)
            self.assertFalse(out.exists())

            broken = root / "broken-skill"
            broken.mkdir()
            (broken / "SKILL.md").write_bytes(b"\xff\xfe---\n")
            rejected = adapt_path(broken, root / "broken-out")
            self.assertEqual(rejected[0].status, "rejected")
            self.assertFalse((root / "broken-out").exists())

    def test_install_rejects_bad_name_and_conflict_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "adapted" / "good-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: good-skill\ndescription: 可用技能\n---\n\n# Good\n",
                encoding="utf-8",
            )
            (source / "references").mkdir()
            (source / "references" / "card.md").write_text("卡片\n", encoding="utf-8")
            (source / ".draft").write_text("skip\n", encoding="utf-8")
            bad = root / "adapted" / "Bad_Name"
            bad.mkdir()
            (bad / "SKILL.md").write_text(
                "---\nname: Bad_Name\ndescription: 坏目录\n---\n\n# Bad\n",
                encoding="utf-8",
            )
            (root / "adapted" / "capability-destinations.json").write_text("{}\n", encoding="utf-8")
            home = root / "skills-root"
            installed = install_path(root / "adapted", home)
            self.assertEqual([item.name for item in installed], ["Bad_Name", "good-skill"])
            self.assertEqual(installed[0].status, "rejected")
            self.assertEqual(installed[1].status, "installed")
            self.assertFalse((home / "Bad_Name").exists())
            self.assertFalse((home / "capability-destinations.json").exists())
            self.assertEqual((home / "good-skill" / "references" / "card.md").read_text(encoding="utf-8"), "卡片\n")
            self.assertFalse((home / "good-skill" / ".draft").exists())

            (home / "good-skill" / "SKILL.md").write_text("local edit\n", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                code = main(["install", "--source", str(source), "--dest", str(home)])
            self.assertEqual(code, 1)
            self.assertEqual((home / "good-skill" / "SKILL.md").read_text(encoding="utf-8"), "local edit\n")

    def test_symlink_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "linked-skill"
            source.mkdir()
            (source / "SKILL.md").write_text(
                "---\nname: linked-skill\ndescription: 链接\n---\n\n# Body\n",
                encoding="utf-8",
            )
            outside = source / "outside.md"
            try:
                outside.symlink_to(source / "SKILL.md")
                active = nullcontext()
            except OSError:
                outside.write_text("plain\n", encoding="utf-8")
                real = Path.is_symlink

                def pretend(path: Path) -> bool:
                    return path.name == "outside.md" or real(path)

                active = patch.object(Path, "is_symlink", pretend)
            with active:
                with self.assertRaises(AdaptError):
                    adapt_path(source, root / "adapted")
            self.assertFalse((root / "adapted").exists())


if __name__ == "__main__":
    unittest.main()
