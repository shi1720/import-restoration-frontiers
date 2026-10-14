from pathlib import Path
import json
import numpy as np, pandas as pd
from model import Market
from analyze import clean, PRODUCTS, ROOT, OUT


def support_frame(base, hist, kind):
    if kind == "all_current":
        return base.copy()
    keys = ["i", "j", "k"]
    if kind == "union3":
        extra = (
            hist[keys]
            .drop_duplicates()
            .merge(base[keys], how="left", on=keys, indicator=True)
        )
        extra = extra[extra._merge == "left_only"][keys]
        extra["q"] = 0.0
        extra["v"] = 0.0
        extra["t"] = 2021
        return pd.concat([base, extra], ignore_index=True)
    counts = hist[hist.v >= 100].groupby(keys).t.nunique()
    elig = set(counts[counts >= 2].index)
    g = base.copy()
    g["route_cap"] = [
        np.inf if (r.i, r.j, r.k) in elig else r.q for r in g.itertuples()
    ]
    return g


def run():
    base, _ = clean(2021)
    hist = pd.concat([clean(y)[0] for y in [2019, 2020, 2021]])
    rows = []
    curves = []
    blueprints = []
    for code, name in PRODUCTS.items():
        original = base[base.k == code].reset_index(drop=True)
        for spec in [
            "all_current",
            "union3",
            "persistent_material",
            "cap2",
            "cap5",
            "cap10",
            "value_units",
        ]:
            if spec.startswith("cap"):
                g = original.copy()
                g["route_cap"] = g.q * int(spec[3:])
            elif spec == "value_units":
                g = original.copy()
                g["q"] = g.v
            else:
                g = support_frame(original, hist[hist.k == code], spec)
            for shock, removed in [("Ukraine", [804]), ("Black Sea", [643, 804])]:
                m = Market.from_frame(g, removed)
                for delta, label in [(0, "frozen"), (1, "swaps")]:
                    r = m.threshold(delta, target=0.95)
                    rows.append(
                        {
                            "product": name,
                            "code": code,
                            "spec": spec,
                            "shock": shock,
                            "policy": label,
                            "rho95": r["rho"],
                            "residual": r.get("max_residual", np.nan),
                            "duality_gap": r.get("objective_gap", np.nan),
                        }
                    )
            print(name, spec, flush=True)
        m = Market.from_frame(original, [804])
        full = m.threshold(1, target=0.95)["rho"]
        frozen = m.threshold(0, target=0.95)["rho"]
        if np.isfinite(full):
            for delta in [0, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0]:
                r = m.threshold(delta, target=0.95)
                curves.append(
                    {
                        "product": name,
                        "kind": "per_route_release",
                        "parameter": delta,
                        "rho95": r["rho"],
                    }
                )
            for budget in [0, 0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 1.0]:
                r = m.threshold(1, budget=budget, target=0.95)
                curves.append(
                    {
                        "product": name,
                        "kind": "total_withdrawal_budget",
                        "parameter": budget,
                        "rho95": r["rho"],
                    }
                )
            r = m.min_withdrawal(full + 1e-7, target=0.95, return_flow=True)
            if isinstance(r, dict):
                y = r["flow"]
                out = original.copy()
                out["restored_q"] = y
                out["baseline_surviving"] = out.q * (out.i != 804)
                out["change"] = y - out.baseline_surviving
                out.to_csv(OUT / f"plan_2021_{code}.csv", index=False)
                blueprints.append(
                    {
                        "product": name,
                        "rho95": full,
                        "withdrawal_mt": r["withdrawal"] / 1e6,
                        "withdrawal_share_surviving": r["withdrawal"]
                        / m.q[m.shock == 0].sum(),
                    }
                )
    pd.DataFrame(rows).to_csv(OUT / "robustness.csv", index=False)
    pd.DataFrame(curves).to_csv(OUT / "coordination_frontiers.csv", index=False)
    pd.DataFrame(blueprints).to_csv(OUT / "minimum_withdrawals.csv", index=False)
    # Out-of-period description, not causal validation: quantity-weighted new-route reliance.
    future, _ = clean(2022)
    desc = []
    for code, name in PRODUCTS.items():
        b = base[base.k == code]
        f = future[future.k == code]
        pairs = set(zip(b.i, b.j))
        old = set(zip(hist[hist.k == code].i, hist[hist.k == code].j))
        new2021 = np.array([(i, j) not in pairs for i, j in zip(f.i, f.j)])
        new3 = np.array([(i, j) not in old for i, j in zip(f.i, f.j)])
        ba = b.groupby("j").q.sum()
        fa = f.groupby("j").q.sum()
        bua = b[b.i == 804].groupby("j").q.sum()
        fua = f[f.i == 804].groupby("j").q.sum()
        reduced = np.maximum(bua - fua.reindex(bua.index, fill_value=0), 0)
        total_reduced = reduced.sum()
        BN = b[b.i != 804].groupby("j").q.sum()
        FN = f[f.i != 804].groupby("j").q.sum()
        increases = np.maximum(
            FN.reindex(reduced.index, fill_value=0)
            - BN.reindex(reduced.index, fill_value=0),
            0,
        )
        paired = np.minimum(increases, reduced).sum()
        desc.append(
            {
                "product": name,
                "new_route_share_2022": f.loc[new2021, "q"].sum() / f.q.sum(),
                "new_3yr_route_share_2022": f.loc[new3, "q"].sum() / f.q.sum(),
                "Ukraine_exports_2021_mt": b[b.i == 804].q.sum() / 1e6,
                "Ukraine_exports_2022_mt": f[f.i == 804].q.sum() / 1e6,
                "positive_destination_Ukraine_loss_mt": total_reduced / 1e6,
                "matched_nonUkraine_increase_mt": paired / 1e6,
                "matched_increase_fraction": (
                    paired / total_reduced if total_reduced else np.nan
                ),
            }
        )
    pd.DataFrame(desc).to_csv(OUT / "historical_2022.csv", index=False)


if __name__ == "__main__":
    run()
