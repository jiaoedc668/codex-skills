import copy
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import check_batch_integrity
import content_contract
import format_acceptance
from test_dual_format_v6 import candidate_v6
from v5_fixtures import valid_persona


class RequestedCountTests(unittest.TestCase):
    def test_cli_accepts_explicit_two_inputs(self):
        args = check_batch_integrity.build_parser().parse_args([
            '--inputs', 'one.json', 'two.json', '--topic-pool', 'pool.json',
            '--persona', 'persona.json', '--feedback-ledger', 'feedback.jsonl',
        ])
        self.assertEqual(2, len(args.inputs))

    def test_v6_count_follows_pool_without_relaxing_other_gates(self):
        c = candidate_v6()
        errors = content_contract.validate_batch([c], valid_persona(), [],
            {'schema_version': 6, 'requested_candidate_count': 1})
        self.assertFalse(any('exactly 3' in e or 'positions must' in e for e in errors), errors)
        self.assertTrue(any('topic pool invalid' in e for e in errors))
        c['candidate']['position'] = 2
        errors = content_contract.validate_batch([c], valid_persona(), [],
            {'schema_version': 6, 'requested_candidate_count': 1})
        self.assertTrue(any('positions must' in e for e in errors))

    def test_custom_count_requires_explicit_request_and_keeps_results_separate(self):
        manifest = {'schema_version': 2, 'batch_id': 'custom', 'format': 'monologue',
            'submitted_at': '2026-09-09T12:00:00+08:00',
            'candidates': [{'candidate_id': 'c1', 'revision_id': 'r1'}],
            'root_cause': {'id': 'rc', 'hypothesis': 'test', 'changed_layer': 'argument', 'root_level_change': False}}
        with self.assertRaises(ValueError):
            format_acceptance.derive([manifest], [])
        manifest['requested_candidate_count'] = 1
        self.assertEqual('pending', format_acceptance.derive([manifest], [])['batches'][0]['state'])
        event = {'event_type': 'candidate_evaluation', 'feedback_id': 'e1', 'batch_id': 'custom',
            'candidate_id': 'c1', 'revision_id': 'r1', 'format': 'monologue',
            'evaluation': 'direct_shoot', 'reason_codes': ['OTHER'], 'preserve': ['观点清楚'], 'avoid': [], 'user_quote': '观点清楚，可以拍'}
        row = format_acceptance.derive([manifest], [event])['batches'][0]
        self.assertEqual('user_reviewed_custom_batch', row['state'])
        self.assertEqual(1, row['direct_shoot_count'])
        self.assertFalse(row['requires_rollback'])
        self.assertFalse(row['requires_root_cause_change'])
        duplicate = copy.deepcopy(manifest)
        duplicate['candidates'] *= 2
        duplicate['requested_candidate_count'] = 2
        with self.assertRaises(ValueError):
            format_acceptance.derive([duplicate], [])


if __name__ == '__main__':
    unittest.main()
