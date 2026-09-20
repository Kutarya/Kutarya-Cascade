import unittest

from kutarya_cascade.integrity import IntegrityGuard


class IntegrityGuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = IntegrityGuard()

    def test_identical_passes(self):
        self.assertTrue(self.guard.validate("asla 3 kg değil", "asla 3 kg değil").passed)

    def test_number_change_fails(self):
        result = self.guard.validate("limit 7", "limit 8")
        self.assertFalse(result.passed)
        self.assertTrue(any(item.startswith("number:7") for item in result.missing))

    def test_negation_removal_fails(self):
        self.assertFalse(self.guard.validate("Bunu asla silme", "Bunu sil").passed)

    def test_date_change_fails(self):
        self.assertFalse(self.guard.validate("2026-10-05", "2026-10-06").passed)

    def test_money_change_fails(self):
        self.assertFalse(self.guard.validate("Bütçe 1.250 TL", "Bütçe 1.500 TL").passed)

    def test_quote_change_fails(self):
        self.assertFalse(self.guard.validate('"SAFE" yaz', '"UNSAFE" yaz').passed)

    def test_json_change_fails(self):
        self.assertFalse(self.guard.validate('{"active":false}', '{"active":true}').passed)

    def test_operator_reordering_fails(self):
        self.assertFalse(self.guard.validate("<= sonra >=", ">= sonra <=").passed)


if __name__ == "__main__":
    unittest.main()
