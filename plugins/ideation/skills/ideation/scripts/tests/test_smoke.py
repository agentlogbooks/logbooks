import unittest


class TestSmoke(unittest.TestCase):
    def test_testing_infrastructure_runs(self):
        self.assertEqual(2 + 2, 4)


if __name__ == "__main__":
    unittest.main()
