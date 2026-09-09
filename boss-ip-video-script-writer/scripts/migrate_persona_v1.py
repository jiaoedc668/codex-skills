#!/usr/bin/env python3
"""Explicitly authorized profile revision 2 migration with byte-exact backup."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path

from content_contract import validate_persona_model
from history_manager import (
    _replace_json_atomically, apply_persona_evolution, default_persona, now_iso,
)


def upgrade_persona(persona: dict) -> dict:
    failures = validate_persona_model(persona)
    if failures:
        raise ValueError('; '.join(failures))
    revision = persona.get('profile_revision', 1)
    if revision == 2:
        return deepcopy(persona)
    if revision != 1:
        raise ValueError('Only unversioned/revision 1 profiles can migrate to revision 2')
    updated = deepcopy(persona)
    template = default_persona()
    frame = updated.setdefault('production_frame', {})
    # Keep user-specific locations, relationships, platform and unknown extensions.
    for key, value in template['production_frame'].items():
        if key in {'default_format', 'duration', 'duration_reference'} or key not in frame:
            frame[key] = deepcopy(value)
    for collection in ('authorized_fictional_behaviors', 'stable_expression',
                       'visible_weaknesses', 'comedy_relationships'):
        replacements = {item['id']: item for item in template[collection]}
        existing = updated.get(collection, [])
        merged = []
        seen = set()
        for item in existing:
            key = item.get('id')
            if collection == 'authorized_fictional_behaviors' and key in {'B01', 'B05'}:
                continue
            # Preserve unknown project records and extra fields on known records.
            merged.append({**deepcopy(item), **deepcopy(replacements.get(key, {}))})
            seen.add(key)
        merged.extend(deepcopy(item) for key, item in replacements.items() if key not in seen)
        updated[collection] = merged
    current = {item['id']: item for item in updated['viewpoint_principles']}
    for item in template['viewpoint_principles']:
        previous = current.get(item['id'])
        if previous and previous['status'] != 'active':
            continue  # Never revive an explicitly retired principle.
        payload = {key: deepcopy(value) for key, value in item['versions'][0].items()
                   if key not in {'version', 'source_candidate_id', 'reason'}}
        updated = apply_persona_evolution(updated, {
            'schema_version': 1,
            'event_type': 'viewpoint_principle',
            'operation': 'revise' if previous else 'add',
            'record_id': item['id'],
            # The legacy contract names this field source_candidate_id; keep an
            # explicit maintenance namespace instead of inventing a candidate.
            'source_candidate_id': 'maintenance:boss-ip-v1.0.0',
            'reason': '用户授权规则维护：建议者边界迁移；不是候选评价',
            'record': payload,
        })
    updated.pop('legacy_v2', None)
    updated['profile_revision'] = 2
    updated['updated_at'] = now_iso()
    failures = validate_persona_model(updated)
    if failures:
        raise ValueError('; '.join(failures))
    return updated


def snapshot_path(persona_path: Path, archive_root: Path) -> Path:
    digest = hashlib.sha256(persona_path.read_bytes()).hexdigest()
    return archive_root / f'{date.today().isoformat()}-{digest[:12]}.json'


def migrate_file(persona_path: Path, archive_root: Path) -> dict:
    persona_path = persona_path.resolve()
    archive_root = archive_root.resolve()
    raw = persona_path.read_bytes()
    original = json.loads(raw.decode('utf-8-sig'))
    updated = upgrade_persona(original)
    before = hashlib.sha256(raw).hexdigest()
    if updated == original:
        return {'changed': False, 'persona': str(persona_path), 'sha256': before}
    snapshot = snapshot_path(persona_path, archive_root)
    if snapshot == persona_path:
        raise ValueError('Snapshot must differ from the live persona path')
    archive_root.mkdir(parents=True, exist_ok=True)
    if snapshot.exists():
        if snapshot.read_bytes() != raw:
            raise FileExistsError(f'Refusing to overwrite snapshot: {snapshot}')
    else:
        with snapshot.open('xb') as file:
            file.write(raw)
    if persona_path.read_bytes() != raw:
        raise ValueError('Persona changed during migration; live file was not replaced')
    _replace_json_atomically(persona_path, updated)
    return {'changed': True, 'persona': str(persona_path), 'snapshot': str(snapshot),
            'before_sha256': before,
            'after_sha256': hashlib.sha256(persona_path.read_bytes()).hexdigest(),
            'profile_revision': 2}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--persona', type=Path, required=True)
    parser.add_argument('--archive-root', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = migrate_file(args.persona, args.archive_root)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Migration refused: {exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
