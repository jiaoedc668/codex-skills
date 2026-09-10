from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent


class SkillStructureTests(unittest.TestCase):
    def test_entrypoint_has_valid_discoverable_frontmatter(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match)
        fields = {}
        for line in match.group(1).splitlines():
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
        self.assertEqual(fields["name"], "product-video-script-writer")
        self.assertTrue(fields["description"].startswith("Use when "))
        self.assertLessEqual(len(match.group(1)), 1024)
        self.assertNotRegex(text, r"\b(?:TODO|TBD)\b")

    def test_referenced_resources_and_executable_scripts_exist(self):
        for relative in (
            "references/candidate-packet.md",
            "references/workspace-events.md",
            "references/word-delivery.md",
            "scripts/check_packet.py",
            "scripts/manage_workspace.py",
            "scripts/generate_word_cli.py",
            "agents/openai.yaml",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((SKILL_ROOT / relative).is_file(), relative)

    def test_openai_metadata_keeps_implicit_discovery_enabled(self):
        text = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "产品视频脚本"', text)
        self.assertNotIn("allow_implicit_invocation: false", text)


if __name__ == "__main__":
    unittest.main()
