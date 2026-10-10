import unittest

from dedup import process


class ProcessTest(unittest.TestCase):
    def test_sums_unique_events(self):
        self.assertEqual(process([{"id": "a", "amount": 100}, {"id": "b", "amount": 50}]), 150)

    def test_duplicate_counted_once(self):
        self.assertEqual(process([{"id": "a", "amount": 100}, {"id": "a", "amount": 100}]), 100)


if __name__ == "__main__":
    unittest.main()
