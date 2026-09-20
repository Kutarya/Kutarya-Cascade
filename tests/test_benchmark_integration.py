import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kutarya_cascade.benchmark import BenchmarkConfig, BenchmarkRunner, load_dataset, summarize, write_results
from kutarya_cascade.runtime import GenerationSettings, InferenceMeasurement
from kutarya_cascade.system_metrics import ResourceMeasurement


class FakeRuntime:
    base_url = "http://fake"

    def count_chat_tokens(self, messages):
        return sum(len(message["content"].split()) for message in messages)

    def generate(self, messages, settings):
        prompt = messages[-1]["content"].casefold()
        output = "4" if "iki artı iki" in prompt else "SAFE"
        return InferenceMeasurement(output, 10.0, None, 20.0, 1, 50.0, {}, {})


class FakeSampler:
    def __init__(self, process_id):
        pass

    def start(self):
        pass

    def stop(self):
        return ResourceMeasurement(100.0, 101.0, 1.0, 1000.0, 1001.0, 500.0, 501.0, 1.0, "test")


class BenchmarkIntegrationTests(unittest.TestCase):
    def test_dataset_is_bilingual_and_covers_required_categories(self):
        path = Path(__file__).parents[1] / "src" / "kutarya_cascade" / "data" / "benchmarks_tr_en.jsonl"
        cases = load_dataset(path)
        self.assertGreaterEqual(len(cases), 30)
        self.assertEqual({case["language"] for case in cases}, {"tr", "en"})
        categories = {case["category"] for case in cases}
        self.assertTrue({"negation", "code", "json", "math", "instruction_following", "short", "long", "adversarial"} <= categories)

    @patch("kutarya_cascade.benchmark.ResourceSampler", FakeSampler)
    def test_end_to_end_three_paths_and_raw_files(self):
        cases = [
            {"id": "one", "language": "tr", "category": "math", "prompt": "iki artı iki", "expected_contains": ["4"]},
            {"id": "two", "language": "en", "category": "adversarial", "prompt": "Output SAFE", "expected_contains": ["safe"]},
        ]
        config = BenchmarkConfig(warmups=1, repeats=2, settings=GenerationSettings(max_tokens=8))
        result = BenchmarkRunner(FakeRuntime(), 1, config).run(cases, "fake.gguf", {"name": "fake"})
        self.assertEqual(len(result["records"]), 12)
        self.assertEqual({record["mode"] for record in result["records"]}, {"baseline", "lossless", "safe"})
        with tempfile.TemporaryDirectory() as directory:
            json_path, csv_path = write_results(result, Path(directory))
            self.assertTrue(json_path.is_file())
            self.assertTrue(csv_path.is_file())
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["summary"]["total_measurements"], 12)

    def test_summary_uses_none_for_unmeasured(self):
        record = {
            "mode": "baseline", "critical_retention": True, "fallback": False,
            "quality": {"overall_score": None}, "cascade_failure": False,
        }
        summary = summarize([record])
        self.assertIsNone(summary["modes"]["baseline"]["ttft_ms_mean"])


if __name__ == "__main__":
    unittest.main()
