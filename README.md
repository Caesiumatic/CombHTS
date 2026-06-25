# CombHTS

CombHTS ranks monomer x solvent x electrolyte triads for electropolymerization. The production
screen enforces three hard constraints - monomer oxidation inside the solvent window, anion
stability at that potential, and monomer-medium compatibility through a solvation-affinity proxy -
then ranks survivors with a weighted composite that includes diagnostic polymer-quality descriptors.

## Current Operating State

- Current library: **36 monomers x 13 solvents x 16 electrolytes = 7,488 triads**. This is the
  current validated iteration scale, not the eventual directive target and not a failed run.
- A real Tier-1 ranking exists for this library; mock mode is only a deterministic plumbing smoke.
- Directive Section-7 validation exists through `eps validate-directive`.
- Tier-2 is scaffold/pilot status. No real Tier-2 scientific values are promoted.
- Diagnostic and staging results are not production truth.
- Production Tier-1 calibration currently uses `agagcl_peak_strict`; default `eps validate` uses
  `agagcl_peak_relaxed`. This divergence is explicitly declared in
  `configs/calibration_operational.yaml`. The manifest and this README do not change scientific
  policy or coefficients.

## Quickstart

```bash
python -m pip install -e ".[dev]"
python -m eps.cli doctor
```

Safe local commands:

```bash
python -m eps.cli doctor
python -m eps.cli run-tier1 --engine mock --cache /tmp/combhts_mock_tier1.sqlite --output /tmp/combhts_tier1_ranked.csv --all-output /tmp/combhts_tier1_all.csv
python -m eps.cli validate --engine mock --cache /tmp/combhts_validation.sqlite --report /tmp/combhts_validation_report.csv
python -m pytest -q
```

Mock outputs are nonphysical. Real chemistry calculations must run through the project scheduler
templates, not on a login/head node. Do not put credentials, host passwords, raw caches, or heavy
cluster outputs in the repository.

## Classification

| Class | Meaning | Examples |
| --- | --- | --- |
| Production | Current screening truth consumed by ranking or validation gates. | Production CSVs in `data/`, `configs/tier1.yaml`, `configs/scoring.yaml`, real Tier-1 ranking. |
| Diagnostic | Evidence and descriptors useful for interpretation but not production truth. | Optical/soft-axis pilots, ESW descriptor accuracy, feasibility diagnostics. |
| Staging/review-only | Curated evidence awaiting human/source review before any production ingest. | `data/lit_curation/`, `docs/research/` review tables. |
| Mock/nonphysical | Deterministic plumbing checks only. | `--engine mock` Tier-1, validation, and Tier-2 smoke outputs. |

## Truth Map

| File | Role |
| --- | --- |
| `docs/current_state.md` | Concise current operating snapshot. |
| `STATUS.md` | Mutable project status history and immediate debts. |
| `THINK.md` | Open scientific decisions and decision logs. |
| `CHANGELOG.md` | Append-only change history. |
| `docs/code_structure.md` | Maintainer map for code, workflows, data/config ownership, and no-touch areas. |
| `docs/runs/README.md` | Index of durable run facts for gitignored output artifacts. |
| `docs/output_contracts.md` | Public output-schema and data-dictionary contract. |

References: Jackson Lab at UIUC, [https://thejacksonlab.github.io/](https://thejacksonlab.github.io/).
