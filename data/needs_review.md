# needs_review — directive §2 species deferred from the live library

Species named in the directive's §2 lists that were **not** added to the live CSVs because either
the SMILES or (for monomers) the coupling site could not be assigned with confidence. Per the
project guardrail ("never fabricate a SMILES or a coupling site — flag uncertain ones instead"),
each is parked here with a one-line reason rather than guessed into `data/*.csv`. Resolve a row by
supplying a verified SMILES **and** an explicit coupling/building-block assignment, then move it to
the live CSV with a test.

## Monomers (directive §2.1)

| species | reason deferred |
| --- | --- |
| o-aminophenol | Electropolymerizes to a phenoxazine-type **ladder** polymer; the C–N / C–O / C–C coupling is not a single clean site. SMILES is clear (`Nc1ccccc1O`); the coupling is not. |
| 3,6-dimethylcarbazole | Concrete rep for "3,6-disubstituted carbazole", but the **standard 3,6 electrocoupling site is blocked** by the two methyls; the alternative (1,8- or N-) coupling is uncertain. SMILES clear; site is not. |
| diketopyrrolopyrrole (DPP) | Polymerized as a **thiophene-flanked, N,N′-dialkylated** unit (e.g. 3,6-di(thiophen-2-yl)-2,5-dialkyl-DPP), not the bare lactam core; the monomer SMILES and coupling site are undefined without specifying the flankers and N-substituents. |
| isoindigo | 6,6′-coupling is standard but requires N,N′-dialkylation and an explicit fused-ring building block; deferred pending an exact regiochemical assignment rather than a hand-guessed fused SMILES. |
| thiadiazoloquinoxaline | Tricyclic acceptor with several named isomers (e.g. [1,2,5]thiadiazolo[3,4-g]quinoxaline); both the exact SMILES and the coupling site are ambiguous without specifying donor flankers. |
| indacenodithiophene (IDT) | Ladder-type fused core that normally carries solubilizing aryl/alkyl groups; the bare-core SMILES and the outer-thiophene coupling need an explicit assignment. |
| acenaphtho-pyrrole hybrid | Name is vague in the directive; the structure itself is undefined. |

## Solvents (directive §2.2) — `special_handling`, excluded from the default screen

These are **not** simple molecular solvents, and the ALPB implicit-solvent model does not represent
them cleanly. None has a single neutral-molecule SMILES that would faithfully stand in for the
medium, so none was added to `data/solvents.csv` (which feeds the default screen).

| medium | reason deferred |
| --- | --- |
| [BMIM][PF6], [BMIM][BF4], [EMIM][TFSI] | Ionic liquids — salt-like (cation + anion), no single neutral-molecule SMILES; ALPB has no clean parameterization. Inventing one SMILES would misrepresent the medium. |
| choline chloride / urea (deep eutectic) | A two-component **mixture**, not a single molecular solvent; no single dielectric/SMILES applies. |
| BFEE (BF₃·OEt₂) | A Lewis-acid **complex**; not represented by a single molecular dielectric. |

## Salts (directive §2.3)

The current per-ion anion model handles small, discrete anions; the following are out of its scope.

| salt | reason deferred |
| --- | --- |
| NaPSS | Sodium poly(styrenesulfonate) — **polymeric** anion; the per-ion model does not handle polymers. |
| NaDBSA | Sodium dodecylbenzenesulfonate — large **surfactant** anion with a long alkyl tail; out of scope for the current anion model. |
