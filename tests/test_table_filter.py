import unittest

from iec104.table_filter import matches_filters


class FilterTests(unittest.TestCase):
    def test_combined_filters(self):
        row = ("CA 2019 / IOA 4235604", "11: Messwert skaliert", "20: Generalabfrage", "100", "1", "100", "good")
        self.assertTrue(matches_filters(row, {0: "4235604", 1: "skaliert", 6: "GOOD"}))
        self.assertFalse(matches_filters(row, {0: "4235604", 6: "IV"}))


if __name__ == "__main__":
    unittest.main()
