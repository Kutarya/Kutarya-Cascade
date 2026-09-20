import unittest

from kutarya_cascade.quality import evaluate_output, output_similarity


class QualityTests(unittest.TestCase):
    def test_contains_and_forbidden(self):
        case = {"expected_contains": ["ankara"], "forbidden_contains": ["istanbul"]}
        result = evaluate_output(case, "Başkent Ankara'dır.")
        self.assertEqual(result.overall_score, 1.0)

    def test_regex(self):
        result = evaluate_output({"expected_regex": "IndexError|indeks"}, "Bu bir IndexError hatasıdır.")
        self.assertTrue(result.expected_regex_pass)

    def test_no_oracle_is_unmeasured(self):
        self.assertIsNone(evaluate_output({}, "serbest yanıt").overall_score)

    def test_similarity(self):
        self.assertEqual(output_similarity("Aynı cevap", "aynı   cevap"), 1.0)


if __name__ == "__main__":
    unittest.main()
