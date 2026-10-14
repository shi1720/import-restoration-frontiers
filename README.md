# Import-Preserving Restoration Frontiers

Reproducible research code for **Protecting Importers or Protecting Routes? Export Expansion and Reallocation in Food and Fertilizer Trade**, prepared for Shivam Gupta.

The code computes the additional exporter availability required to restore disrupted imports while protecting every importer's surviving total. It contrasts that constraint with protection of every surviving bilateral route and measures how many incumbent shipments must be reassigned. This is a conditional trade-accounting stress test, not an estimate of spare production capacity, a causal war-impact model, or a welfare analysis.

## Main benchmark

Using the 2021 CEPII BACI network, removing Ukraine, and restoring 95% of aggregate lost soybean tonnage requires approximately 14.25% common exporter growth with route protection and 0.70% with importer protection. Wheat and maize show almost no analogous wedge. The soybean result survives the persistent-material screen and a fivefold route ceiling, while a twofold ceiling makes the target infeasible under both policies. In the 2023–2024 soybean snapshots, the Ukraine-removal protection wedge is below 0.01 percentage points. These qualifications are part of the result.

## Reproduce

Python 3.9.6 was used for the recorded run. The pinned dependencies target Python 3.9–3.12; the recorded run was tested on 3.9.6.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python reproduce.py --verify
```

This verifies the included data hashes, runs the tests, recomputes all eight annual panels, uniform-target and cut diagnostics, robustness specifications, shipment ledgers, figures, and LaTeX tables. No API key or proprietary data is needed. The selected data are already included; a fresh full source retrieval is optional:

```bash
python src/fetch_baci.py
```

The downloader retrieves selected members of the official ZIP with HTTP ranges, validates each member's CRC32, and filters the six research product codes. It transfers approximately 795 MB to recover the annual source members, retaining only about 3 MB of selected data and metadata. It uses up to 24 simultaneous range requests. The archived uncompressed-member and selected-file SHA-256 hashes are in `data/source_manifest.json`. If the source archive changes, investigate the revision before comparing results.

The manuscript source and PDF are included. To compile it, install Tectonic from its official distribution and run:

```bash
python reproduce.py --verify --paper
```

The paper was submitted to ISoT 2027 through CEPR HUB on 14 October 2026; the portal confirmed the application complete. Acceptance is pending. The repository contains the submitted manuscript, source, code, selected data, and numerical/visual results. Private account and submission-receipt materials are excluded.

## Layout

- `src/model.py`: expansion threshold, maximum recovery, and minimum withdrawal LPs.
- `src/test_model.py`: 150 small random networks checked by exhaustive subset enumeration at five release levels; structural and withdrawal-bound tests.
- `src/analyze.py`: eight-year quantity panels and cleaning ledgers.
- `src/robustness.py`: support, route ceiling, value unit, coordination budget, and 2022 descriptive exercises.
- `src/diagnostics.py`: uniform-country targets and reconstructed full-restoration cut witnesses.
- `src/case_study.py`: unconstrained and fivefold-ceiling soybean shipment ledgers.
- `src/figures.py`, `src/tables.py`: figures and paper-ready tables generated from result files.
- `results/`: complete machine-readable outputs, including infeasible specifications.
- `docs/literature_audit.txt`: closest work and the deliberately narrow novelty claim.
- `docs/crossref_verified.json`: verified bibliographic metadata.

## Definitions that matter

The main 95% target is **aggregate lost quantity**, not 95% recovery for every country. All importers retain at least the quantity that survived the declared original shock. The stricter uniform-country target is reported separately and can be infeasible. Infinity is retained; constraints are not automatically relaxed.

Exporter growth is relative to its baseline gross exports. No domestic-production, re-export material balance, price, timing, contractual, or nutritional claim follows. The six products are optimized separately. The joint Russia–Ukraine removal is hypothetical and is not a description of actual 2022 trade or sanctions. The support screens and bilateral ceilings are explicit scenarios, not estimated engineering constraints.

## Attribution and licensing

Data: CEPII BACI HS17, release 202601, retrieved 14 October 2026; underlying source UN Comtrade. The data and metadata remain under the **Etalab Open Licence 2.0**, not the code's MIT licence. See `DATA_LICENSE.md`.

Gaulier, G. and Zignago, S. (2010). *BACI: International Trade Database at the Product-Level. The 1994–2007 Version*. CEPII Working Paper 2010-23.

The model specializes established transportation/max-flow mathematics. It does not claim a new max-flow theorem, the discovery of shared supplier capacity, or guaranteed novelty or patentability. See the literature audit for close overlaps with Erokhin (2026) and Gupta et al. (2026).
