import json
import pandas as pd
from analyze import clean, OUT
from model import Market


def main():
    b, _ = clean(2021)
    g0 = b[b.k == "120190"].copy().reset_index(drop=True)
    summary = []
    for factor in [None, 5]:
        g = g0.copy()
        if factor:
            g["route_cap"] = factor * g.q
        m = Market.from_frame(g, [804])
        r = m.threshold(1, target=0.95)
        p = m.min_withdrawal(r["rho"] + 1e-7, target=0.95, return_flow=True)
        g["restored_q"] = p["flow"]
        g["surviving_q"] = g.q * (g.i != 804)
        g["change"] = g.restored_q - g.surviving_q
        g.to_csv(OUT / f'soybeans_plan_cap{factor or "none"}.csv', index=False)
        summary.append(
            {
                "route_cap_factor": factor,
                "rho95": r["rho"],
                "rho_margin": 1e-7,
                "withdrawal_tonnes": p["withdrawal"],
            }
        )
    (OUT / "soybeans_case.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
