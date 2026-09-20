import unittest

from kutarya_cascade.inspector import PromptInspector


class PromptInspectorTests(unittest.TestCase):
    def setUp(self):
        self.inspector = PromptInspector()

    def test_detects_turkish(self):
        self.assertEqual(self.inspector.inspect("Lütfen bunu Türkçe ve kısa yaz.").language, "tr")

    def test_detects_english(self):
        self.assertEqual(self.inspector.inspect("Please write this with no heading.").language, "en")

    def test_detects_negation_without_ascii_word_boundary_bug(self):
        values = [a.value.casefold() for a in self.inspector.inspect("Bunu değiştirme; değil ve asla deme.").artifacts if a.kind == "negation"]
        self.assertIn("değil", values)
        self.assertIn("asla", values)

    def test_detects_critical_literals(self):
        prompt = '2026-10-05 tarihinde 1.250 TL ve 3 kg; "Ada" için x >= 2 kullan.'
        result = self.inspector.inspect(prompt)
        kinds = {a.kind for a in result.artifacts}
        self.assertTrue({"date", "money", "unit", "quote", "operator"} <= kinds)

    def test_json_is_one_protected_artifact(self):
        result = self.inspector.inspect('Veri: {"active":false,"limit":7}')
        json_items = [a for a in result.artifacts if a.kind == "json"]
        self.assertEqual(len(json_items), 1)
        self.assertEqual(json_items[0].value, '{"active":false,"limit":7}')

    def test_code_fence_is_protected(self):
        result = self.inspector.inspect("Kod:\n```python\nx =  1\n```")
        self.assertEqual(result.count("code"), 1)

    def test_code_and_json_raise_risk(self):
        result = self.inspector.inspect('```js\nconst x=1;\n```\n{"x":1}')
        self.assertIn(result.risk_level, {"high", "critical"})

    def test_entity_detection(self):
        result = self.inspector.inspect("Ada Lovelace Analytical Engine üzerinde çalıştı.")
        self.assertGreaterEqual(result.count("entity"), 1)

    def test_single_entity_detection_inside_sentence(self):
        result = self.inspector.inspect("Başkent Ankara olarak kalmalıdır.")
        self.assertTrue(any("Ankara" in item.value for item in result.artifacts if item.kind == "entity"))

    def test_instruction_inside_sentence_is_protected(self):
        result = self.inspector.inspect("Bağlam verdim. Çıktıyı tam olarak üç madde yaz.")
        self.assertGreaterEqual(result.count("instruction"), 1)


if __name__ == "__main__":
    unittest.main()
