import json
import numpy as np, pandas as pd
from analyze import clean, PRODUCTS, OUT
from model import Market


def main():
    df, _ = clean(2021)
    cuts = []
    fair = []
    for code, name in PRODUCTS.items():
        g = df[df.k == code].reset_index(drop=True)
        for shock, removed in [("Ukraine", [804]), ("Black Sea", [643, 804])]:
            m = Market.from_frame(g, removed)
            ex, im, ei, ii, E, D, b, active, cap, S, B, L = m.prepare()
            for delta, label in [(0, "frozen"), (1, "swaps")]:
                r = m.threshold(delta, target=0.95, uniform=True)
                fair.append(
                    {
                        "product": name,
                        "shock": shock,
                        "policy": label,
                        "rho_uniform95": r["rho"],
                    }
                )
                full = m.threshold(delta)
                if full["success"]:
                    chosen = im[full["demand_dual"] > 1e-7]
                    nei = np.unique(ei[active & np.isin(m.importers, chosen)])
                    need = (D if delta else L)[np.isin(im, chosen)].sum()
                    supply = cap[nei].sum()
                    bound = need / supply - int(delta)
                    cuts.append(
                        {
                            "product": name,
                            "shock": shock,
                            "policy": label,
                            "rho": full["rho"],
                            "cut_bound": bound,
                            "certificate_gap": abs(full["rho"] - bound),
                            "importers": list(map(int, chosen)),
                            "exporters": list(map(int, ex[nei])),
                            "need_mt": need / 1e6,
                            "supply_mt": supply / 1e6,
                        }
                    )
            missing_im = im[(L > 0) & ~np.isin(im, np.unique(m.importers[active]))]
            fair[-1]["no_alternative_importers"] = ",".join(map(str, missing_im))
            fair[-1]["no_alternative_loss_share"] = float(
                L[np.isin(im, missing_im)].sum() / L.sum()
            )
    pd.DataFrame(fair).to_csv(OUT / "uniform_targets.csv", index=False)
    (OUT / "cut_certificates.json").write_text(json.dumps(cuts, indent=2))
    print(
        "maximum certificate gap", max(x["certificate_gap"] for x in cuts), flush=True
    )


if __name__ == "__main__":
    main()
