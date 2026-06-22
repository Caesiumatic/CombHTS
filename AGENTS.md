PROJECT: High-throughput virtual screen ranking (monomer × solvent × electrolyte) triads
for electropolymerization. ~100 monomers × ~30 solvents × ~25 salts ≈ 50,000 triads.
Goal: rank triads by a weighted composite score under three hard constraints
(monomer Eox inside solvent window; electrolyte anion stable at that potential;
monomer soluble in solvent), plus predicted band gap.

ARCHITECTURE PRINCIPLES (do not violate):
1. COMPUTE PER-SPECIES, NOT PER-TRIAD. Expensive quantities depend on a single
   species in a given solvent dielectric, never on the full triad:
   - monomer props depend on (monomer, solvent)
   - solvent props depend on (solvent)
   - anion/cation props depend on (ion, solvent)
   Triad scoring is a cheap JOIN + arithmetic over precomputed per-species tables.
   Never loop over 50,000 triads calling an engine.
2. MOCK-FIRST. All quantum-chemistry runs go through an Engine interface.
   Build and test everything against a deterministic MockEngine first; real xtb/DFT
   backends plug in later without changing callers.
3. Library data (monomers/solvents/electrolytes/benchmark) lives in versioned CSVs.
   Thresholds and scoring weights live in YAML under configs/. Nothing hardcoded.
4. Every engine result is cached in SQLite keyed by
   (canonical_smiles, charge_state, method, solvent) for idempotent re-runs.
5. The redox-to-(V vs Ag/AgCl) conversion is one tested function; constants pinned.

STACK: Python 3.11+, RDKit, pandas, pydantic, pytest, SQLite (stdlib sqlite3),
PyYAML. (The xtb backend and a Gaussian DFT backend are now wired, mock-first;
stk is substituted by documented RDKit α-coupling, as stk is unavailable in the env.)
Use a src-layout package `eps`.
STYLE: type hints, docstrings with the physical meaning + units of every quantity,
small pure functions, pytest for every module. Units always explicit (V, eV, kcal/mol).

DOCUMENTATION MAINTENANCE:
At the end of every work unit: (1) overwrite STATUS.md to reflect the new current state
(phase, what works, placeholders, open debts, next action); (2) prepend a dated entry to
CHANGELOG.md describing what changed and why. STATUS.md is a mutable snapshot; CHANGELOG.md
is append-only history. Keep both concise.
THINK.md is the register of open scientific/decision questions (the why/what-if
layer). At the end of a work unit, if a genuine research question, tradeoff, or sign-off
need was opened, advanced, or resolved, update the relevant THINK.md entry (open ->
exploring -> decided/parked) and its Decision log. Keep engineering debt in STATUS.md;
THINK.md is only for items needing scientific judgment. Do not duplicate STATUS content.
RUN MANIFESTS: Whenever a run is executed or its results become known (from a cluster log,
qacct, or output inspection), create a manifest under docs/runs/ from docs/runs/TEMPLATE.md
and add a row to docs/runs/README.md. Manifests record the FACTS of a run (engine, scope,
job, status, headline numbers, output paths, provenance, caveats) because run artifacts live
in gitignored outputs/ and never enter the repo. ALWAYS state the engine explicitly (mock vs
real); never present a mock smoke as a scientific result.

VERSION CONTROL:
Creating or switching to a new branch still requires explicit user approval or mention.
After a major work unit is genuinely complete, proportionate verification has passed, and
STATUS.md / CHANGELOG.md / THINK.md / run manifests have been synchronized as applicable,
you are authorized to commit the completed work and push the current branch without asking
for additional approval. Do not commit or push partial, unverified, or stale-record work.
