import importlib.util
import unittest
from pathlib import Path

file = Path(__file__).resolve().parents[1] / "scripts/yel_test_005_navigation.py"
spec = importlib.util.spec_from_file_location("navigation", file)
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)


class Navigation(unittest.TestCase):
    def test_simple_route(self):
        self.assertEqual(nav.shortest_path((0, 0), (2, 0), 3, 2), ["right", "right"])

    def test_avoid_wall(self):
        route = nav.shortest_path((0, 0), (2, 0), 3, 2, [(1, 0)])
        self.assertEqual(route, ["down", "right", "right", "up"])

    def test_unreachable(self):
        with self.assertRaises(ValueError):
            nav.shortest_path((0, 0), (2, 0), 3, 1, [(1, 0)])

    def test_exact_one_tile(self):
        self.assertEqual(nav.verify_step({"map": 38, "x": 3, "y": 6},
                                         {"map": 38, "x": 3, "y": 7},
                                         "down"), "verified_tile")

    def test_stationary_rejected(self):
        with self.assertRaises(AssertionError):
            nav.verify_step({"map": 38, "x": 3, "y": 6},
                            {"map": 38, "x": 3, "y": 6}, "down")

    def test_two_tiles_rejected(self):
        with self.assertRaises(AssertionError):
            nav.verify_step({"map": 38, "x": 3, "y": 6},
                            {"map": 38, "x": 3, "y": 8}, "down")

    def test_unknown_warp_rejected(self):
        with self.assertRaises(AssertionError):
            nav.verify_step({"map": 38, "x": 7, "y": 2},
                            {"map": 37, "x": 7, "y": 1}, "up")

    def test_expected_warp(self):
        self.assertEqual(nav.verify_step({"map": 38, "x": 7, "y": 2},
                                         {"map": 37, "x": 7, "y": 1}, "up",
                                         allowed_warp=(37, 7, 1)), "verified_warp")


if __name__ == "__main__":
    unittest.main()
