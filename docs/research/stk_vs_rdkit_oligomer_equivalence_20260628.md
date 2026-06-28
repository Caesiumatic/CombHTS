# Oligomer assembly: RDKit (ours) ≡ stk — proof of equivalence

**Date:** 2026-06-28
**Question:** Directive §4.1 names `stk` for oligomer assembly; we use a pure-RDKit assembler
(`src/eps/structures/oligomer.py`). Is keeping RDKit a real scientific deviation, or only a
tool-identity one? **Verdict: tool-identity only — the assembled molecule is byte-identical.**

## 1. The "stk not installable" premise was false

The prior justification ("stk is not available/installable in this env") is **wrong** and is
retired. `stk 2026.1.4.0` resolves cleanly under this project's constraints:

```
pip install --dry-run "numpy<2" rdkit stk
# → Would install ... numpy-1.26.4 rdkit-2026.3.3 stk-2026.1.4.0 ...
```

The resolver picks `numpy-1.26.4` (satisfies `numpy<2`) alongside `rdkit-2026.3.3`. So
installability is **not** the reason we don't use stk.

## 2. Why we still don't adopt it

1. **Zero scientific gain.** stk wraps RDKit internally; the linear n-mer it constructs is the
   same molecular graph ours builds, and graphs canonicalize to the same SMILES (§3 below). The
   3D geometry that actually enters the physics is regenerated downstream from that SMILES by
   ETKDG/MMFF94 + GFN2-xTB (`oligomer.py:190` → `smiles_to_xyz(oligomer_smiles(...))`), so the
   assembler only ever supplies connectivity — and the connectivity is identical.
2. **Heavy dependency cost.** Adopting stk pulls ~15 transitive deps into a CV-screening repo,
   including a **MongoDB client** (`pymongo` via `atomlite`), `polars`, `pathos`, `multiprocess`,
   `seaborn`, `dnspython`, `MCHammer`, `SpinDry`, `vabene`, … — a maintainability/anti-bloat cost
   for no numeric change.

The directive's **method** — defined-regiochemistry linear oligomer assembly with human-reviewable
coupling sites — is fully satisfied by `oligomer.py` (data-driven `[1*]/[2*]` ditopic building
blocks in `data/polymerization.csv`). The `[1*]`/`[2*]` dummies play exactly the role of stk's
functional-group "deleter" atoms: mark the bond, then disappear on coupling.

## 3. Proof: byte-identical canonical SMILES

Built thiophene di-/hexamer both ways and compared canonical SMILES (the unique normal form for
connectivity; if two builders make the same molecule, these strings are byte-equal).

**Ours** (`eps.structures.oligomer.oligomer_smiles`, thiophene building block `[1*]c1ccc([2*])s1`):

```
n=2: c1csc(-c2cccs2)c1
n=6: c1csc(-c2ccc(-c3ccc(-c4ccc(-c5ccc(-c6cccs6)s5)s4)s3)s2)c1
```

**stk** (`stk.polymer.Linear`, 2,5-dibromothiophene `Brc1ccc(Br)s1` + `BromoFactory`, terminal
Br stripped to H to match our cap):

```
n=2: c1csc(-c2cccs2)c1
n=6: c1csc(-c2ccc(-c3ccc(-c4ccc(-c5ccc(-c6cccs6)s5)s4)s3)s2)c1
```

`diff` → identical. α,α′-linked sexithiophene, H-capped, both ways.

## 4. Reproduce

Ours (project `.venv`, has rdkit):
```bash
PYTHONPATH=src .venv/bin/python -c "
from rdkit import Chem
from eps.structures.oligomer import load_polymerization_specs, oligomer_smiles
s = load_polymerization_specs()['thiophene']
for n in (2,6):
    print(n, Chem.MolToSmiles(Chem.MolFromSmiles(oligomer_smiles('c1ccsc1', s, n))))
"
```

stk (throwaway venv, `pip install 'numpy<2' rdkit stk`):
```python
import stk
from rdkit import Chem
bb = stk.BuildingBlock('Brc1ccc(Br)s1', [stk.BromoFactory()])
for n in (2, 6):
    poly = stk.ConstructedMolecule(stk.polymer.Linear((bb,), 'A', n))
    rw = Chem.RWMol(Chem.RemoveHs(poly.to_rdkit_mol()))
    br = [a.GetIdx() for a in rw.GetAtoms() if a.GetAtomicNum() == 35]
    for b in br:
        for nb in rw.GetAtomWithIdx(b).GetNeighbors():
            nb.SetNoImplicit(False)          # let sanitize refill H on the freed carbon
    for idx in sorted(br, reverse=True):
        rw.RemoveAtom(idx)
    m = rw.GetMol(); Chem.SanitizeMol(m)
    print(n, Chem.MolToSmiles(Chem.MolFromSmiles(Chem.MolToSmiles(m))))
```

## 5. Decision

Keep the RDKit assembler; record this as a **PI-accepted, tool-identity-only deviation** from
§4.1. The false "not installable" justification is corrected in `oligomer.py`, the §4.1 compliance
audit, and `docs/step1_real_bandgap_dimerization_report.md`. No code or numbers change.
