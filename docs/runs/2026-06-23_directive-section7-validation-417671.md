# Run: 2026-06-23 — directive section-7 validation package (gfn2-xtb)

- run_id: `2026-06-23_directive-section7-validation-417671`
- date: 2026-06-23
- command: `qsub -v COMBHTS_ROOT=/home/shic4/CombHTS_section7_e023a1c,VALIDATE_HARVEST=/home/shic4/CombHTS/outputs/tier1_real_7488_salt_fixed/tier1_all.csv,VALIDATE_OUTDIR=/home/shic4/CombHTS_section7_e023a1c/outputs/directive_section7_validation,VALIDATE_CACHE=/home/shic4/CombHTS_section7_e023a1c/outputs/directive_section7_validation/cache.sqlite scripts/run_validate_directive.sge`
- engine / method: real `gfn2-xtb+conf-mmff94-n100`
- scope: directive section-7 validation package for the 36 x 13 x 16 salt-role-fixed real harvest
  (7,488 triads; 2,143 per-salt survivors), plus Eox benchmark profiles, solvent ESW benchmark
  rows, and polymerization-feasibility labels.
- cluster job: SGE 417671; `intel24@compute-3-16.local`; 4 slots; wall 398 s; exit 0; failed 0;
  maxvmem 172.801 MB.
- status: completed
- headline results: active production `agagcl_peak_strict` Eox LOO-CV MAE 0.186 V over 9 collapsed
  groups (PASS vs <0.30 V, but not below the 0.15 V reference floor); Tier-2 held-out validation
  OUT_OF_SCOPE; raw solvent ESW descriptor MAE failed (anodic 5.409 V, cathodic 3.755 V; n=6);
  production ESW gate safety passed with 0 unsafe widenings across 5,760 comparable measured rows;
  feasibility remained NOT_YET_TESTABLE with 12 matched labels, TP=5/FN=3/TN=2/FP=2, balanced
  accuracy 56.25% and 95% stratified-bootstrap interval 25.0-87.5%.
- per-property failures: none in the validation workflow. The scheduler log contains RDKit
  `UFFTYPER` warnings for selenium atom types, but the workflow completed and wrote all required
  artifacts.
- output artifacts (paths, NOT committed):
  `/home/shic4/CombHTS_section7_e023a1c/outputs/directive_section7_validation/validation_summary.json`,
  `validation_report.md`, `eox_profile_summary.csv`, `eox_points.csv`,
  `esw_descriptor_points.csv`, `esw_gate_diagnostics.csv`, `feasibility_matches.csv`,
  `provenance.json`, and `cache.sqlite`. SGE log:
  `/home/shic4/combhts_validate_directive.o417671`.
- provenance: git commit `e023a1c6bba0b60f22a6afb3a649f45308234122`, dirty false. Input hashes
  recorded in `provenance.json`; key hashes include harvest
  `26038208457a2855e4aaa123ed02c351aeeed53acd66dfe6c66dfa79aeb61253`,
  `configs/tier1.yaml` `abfb074087cd057cdfb24b2d0c38af7d537ff71b468d9af192334c6491bb9c45`,
  `configs/calibration_profiles.yaml` `009781e4813150e41fe791f37fe6b0ada2e2a2082a5764de76ef0fe993e47f14`,
  `data/benchmark.csv` `572ecd8e4339fcd1e7bb31834f90ee5b4f7bf3690550e3f53ad2044d9b2fa6fe`,
  `data/solvent_benchmark.csv` `1b14d8884e64c330a835abe8618cb3776be0e822fade6c03fedbe7edc2404957`,
  and `data/polymerizability_labels.csv`
  `cf2f2f788b8c683631372c1f02ec53edf2acca398e9eb282e936f3afa75979bb`.
- caveats: This closes the current section-7 reporting package, not the scientific gaps. Raw
  isolated-solvent descriptors are not practical ESW calibrations; exact formulation coverage is
  sparse; feasibility is underpowered; existing DFT results are in-sample, not held-out Tier-2
  validation. No scoring weights, thresholds, redox constants, optical policy, production CSVs, or
  417587 artifacts changed.
- supersedes / superseded_by: supersedes the prior section-7 pivot as a concrete machine-readable
  real validation package; superseded_by: —
