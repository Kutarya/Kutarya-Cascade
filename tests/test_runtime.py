import unittest

from kutarya_cascade.runtime import LlamaCppRuntime


class RuntimeTests(unittest.TestCase):
    def test_token_count_list(self):
        self.assertEqual(LlamaCppRuntime._token_count({"tokens": [1, 2, 3]}), 3)

    def test_token_count_explicit(self):
        self.assertEqual(LlamaCppRuntime._token_count({"count": 9}), 9)

    def test_token_count_unavailable(self):
        self.assertIsNone(LlamaCppRuntime._token_count({"x": 1}))

    def test_number_finds_first_supported_key(self):
        self.assertEqual(LlamaCppRuntime._number({"prompt_ms": 12.5}, "prompt_ms", "x"), 12.5)


if __name__ == "__main__":
    unittest.main()
