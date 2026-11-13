# Electropolymerization screening: project map

The project progresses from reusable species calculations to calibration,
full-space collection, and property-surrogate modeling. `electropoly-jointopt-hts`
is the entry point for the implemented screening method and its recorded pilot results.

## Local workspaces

Directory names below refer to sibling checkouts under the same local workspace.
Each retains its own source history, input registries, and run definitions.

| Directory | Role | Entry point |
| --- | --- | --- |
| `electropoly-jointopt-hts` | Descriptor reuse, screening, calibration, and ranking | `src/eps/`, `README.md` |
| `JOHTVS` | Subsequent workflow and orchestration implementation | `src/johtvs/`, `orchestration/` |
| `20260707` | Tier-1/Tier-2 calibration and experimental-validation workspace | `calibration/`, `validation/`, `docs/` |
| `jhtvs` | Extracted full-space source, collection/QC, and apply-only calibration model | `fullspace/src/`, `models/active/` |
| `jhtvs_fullspace` | Historical full-space execution workspace and records | Its run-specific documentation |
| `jhtvs_ft0806` | Solvent-conditioned property-surrogate implementation | `spec/`, package CLI |

The later full-space implementation has a concise overview in `jhtvs/README.md`.
It is the source entry point for that stage. Historical execution workspaces
remain available for tracing their results.

## How the methods connect

1. **Descriptor computation:** molecular and solvent-conditioned calculations
   supply redox, optical, and solvation quantities.
2. **Calibration:** property-specific models map lower-cost estimates to the
   chosen references. Model revisions retain the fitting provenance.
3. **Full-space evaluation:** preparation and collection generate descriptors
   under one run's identities, geometry choices, and QC rules.
4. **Candidate selection:** compatibility filters and ranking operate on a
   defined descriptor table and configuration.
5. **Surrogate work:** the solvent-conditioned model implementation is reviewed
   separately from the completed screening and calibration records.

## Module boundaries

The full-space source lives in `jhtvs`, separately from the older `eps` package. Their schemas,
calibration revisions, and geometry contracts differ, so importing files into
one namespace would require an explicit schema migration.

The June triad ranking, later calibration studies, and full-space results keep
separate result tables. A figure or metric should identify its input library,
model revision, and run record. In particular, the June top-30 export belongs to
the 7,488-triad screen.

## Next consolidation boundary

A future source merge can move the extracted full-space module together with
its input registries, tests, and apply-only model provenance. The prerequisite
is an agreed package interface between descriptor collection and scoring.
Calibration fitting histories and generated calculation outputs remain in their
respective research workspaces.
