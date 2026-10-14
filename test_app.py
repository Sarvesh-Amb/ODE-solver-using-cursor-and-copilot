import math
import unittest

from app import compile_expression, solve_ode


class SolveODETests(unittest.TestCase):
    def test_rk4_solves_exponential_growth(self):
        points = solve_ode("y", 0, 1, 1, 20, "RK4")
        self.assertAlmostEqual(points[-1]["y"], math.e, places=6)
        self.assertEqual(len(points), 21)
        self.assertEqual(points[0]["t"], 0)
        self.assertEqual(points[-1]["t"], 1)

    def test_methods_solve_constant_derivative(self):
        for method in ("Euler", "Heun", "RK4"):
            with self.subTest(method=method):
                points = solve_ode("2", 1, 4, 3, 8, method)
                self.assertAlmostEqual(points[-1]["y"], 8)

    def test_reverse_interval_is_supported(self):
        points = solve_ode("1", 2, 5, 0, 4, "RK4")
        self.assertAlmostEqual(points[-1]["y"], 3)
        self.assertEqual(points[-1]["t"], 0)

    def test_rejects_code_execution_and_unknown_names(self):
        for expression in ("__import__('os')", "t.real", "unknown + y"):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                compile_expression(expression)

    def test_rejects_unbounded_expression_complexity(self):
        for expression in ("y ** (y + 1)", "2 ** 1001", "y" * 257):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                compile_expression(expression)

    def test_rejects_invalid_inputs_and_non_finite_solution(self):
        with self.assertRaises(ValueError):
            solve_ode("y", 0, 1, 1, 0)
        with self.assertRaises(ValueError):
            solve_ode("1 / (t - t)", 0, 1, 1, 2)


if __name__ == "__main__":
    unittest.main()