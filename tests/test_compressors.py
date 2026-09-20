import random
import unittest

from kutarya_cascade.lossless import LosslessCompressor
from kutarya_cascade.pipeline import CascadePipeline


class CompressorTests(unittest.TestCase):
    def setUp(self):
        self.lossless = LosslessCompressor()
        self.pipeline = CascadePipeline()

    def test_lossless_exact_round_trip(self):
        original = "  Lütfen   kısa yaz.\n\n\nSon satır.  "
        transformed = self.lossless.compress(original)
        self.assertLess(len(transformed.text), len(original))
        self.assertEqual(transformed.restore(), original)

    def test_lossless_preserves_code_byte_for_byte(self):
        original = "Örnek  kod:\n```python\nx  =  1\n\n\nprint(x)\n```\n  Bitti"
        transformed = self.lossless.compress(original)
        self.assertIn("```python\nx  =  1\n\n\nprint(x)\n```", transformed.text)
        self.assertEqual(transformed.restore(), original)

    def test_lossless_preserves_json(self):
        original = 'Veri   {"name": "Ada  X", "limit":  7}'
        transformed = self.lossless.compress(original)
        self.assertIn('{"name": "Ada  X", "limit":  7}', transformed.text)
        self.assertEqual(transformed.restore(), original)

    def test_pipeline_lossless_retains_integrity(self):
        result = self.pipeline.process("Asla   3 kg değerini değiştirme.", "lossless")
        self.assertFalse(result.fallback)
        self.assertTrue(result.integrity.passed)
        self.assertIn("3 kg", result.compressed)

    def test_safe_removes_politeness_on_low_risk_prompt(self):
        result = self.pipeline.process("Lütfen basit bir selamlama yaz.", "safe")
        self.assertFalse(result.fallback)
        self.assertNotIn("Lütfen", result.compressed)

    def test_safe_deduplicates_low_risk_adjacent_sentence(self):
        result = self.pipeline.process("Kediyi tanımla. Kediyi tanımla.", "safe")
        self.assertFalse(result.fallback)
        self.assertEqual(result.compressed.count("Kediyi tanımla"), 1)

    def test_safe_falls_back_for_high_risk_json(self):
        prompt = 'Bu JSON\'ı koru: {"limit":7,"active":false}'
        result = self.pipeline.process(prompt, "safe")
        self.assertTrue(result.fallback)
        self.assertEqual(result.compressed, prompt)
        self.assertTrue(result.fallback_reason.startswith("risk_gate:"))

    def test_original_mode_never_changes_prompt(self):
        prompt = "  özgün   metin  "
        result = self.pipeline.process(prompt, "original")
        self.assertEqual(result.compressed, prompt)
        self.assertFalse(result.fallback)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            self.pipeline.process("x", "unsafe")  # type: ignore[arg-type]

    def test_lossless_round_trip_randomized_whitespace(self):
        rng = random.Random(42)
        atoms = ["Ada", " ", "  ", "\t", "\n", "\n\n\n", '"x  y"', '{"n":  7}', "`a  b`"]
        for _ in range(250):
            original = "".join(rng.choice(atoms) for _ in range(20))
            self.assertEqual(self.lossless.compress(original).restore(), original)


if __name__ == "__main__":
    unittest.main()
