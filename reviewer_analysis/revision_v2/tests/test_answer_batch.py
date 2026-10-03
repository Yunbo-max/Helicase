import json
import tempfile
import unittest
from pathlib import Path
from reviewer_analysis.revision_v2 import answer_batch as ab


class FakeClient:
    public_config = {'test_only': True}
    def __init__(self): self.calls = 0
    def chat(self, prompt, payload):
        self.calls += 1
        return json.dumps(payload), {'input_tokens': 1, 'output_tokens': 1}, None


class BatchTests(unittest.TestCase):
    def test_resume_revalidates_success_without_repeating_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = FakeClient(); tasks = [{'key': [i], 'payload': {'x': i}} for i in range(3)]
            transform = lambda obj, task: {'x': obj['x']}
            out = ab.run_stage(tasks, Path(tmp), 'test', transform, client=c, workers=2)
            self.assertEqual(out['successful'], 3)
            ab.run_stage(tasks, Path(tmp), 'test', transform, client=c, workers=2)
            self.assertEqual(c.calls, 3)
            p = next((Path(tmp)/'items').glob('*.json')); row = json.loads(p.read_text())
            row['result']['x'] = 99; p.write_text(json.dumps(row))
            with self.assertRaises(ValueError): ab.run_stage(tasks, Path(tmp), 'test', transform, client=c)

    def test_failures_are_saved_and_never_silently_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = FakeClient()
            def transform(obj, task): raise ValueError('bad content')
            tasks = [{'key': [1], 'payload': {'x': 1}}]
            out = ab.run_stage(tasks, Path(tmp), 'test', transform, client=c)
            self.assertEqual(out['failed'], 1)
            ab.run_stage(tasks, Path(tmp), 'test', transform, client=c)
            self.assertEqual(c.calls, 1)
            with self.assertRaises(ValueError): ab.run_stage(tasks, Path(tmp), 'changed', transform, client=c)


if __name__ == '__main__': unittest.main()
