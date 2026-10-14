from pathlib import Path
import json, time, sys
import numpy as np, pandas as pd
from model import Market

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)
PRODUCTS = {
    "100199": "Wheat",
    "100590": "Maize",
    "100390": "Barley",
    "120190": "Soybeans",
    "151211": "Sunflower oil",
    "310210": "Urea",
}


def clean(year):
    df = pd.read_csv(DATA / f"baci_selected_{year}.csv", dtype={"k": str})
    df["q"] = pd.to_numeric(df.q, errors="coerce")
    df["v"] = pd.to_numeric(df.v, errors="coerce")
    audit = {
        "year": year,
        "raw_rows": len(df),
        "missing_quantity": int(df.q.isna().sum()),
        "nonpositive_quantity": int((df.q <= 0).sum()),
        "self_flows": int((df.i == df.j).sum()),
        "duplicate_rows": int(df.duplicated(["i", "j", "k"]).sum()),
        "missing_q_value_share": float(df.loc[df.q.isna(), "v"].sum() / df.v.sum()),
    }
    df = df[(df.q > 0) & (df.v > 0) & (df.i != df.j)].copy()
    return df, audit


def run(year):
    df, audit = clean(year)
    rows = []
    coverage = []
    for code, name in PRODUCTS.items():
        g = df[df.k == code].reset_index(drop=True)
        coverage.append(
            {
                "year": year,
                "code": code,
                "product": name,
                "edges": len(g),
                "exporters": g.i.nunique(),
                "importers": g.j.nunique(),
                "quantity_mt": g.q.sum() / 1e6,
                "value_billion_usd": g.v.sum() / 1e6,
            }
        )
        for shock, removed in [("Ukraine", [804]), ("Black Sea", [643, 804])]:
            m = Market.from_frame(g, removed)
            L = m.q[m.shock > 0].sum()
            E = m.q.sum() - L
            if L <= 0:
                continue
            row = {
                "year": year,
                "code": code,
                "product": name,
                "shock": shock,
                "lost_mt": L / 1e6,
                "lost_share": L / m.q.sum(),
                "rho_aggregate95": 0.95 * L / E,
                "rho_aggregate100": L / E,
            }
            for target in [0.95, 1.0]:
                for delta, label in [(0, "frozen"), (1, "swaps")]:
                    r = m.threshold(delta, target=target)
                    key = f"{label}{round(100*target)}"
                    row["rho_" + key] = r["rho"]
                    row["residual_" + key] = r.get("max_residual", np.nan)
                    row["gap_" + key] = r.get("objective_gap", np.nan)
                    row["stationarity_" + key] = r.get("stationarity", np.nan)
            for rho in [0.05, 0.1, 0.2, 0.3, 0.5]:
                for delta, label in [(0, "frozen"), (1, "swaps")]:
                    row[f"recovery_{label}_{rho}"] = m.recovery(rho, delta)["fraction"]
            rows.append(row)
            print(
                year,
                name,
                shock,
                "95%",
                round(row["rho_frozen95"], 4),
                round(row["rho_swaps95"], 4),
                "full",
                row["rho_frozen100"],
                row["rho_swaps100"],
                flush=True,
            )
    pd.DataFrame(rows).to_csv(OUT / f"panel_{year}.csv", index=False)
    pd.DataFrame(coverage).to_csv(OUT / f"coverage_{year}.csv", index=False)
    (OUT / f"audit_{year}.json").write_text(json.dumps(audit, indent=2))


if __name__ == "__main__":
    years = list(map(int, sys.argv[1:])) or [2021]
    for year in years:
        run(year)
