"""Offline regression tests for DeepSeek fragment replacement events."""

import importlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
DeepSeekAPI = importlib.import_module(f'{ROOT.name}.api').DeepSeekAPI


class FragmentSnapshotTests(unittest.TestCase):
    def setUp(self):
        # Parsing requires no credentials, HTTP session, cookies, or PoW solver.
        self.api = DeepSeekAPI.__new__(DeepSeekAPI)
        self.api._reset_stream_state()

    def parse(self, event):
        return self.api._parse_chunk_sync('data: ' + json.dumps(event))

    def test_replacement_switches_hidden_thinking_to_answer(self):
        for operation in (None, 'SET'):
            with self.subTest(operation=operation):
                self.api._reset_stream_state()
                thinking = {'id': 2, 'type': 'THINK', 'content': 'Compute 2+2.'}
                self.assertIsNone(self.parse({'v': {'response': {'fragments': [thinking]}}}))
                event = {
                    'p': 'response/fragments',
                    'v': [thinking, {'id': 3, 'type': 'RESPONSE', 'content': '4'}],
                }
                if operation is not None:
                    event['o'] = operation
                self.assertEqual(self.parse(event), {
                    'type': 'text', 'content': '4', 'finish_reason': None,
                })
                self.assertEqual(self.parse({'v': '!'})['content'], '!')
                self.assertEqual(self.parse({'p': 'response/status', 'v': 'FINISHED'})[
                    'finish_reason'], 'stop')

    def test_replacement_keeps_thinking_hidden(self):
        self.assertIsNone(self.parse({
            'p': 'response/fragments',
            'v': [{'id': 2, 'type': 'THINK', 'content': 'Private reasoning'}],
        }))
        self.assertIsNone(self.parse({'v': ' more reasoning'}))

    def test_empty_and_invalid_snapshots_are_ignored(self):
        for fragments in ([], None, 'invalid', [None], [{'id': 3, 'type': 'RESPONSE', 'content': ''}]):
            with self.subTest(fragments=fragments):
                self.assertIsNone(self.parse({'p': 'response/fragments', 'v': fragments}))

    def test_append_still_selects_new_empty_fragment(self):
        self.assertIsNone(self.parse({
            'p': 'response/fragments', 'o': 'APPEND',
            'v': [{'id': 3, 'type': 'RESPONSE', 'content': ''}],
        }))
        self.assertEqual(self.parse({'v': '4'})['content'], '4')


if __name__ == '__main__':
    unittest.main()
