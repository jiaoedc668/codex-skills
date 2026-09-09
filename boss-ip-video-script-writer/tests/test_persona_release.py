from __future__ import annotations

import copy
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from history_manager import default_persona
from content_contract import validate_persona_model
from v5_fixtures import valid_persona


class PersonaReleaseTests(unittest.TestCase):
    def test_fresh_persona_uses_adviser_boundary_and_format_durations(self):
        persona = default_persona()
        self.assertEqual([], validate_persona_model(persona))
        self.assertEqual(2, persona.get('profile_revision'))
        self.assertNotIn('legacy_v2', persona)
        ids = {item['id'] for item in persona['authorized_fictional_behaviors']}
        self.assertNotIn('B01', ids)
        self.assertNotIn('B05', ids)
        self.assertEqual({'story', 'monologue'}, set(persona['production_frame']['duration_reference']))
        self.assertEqual(60, persona['production_frame']['duration_reference']['story']['target_seconds'])
        self.assertEqual(30, persona['production_frame']['duration_reference']['monologue']['target_seconds'])

    def test_upgrade_keeps_identity_custom_fields_and_prior_versions(self):
        migration = importlib.import_module('migrate_persona_v1')
        original = valid_persona()
        original['custom_note'] = {'keep': True}
        original['legacy_v2'] = {'old': 'historical duplicate'}
        before = copy.deepcopy(original)
        updated = migration.upgrade_persona(original)
        self.assertEqual(before, original)
        self.assertEqual(original['identity'], updated['identity'])
        self.assertEqual(original['custom_note'], updated['custom_note'])
        self.assertEqual(original['viewpoint_principles'][0]['versions'], updated['viewpoint_principles'][0]['versions'][:-1])
        self.assertEqual(2, updated['viewpoint_principles'][0]['active_version'])
        self.assertEqual([], validate_persona_model(updated))
        self.assertEqual(updated, migration.upgrade_persona(updated))

    def test_migration_archives_exact_bytes_and_repeat_is_noop(self):
        migration = importlib.import_module('migrate_persona_v1')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'persona.json'
            archive = Path(temp) / 'history'
            raw = (json.dumps(valid_persona(), ensure_ascii=False, indent=4) + '\r\n').encode('utf-8')
            path.write_bytes(raw)
            result = migration.migrate_file(path, archive)
            self.assertTrue(result['changed'])
            self.assertEqual(raw, Path(result['snapshot']).read_bytes())
            current = path.read_bytes()
            again = migration.migrate_file(path, archive)
            self.assertFalse(again['changed'])
            self.assertEqual(current, path.read_bytes())
            self.assertEqual(1, len(list(archive.glob('*.json'))))

    def test_invalid_input_or_archive_collision_cannot_change_persona(self):
        migration = importlib.import_module('migrate_persona_v1')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'persona.json'
            archive = Path(temp) / 'history'
            path.write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                migration.migrate_file(path, archive)
            self.assertEqual(b'{}', path.read_bytes())
            self.assertFalse(archive.exists())
            path.write_text(json.dumps(valid_persona()), encoding='utf-8')
            original = path.read_bytes()
            snapshot = migration.snapshot_path(path, archive)
            archive.mkdir()
            snapshot.write_bytes(b'conflicting evidence')
            with self.assertRaises(FileExistsError):
                migration.migrate_file(path, archive)
            self.assertEqual(original, path.read_bytes())
            self.assertEqual(b'conflicting evidence', snapshot.read_bytes())


if __name__ == '__main__':
    unittest.main()
