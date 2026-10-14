import unittest, itertools
import numpy as np
from model import Market


def hall(m, delta):
    ex, im, ei, ii, E, D, b, active, cap, S, B, L = m.prepare()
    worst = 0
    for bits in itertools.product([False, True], repeat=len(im)):
        s = np.array(bits)
        need = (L + delta * B)[s].sum()
        neighborhood = np.unique(ei[active & s[ii]])
        supply = cap[neighborhood].sum()
        ratio = (
            need / supply - delta if supply else (float("inf") if need > 1e-9 else 0)
        )
        worst = max(worst, ratio)
    return worst


class TestRestoration(unittest.TestCase):
    def test_swap_example(self):
        m = Market(
            np.array([1, 1, 2, 3]),
            np.array([4, 5, 5, 4]),
            np.array([1.0, 9.0, 10.0, 8.0]),
            np.array([0.0, 0.0, 0.0, 1.0]),
        )
        self.assertAlmostEqual(m.threshold(0)["rho"], 0.8)
        self.assertAlmostEqual(m.threshold(1)["rho"], 0.4)
        self.assertAlmostEqual(m.min_withdrawal(0.4), 4.0)
        self.assertAlmostEqual(m.threshold(1, budget=0)["rho"], 0.8)
        self.assertAlmostEqual(m.threshold(1, budget=0.2)["rho"], 0.4)
        self.assertAlmostEqual(m.threshold(0, target=0.95)["rho"], 0.76)
        self.assertAlmostEqual(m.threshold(1, target=0.95)["rho"], 0.38)

    def test_hall_random(self):
        rng = np.random.default_rng(1720406)
        for _ in range(150):
            e, i = np.where(rng.random((5, 5)) < 0.55)
            q = rng.uniform(0.1, 10, len(e))
            m = Market(e, i, q, (e == 0).astype(float))
            values = []
            for delta in [0, 0.1, 0.5, 0.9, 1]:
                a = m.threshold(delta)
                h = hall(m, delta)
                if np.isfinite(h):
                    self.assertTrue(a["success"])
                    self.assertAlmostEqual(a["rho"], h, places=6)
                    self.assertLess(a["max_residual"], 1e-7)
                else:
                    self.assertFalse(a["success"])
                values.append(a["rho"])
            self.assertTrue(all(a + 1e-7 >= b for a, b in zip(values, values[1:])))
            if np.isfinite(values[0]):
                self.assertLessEqual(values[0] - values[-1], 1.0 + 1e-7)

    def test_monotonicity(self):
        rng = np.random.default_rng(123)
        for _ in range(30):
            e, i = np.where(rng.random((6, 5)) < 0.65)
            q = rng.uniform(1, 10, len(e))
            m = Market(e, i, q, (e == 0).astype(float))
            vals = [m.threshold(d, target=0.95)["rho"] for d in [0, 0.1, 0.5, 1]]
            self.assertTrue(all(a + 1e-7 >= b for a, b in zip(vals, vals[1:])))
            for d in [0, 1]:
                fr = [m.recovery(r, d)["fraction"] for r in [0, 0.1, 0.5, 1]]
                self.assertTrue(all(a <= b + 1e-7 for a, b in zip(fr, fr[1:])))

    def test_withdrawal_bound(self):
        rng = np.random.default_rng(998)
        for _ in range(40):
            e, i = np.where(rng.random((6, 5)) < 0.7)
            q = rng.uniform(1, 10, len(e))
            m = Market(e, i, q, (e == 0).astype(float))
            r = m.threshold(1, target=0.95)
            if r["success"]:
                rho = r["rho"] + 1e-6
                w = m.min_withdrawal(rho, target=0.95)
                rec = m.recovery(rho, 0)
                self.assertGreaterEqual(
                    w + 1e-5, max(0, 0.95 * rec["lost"] - rec["recovered"])
                )

    def test_no_shock(self):
        m = Market(
            np.array([1, 2]), np.array([3, 3]), np.array([4.0, 5.0]), np.zeros(2)
        )
        self.assertAlmostEqual(m.threshold()["rho"], 0.0)


if __name__ == "__main__":
    unittest.main()
