# Run: 2026-11-13 — recorded screening figure (none)

- run_id: `2026-11-13_readme-screening-figure`
- date: 2026-11-13
- command: `MPLCONFIGDIR=/private/tmp/readme-figures-mpl .venv/bin/python scripts/plot_readme_screening.py --rebuild-from outputs/tier1_real_7488_capped_esw/tier1_all.csv --preview /private/tmp/public-repo-wording-20261113/combhts-screening-preview.png`
- engine / method: none; deterministic aggregation and Matplotlib rendering of a recorded real-GFN2-xTB screen
- scope: the complete 7,488-row capped-ESW harvest from run 417562, with the salt-role exclusions recorded by run 417569
- cluster job: local; no cluster access or engine invocation
- status: completed
- headline results: 2,143 retained triads; 1,127 exact score classes; class multiplicities 373 singletons, 492 pairs, 262 triples. All 30 exported Pareto rows match run 417571 in identity, order, representative salt, tied members, and score to the recorded six decimals.
- per-property failures: inherited source statuses; no property recomputation
- source artifact (not committed): `outputs/tier1_real_7488_capped_esw/tier1_all.csv`, SHA-256 `c4eee9ce3b77264b5370e1b2421fbbfd50962259e81e0c450fcb9e38c41d4076`
- documentation outputs: `docs/figures/screening_snapshot_20260622.svg` and its aggregate/provenance JSON; raw harvest and PNG preview remain outside version control
- provenance: base commit `c700f6e3f6ea184a0aaf93f7a328788cc6613eee`; original engine and replay lineage are linked in the JSON. The exact salt-fixed CSV is absent locally, so the recorded role exclusions are applied to the preserved complete parent harvest. Composite values and Pareto flags are retained.
- interpretation: per-salt counts and distinct score-class distributions describe the June 22 computational screen. Whiskers are min–max and boxes are interquartile ranges, not confidence intervals. The composite includes uncalibrated optical, dimerization, and solvation-affinity axes; later IPEA/calibration snapshots are separate.
- supersedes / superseded_by: —; visualizes existing records without replacing them
