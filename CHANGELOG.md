# Changelog

## 2026-06-16
- Recorded the first real cluster xTB validation milestone: SCS Lop/Grid Engine environment confirmed, `xtb/6.4.1` with `--json` and `--alpb <name>` verified on a compute node, `eps run-tier1 --engine mock` completed on the cluster, and `eps validate --engine xtb` completed with MAE 5.398 V before calibration and 0.145 V after in-sample calibration.
- Updated the living project status to make benchmark curation and queue-safe real xTB Tier-1 execution the next priorities.

## 2026-06-15
Back-filled on 2026-06-15 from session history; exact per-milestone dates not recorded.

- M7 — xTB solvent fix + robust JSON parsing: --alpb takes solvent NAMES (removed the invalid numeric-dielectric path); filled xtb_gbsa_name for all solvents incl. nitromethane + 4 nearest-dielectric ALPB proxies; switched energy/gap parsing to xtbout.json with last-match regex fallback; added xtbout.json fixture.
- M6 — Real GFN2-xTB engine: XTBEngine via subprocess (RDKit ETKDG->xyz, adiabatic IP/EA with q/multiplicity rule, solvated redox, GBSA/ALPB solvation), fixture-tested + skipif live test; added structures/geometry.py and xtb_gbsa_name column; CLI --engine {mock,xtb}.
- M5 — Corrected solvent anodic limits: previous derivation reused a stale column and corrupted 6 solvents; replaced with cathodic + spec ESW width (CombHTS table 2.2), all flagged TODO for measured values.
- M4 — Calibration + validation harness: benchmark.csv (seed CV Eox), linear xTB->reference calibration, validation runner reporting MAE before/after vs targets in validation.yaml; `eps validate`.
- M3 — Data/reference fixes: solvent ESW semantics corrected (anodic limit vs width), added potential_reference column + loader warning, water eps_r 80.1, rdkit-pypi -> rdkit.
- M2 — Tier-1 driver + SQLite cache + composite scoring + Pareto + end-to-end mock smoke test (`eps run-tier1`).
- M1 — Engine interface + deterministic MockEngine + pinned redox conversion.
- M0 — Project brief (AGENTS.md), repo scaffold, chemical-space data layer (monomers/solvents/electrolytes CSVs, pydantic models, RDKit-validating loaders).
