"""The baseline must fail rather than claim silently ignored resource limits."""
import unittest

from run_container_staging import read_limits


class ResourceLimitTests(unittest.TestCase):
    def test_accepts_enforced_one_cpu_and_memory(self):
        self.assertEqual(read_limits("100000 100000\n", "536870912\n"),
                         {"cpu.max": "100000 100000", "memory.max": 536870912})

    def test_rejects_unlimited_or_wrong_cpu(self):
        for value in ("max 100000", "200000 100000", "50000 100000"):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                read_limits(value, "536870912")

    def test_rejects_unlimited_or_zero_memory(self):
        for value in ("max", "0"):
            with self.subTest(value=value), self.assertRaises((RuntimeError, ValueError)):
                read_limits("100000 100000", value)
