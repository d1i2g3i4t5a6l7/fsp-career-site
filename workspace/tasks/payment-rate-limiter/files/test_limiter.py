import unittest

from clock import FakeClock
from limiter import RateLimiter


class RateLimiterTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.limiter = RateLimiter(limit=3, window=60, clock=self.clock)

    def test_allows_up_to_limit(self):
        self.assertEqual([self.limiter.allow("p1") for _ in range(4)], [True, True, True, False])

    def test_partners_are_independent(self):
        for _ in range(3):
            self.limiter.allow("p1")
        self.assertTrue(self.limiter.allow("p2"))

    def test_window_slides(self):
        self.limiter.allow("p1")  # t=0
        self.clock.advance(30)
        self.limiter.allow("p1")  # t=30
        self.limiter.allow("p1")  # t=30
        self.assertFalse(self.limiter.allow("p1"))
        self.clock.advance(31)  # t=61: запрос с t=0 вышел из окна, с t=30 — ещё нет
        self.assertTrue(self.limiter.allow("p1"))
        self.assertFalse(self.limiter.allow("p1"))


if __name__ == "__main__":
    unittest.main()
