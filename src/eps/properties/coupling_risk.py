"""Directive §3.1/§5 (B2) — screening-grade SOFT coupling-site-availability flag.

Reported-only second-tier screen: it NEVER changes the Tier-1 survivor set or the composite score
(promoting it to a hard reject is a PI decision — `DECISIONS_PENDING.md` B1/B4). It encodes the ONE
intrinsic-NO mechanism the B1 diagnostic showed screening descriptors can actually separate —
**position-blocked coupling** — applied PER MONOMER CLASS (directive §5 point 2: a single signal is
not valid across classes):

- α-coupling monomers (5-membered heteroaromatics: thiophene/pyrrole/furan/selenophene/EDOT …):
  flag when fewer than ``min_free_alpha`` α C–H coupling sites remain. Default ``min_free_alpha=1``
  flags only the α,α′-DIBLOCKED case (e.g. 2,5-dimethylpyrrole, 0 free α). A monomer with one free α
  (e.g. 2-methylfuran, a YES) still couples, so it is NOT flagged.
- carbazole-scaffold monomers: flag when BOTH 3- and 6-positions (the standard electropolymerization
  coupling sites) are substituted (e.g. 3,6-di-tert-butyl-/3,6-diphenyl-carbazole). Parent and
  3-mono-substituted carbazoles (≥1 free 3/6 site) are NOT flagged.

What it deliberately does NOT catch (B1 screening-grade blind spots → need Tier-2 / explicit
kinetics, recorded as ``not_assessed``/``ok`` honestly, never faked):
- electronic deactivation (3-thiophenecarboxaldehyde: α free, planar dimer thermodynamically normal);
- β-substituent α-coupling steric block (3,4-dibutylthiophene: the planar α-dimer ignores the
  out-of-plane clash);
- radical-cation over-stabilization (1-aminopyrene); 3,3′-only dimerization (N-phenylcarbazole).

All thresholds come from config (AGENTS.md: nothing hardcoded). Pure structure (RDKit only; no engine,
no cache).
"""

from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import rdmolops

from eps.structures.oligomer import detect_alpha_carbons

# carbazole (9H-dibenzo[b,d]pyrrole) carbon/N skeleton; matches N- and 3,6-substituted variants.
_CARBAZOLE_CORE = Chem.MolFromSmarts("c1ccc2c(c1)[#7]c1ccccc12")


def _carbazole_3_6_carbons(mol: Chem.Mol) -> list[int] | None:
    """Indices of the two carbazole 3/6 carbons (aromatic C at graph distance 4 from the pyrrole N),
    or None if the molecule is not a carbazole scaffold."""

    if _CARBAZOLE_CORE is None or not mol.HasSubstructMatch(_CARBAZOLE_CORE):
        return None
    core = set(mol.GetSubstructMatch(_CARBAZOLE_CORE))  # restrict to the 13-atom carbazole core
    n_idx = next((i for i in core if mol.GetAtomWithIdx(i).GetAtomicNum() == 7), None)
    if n_idx is None:
        return None
    dist = rdmolops.GetDistanceMatrix(mol)
    # carbazole positions 3 and 6 = the two core aromatic carbons at graph distance 4 from the
    # pyrrole N. Restricting to the core excludes any N-aryl substituent's para carbon (also dist 4).
    pos = [
        i
        for i in core
        if mol.GetAtomWithIdx(i).GetIsAromatic()
        and mol.GetAtomWithIdx(i).GetAtomicNum() == 6
        and int(dist[i][n_idx]) == 4
    ]
    return pos if len(pos) == 2 else None


def _is_substituted_aromatic_carbon(mol: Chem.Mol, idx: int) -> bool:
    """True if the aromatic carbon bears no H (i.e. it carries a substituent → coupling-blocked).

    An unsubstituted carbazole 3/6 carbon is a C–H; any substituent (alkyl OR aryl) removes that H.
    """

    return mol.GetAtomWithIdx(idx).GetTotalNumHs() == 0


def coupling_risk_flag(
    smiles: str,
    coupling_mode: str | None,
    *,
    min_free_alpha: int = 1,
) -> dict[str, object]:
    """Per-class coupling-site-availability flag for one monomer (see module docstring).

    Returns a dict with ``coupling_risk`` in {``ok``, ``risk_alpha_blocked``, ``risk_3_6_blocked``,
    ``not_assessed``, ``unparseable``}, an integer ``n_free_alpha`` (−1 if N/A), and a human
    ``coupling_risk_detail``. ``risk_*`` means "predicted coupling-infeasible (position-blocked)";
    it is SOFT/reported and must not alter survivors or the composite.
    """

    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return {"coupling_risk": "unparseable", "n_free_alpha": -1,
                "coupling_risk_detail": f"RDKit could not parse {smiles!r}"}

    carbazole_3_6 = _carbazole_3_6_carbons(mol)
    if carbazole_3_6 is not None:
        blocked = [i for i in carbazole_3_6 if _is_substituted_aromatic_carbon(mol, i)]
        if len(blocked) == 2:
            return {"coupling_risk": "risk_3_6_blocked", "n_free_alpha": -1,
                    "coupling_risk_detail": "carbazole 3- and 6-coupling sites both substituted"}
        return {"coupling_risk": "ok", "n_free_alpha": -1,
                "coupling_risk_detail": f"carbazole; {2 - len(blocked)}/2 of 3,6 sites free"}

    if (coupling_mode or "").strip().lower() == "alpha":
        n_free = len(detect_alpha_carbons(mol))
        if n_free < min_free_alpha:
            return {"coupling_risk": "risk_alpha_blocked", "n_free_alpha": n_free,
                    "coupling_risk_detail": f"{n_free} free α C–H sites < min_free_alpha={min_free_alpha}"}
        return {"coupling_risk": "ok", "n_free_alpha": n_free,
                "coupling_risk_detail": f"{n_free} free α C–H coupling sites"}

    # explicit non-carbazole couplers (fluorene 2,7 / aniline / diphenylamine / fused D-A …):
    # screening-grade position-block detection is not class-defined here — disclose, do not fake.
    return {"coupling_risk": "not_assessed", "n_free_alpha": -1,
            "coupling_risk_detail": f"coupling_mode={coupling_mode!r}: not screening-assessable (B1 blind spot)"}
