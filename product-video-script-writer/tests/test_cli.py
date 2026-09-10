from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(TEST_ROOT))

from fixtures import packet
from test_word_delivery import final_script


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_check_packet_prints_only_public_candidate_fields(self):
        source = self.root / "packet.json"
        source.write_text(json.dumps(packet("both"), ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "check_packet.py"), "--input", str(source), "--public-json"],
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        visible = json.loads(result.stdout)
        self.assertEqual(len(visible), 6)
        self.assertEqual(set(visible[0]), {"format", "theme", "creative_note", "full_copy", "estimated_seconds"})

    def test_check_packet_returns_nonzero_for_tampered_facts(self):
        value = packet("monologue")
        value["brief"]["selling_points"][0] = "虚构价格 79 元"
        source = self.root / "tampered.json"
        source.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "check_packet.py"), "--input", str(source)],
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("facts hash", result.stderr)

    def test_workspace_cli_registers_product_without_overwriting_history(self):
        brief_path = self.root / "brief.json"
        brief_path.write_text(json.dumps(packet()["brief"], ensure_ascii=False), encoding="utf-8")
        workspace = self.root / "workspace"
        command = [
            sys.executable, str(SKILL_ROOT / "scripts" / "manage_workspace.py"),
            "register-product", "--workspace-root", str(workspace), "--input", str(brief_path),
            "--user-quote", "用户原话：这是测试资料",
        ]
        first = subprocess.run(command, text=True, encoding="utf-8", capture_output=True)
        second = subprocess.run(command, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        lines = (workspace / "product-catalog.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertNotEqual(json.loads(lines[0])["event_id"], json.loads(lines[1])["event_id"])

    def test_real_cli_word_chain_blocks_then_generates_two_versions(self):
        value = packet()
        brief_path = self.root / "brief.json"
        copy_path = self.root / "copy.txt"
        script_path = self.root / "final.json"
        brief_path.write_text(json.dumps(value["brief"], ensure_ascii=False), encoding="utf-8")
        copy_text = value["candidates"][0]["full_copy"]
        copy_path.write_text(copy_text, encoding="utf-8")
        script_path.write_text(json.dumps(final_script(copy_text), ensure_ascii=False), encoding="utf-8")
        workspace = self.root / "workspace"
        output = self.root / "output"
        manager = [sys.executable, str(SKILL_ROOT / "scripts" / "manage_workspace.py")]
        generator = [
            sys.executable, str(SKILL_ROOT / "scripts" / "generate_word_cli.py"),
            "--workspace-root", str(workspace), "--product-id", "test-cleaner-x1",
            "--input", str(script_path), "--output-root", str(output),
        ]
        commands = [
            manager + ["register-product", "--workspace-root", str(workspace), "--input", str(brief_path), "--user-quote", "用户原话：登记测试产品"],
            manager + ["select", "--workspace-root", str(workspace), "--product-id", "test-cleaner-x1", "--candidate-id", "m1", "--copy-file", str(copy_path), "--user-quote", "用户原话：选第一条"],
        ]
        for command in commands:
            result = subprocess.run(command, text=True, encoding="utf-8", capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        blocked = subprocess.run(generator, text=True, encoding="utf-8", capture_output=True)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("确认", blocked.stderr)
        confirmed = subprocess.run(
            manager + ["confirm", "--workspace-root", str(workspace), "--product-id", "test-cleaner-x1", "--copy-file", str(copy_path), "--user-quote", "用户原话：确认当前全文"],
            text=True, encoding="utf-8", capture_output=True,
        )
        self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
        first = subprocess.run(generator, text=True, encoding="utf-8", capture_output=True)
        second = subprocess.run(generator, text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        first_path = Path(first.stdout.strip())
        second_path = Path(second.stdout.strip())
        self.assertTrue(first_path.exists() and second_path.exists())
        self.assertTrue(first_path.name.endswith("-V1.docx"))
        self.assertTrue(second_path.name.endswith("-V2.docx"))
        self.assertNotEqual(first_path, second_path)


if __name__ == "__main__":
    unittest.main()
