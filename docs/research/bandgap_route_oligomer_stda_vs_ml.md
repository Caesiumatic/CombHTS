# Predicting the Optical/Band Gap of Conjugated Polymers: Oligomer + sTDA-xTB vs. ML/GNN — A Decision-Support Synthesis

**TL;DR**
- For a screening-grade band-gap descriptor across thiophenes, EDOT/ProDOT, pyrroles, furans, selenophenes, anilines, carbazoles, fluorenes, fused-ring (CPDT) and donor–acceptor (D–A) monomers, **Route A (oligomer + sTDA-xTB, calibrated to TD-DFT) is the recommended primary method now**: it is physics-based, applies uniformly to any monomer you can draw, predicts the *optical* gap you actually want, and has direct peer-reviewed precedent for exactly this task (the Zwijnenburg group screened thousands of conjugated co-polymers with calibrated xTB).
- **Route B (ML/GNN) is not yet stand-alone-ready** for this chemistry: the large public polymer datasets (PolyInfo, Khazana/Polymer Genome) are dominated by commodity/dielectric polymers, public DFT band-gap labels number only ~3,000–4,000 chain values, the models predict the *fundamental* (not optical) gap, and reported errors are RMSE ≈ 0.45 eV — too coarse and out-of-domain for low-band-gap D–A systems. The one conjugated-specific dataset (3,120 D–A polymers, Haciefendioglu & Yildirim 2025) shows feasibility but is a single study with no released turnkey predictor.
- **Recommended staging: Do A now, build B later.** Use calibrated sTDA-xTB to both score candidates AND generate a self-consistent, in-domain labeled dataset; once you accumulate ~5,000–20,000 calibrated gaps spanning your monomer classes, train/fine-tune a GNN as a fast surrogate to feed downstream generative design.

---

## Key Findings

1. **sTDA-xTB intrinsic accuracy is ~0.27–0.5 eV vs. high-level reference** — adequate for *ranking*, not absolute quantitative prediction. The original Grimme & Bannwarth method reports MAE 0.27 eV against SCS-CC2 vertical excitations.
2. **Calibration is the decisive step.** Linear calibration of xTB to (TD)DFT collapses optical-gap error from ~0.18–0.72 eV (raw) to **0.08–0.15 eV** (Zwijnenburg group), making it screening-grade.
3. **The biggest physics risks for your chemistry are charge-transfer states (D–A systems) and sulfur heterocycles (thiophene/EDOT/CPDT)** — both documented, both mitigable with range-separated-functional calibration and per-class validation.
4. **No turnkey public ML model fits this use case.** polyBERT/polyGNN/Polymer Genome/TransPolymer all predict the DFT *fundamental/chain* gap on commodity-skewed data; they extrapolate poorly to electropolymerizable conjugated monomers.
5. **Data availability is the binding constraint for Route B** — and Route A is the cheapest way to manufacture the in-domain labeled dataset Route B needs.

---

## PART A — Oligomer + sTDA-xTB (and TD-DFT) accuracy

### A.1 Intrinsic accuracy of sTDA-xTB and TD-DFT for optical gaps

**sTDA-xTB (Grimme & Bannwarth, *J. Chem. Phys.* 2016, 145, 054103, DOI 10.1063/1.4959605)** is a tight-binding-accelerated version of the simplified Tamm-Dancoff approximation (sTDA), first introduced by Grimme (*J. Chem. Phys.* 2013, 138, 244104, DOI 10.1063/1.4811331). Quantitative accuracy from primary literature:

- The original method reproduces **SCS-CC2/aug-cc-pVXZ vertical singlet–singlet excitation energies with a MAE of 0.27 eV** (compared to TD-PBE 0.67 eV and TD-PBE0 0.31 eV), for molecules of 500–1000 atoms in a few minutes of CPU time (Grimme & Bannwarth 2016). The widely quoted "0.3–0.5 eV average error" describes performance over broader, more heterogeneous benchmark sets.
- A follow-up calibration study (Adamson et al., "Machine learned calibrations to high-throughput molecular excited state calculations," *J. Chem. Phys.* 2022, 156, 134116, DOI 10.1063/5.0084535) reports raw **xTB-sTDA MAE of 0.38 eV vs. TD-DFT** on its external test sets, and notes Grimme & Bannwarth's original **0.34–0.48 eV MAE** vs. coupled-cluster/TD-DFT depending on structural complexity. A trained nonlinear calibration cut this to **0.14 eV**.
- The underlying sTDA approximation with a good hybrid functional gives **MAE 0.2–0.3 eV** vs. reference for standard singlet–singlet benchmark sets (Grimme 2013).

**Key interpretive point:** these errors are versus *higher-level theory* and are *vertical* excitations, not direct comparisons to experimental optical gaps. sTDA-xTB is explicitly positioned by its developers and practitioners as a **screening/ranking tool, not a quantitative predictor**. The 747-molecule TADF benchmark (Tomas et al., arXiv:2511.00922; *J. Chem. Inf. Model.* 2025, DOI 10.1021/acs.jcim.5c02978) attributes its residual ~0.17 eV experimental MAE partly to the vertical approximation and stresses the methods' "role in screening rather than quantitative prediction."

**TD-DFT reference accuracy:** For "well-behaved" valence states of conjugated chromophores, global hybrids (B3LYP, PBE0) give vertical-excitation MAEs ~0.2–0.4 eV vs. experiment, but B3LYP systematically errs for extended/charge-transfer states (see A.3). For fused-ring electron acceptors (FREAs, relevant to D–A systems), a TD-DFT benchmark (Liu et al., *Phys. Chem. Chem. Phys.* 2020, DOI 10.1039/D0CP00060D) found absorption-maximum MAE ≈ 22 nm (PBE0) and ≈ 38 nm (B3LYP), with range-separated functionals comparable after linear calibration (CAM-B3LYP ≈ 25 nm).

### A.2 Oligomer-length convergence (n) and extrapolation

Standard practice computes a property for oligomers of increasing length n and extrapolates to n→∞. Critical findings:

- **The naive linear 1/n extrapolation FAILS for long oligomers.** Zade & Bendikov (*Org. Lett.* 2006, 8, 5243, DOI 10.1021/ol062030y) showed that B3LYP/6-31G(d) HOMO–LUMO gaps extrapolated linearly in 1/n reproduce polymer band gaps within 0.1–0.2 eV **only when long oligomers (at least 20-mer) are used**; the gap "saturates" and deviates below the 1/n line for long chains.
- The follow-up Account (Zade, Zamoshchik & Bendikov, *Acc. Chem. Res.* 2011, 44, 14, DOI 10.1021/ar1000555) recommends a **second-order polynomial fit in 1/n** at B3LYP, or directly using periodic boundary conditions (PBC/B3LYP/6-31G(d)) to avoid extrapolation entirely.
- The "Meier" criterion (Meier, Stalmach & Kolshorn, *Acta Polym.* 1997, 48, 379) defines the effective conjugation length (ECL) as reached when the bathochromic shift per added unit drops below ~1 nm; ECL is long for many systems (~16–20 thiophene rings for polythiophene/thienylenevinylenes).
- A common practical convergence threshold in TD-DFT oligomer studies is **0.05 eV change per added unit**, reached at modest n only for strongly localized systems.

**On the specific claim "n≈6 for homopolymers, n=4–6 for D–A":**
- **Partially supported, and optimistic for homopolymers.** The consensus (Zade/Bendikov) is that *true* absolute convergence needs 12–20-mers or PBC. n≈6 captures most of the homopolymer gap-narrowing and is defensible **for relative screening** (systematic offsets cancel and are absorbed by calibration), but n≈6 alone does NOT yield a converged absolute polymer gap without an extrapolation/calibration step.
- **Better supported for D–A systems.** D–A low-band-gap systems converge faster because the gap is set largely by the local D–A interaction within one repeat unit. Tetramer-level (D–B–A–B)₄ DFT is standard in the D–A design literature (Yildirim group, *ACS Omega* 2022, DOI 10.1021/acsomega.2c04713), and D–A copolymer gaps are routinely extrapolated from n=1–4 oligomers with good linearity. **n=4–6 for D–A is reasonably supported.**
- **Caveat (established):** Hutchison/Ratner/Marks and the Salzner/Brédas tradition, and the DFT-vs-PBC analysis (*Phys. Rev. B* 2003, 68, 035204, DOI 10.1103/PhysRevB.68.035204), show that simple oligomer extrapolation cannot capture band crossing, localized bands, and heteroatom effects in some polymers (polypyrrole, polyfuran, polythiophene). Per-class spot-checks against PBC or experiment are advisable.

### A.3 Known failure modes (and mitigations)

1. **Charge-transfer / low-band-gap D–A states** — the single most important failure for your D–A class. Pure and global-hybrid TD-DFT (B3LYP) **spuriously over-stabilize CT excitations**, underestimating D–A optical gaps, with errors up to ~1 eV for long-range CT (orbital-optimized vs TD-DFT study, arXiv:2311.01604). Range-separated functionals (**CAM-B3LYP, ωB97X-D, LC-ωHPBE**) correct the asymptotic behavior and are the standard fix. The Zwijnenburg DPP-dye screen (Heath-Apostolopoulos et al., *Sustainable Energy Fuels* 2021, DOI 10.1039/D0SE00985G) deliberately used **ωB97X/6-311+G** for TD-DFT because the dyes' "donor acceptor character … means that those dyes are likely to have low lying charge-transfer excited states … spuriously stabilised by non-range-separated functionals." sTDA-xTB itself *includes* range-separated exchange (partial mitigation), but in the polymer work it is calibrated to global-hybrid (B3LYP) data, so the calibration set must include D–A systems.
2. **Self-interaction error / oligomer-length artifact.** Wilbraham et al. (*J. Chem. Inf. Model.* 2018, 58, 2450, DOI 10.1021/acs.jcim.8b00256) document verbatim that "as the oligomer length decreases from 12, to 8 and then to 4 equivalent phenylene units, we see the systematic increase in optical gap relative to sTDA-xTB with decreasing oligomer length associated with the self-interaction error," mitigated by CAM-B3LYP and further by LC-ωHPBE.
3. **Planarity / conformer / torsional sensitivity.** Inter-ring torsion strongly modulates the gap; standard practice is conformer sampling + lowest-energy/Boltzmann selection. Reassuringly, the Zwijnenburg group found conjugated (co)polymer optoelectronic properties vary only weakly with conformer — "the maximum variation of a given property with respect to conformation is generally of the order of 0.1 (e)V" (Heath-Apostolopoulos, Wilbraham & Zwijnenburg, *Faraday Discuss.* 2019, DOI 10.1039/C8FD00171E), from 500 conformers each of 7 polymers. A major practical advantage for screening.
4. **Sulfur-containing systems (DIRECTLY relevant: thiophene, EDOT/ProDOT, CPDT).** The DPP-dye screen found that for optical gaps "the correlation is poor, but improves significantly when excluding dyes containing sulfur" (DOI 10.1039/D0SE00985G) — a **documented sTDA-xTB weakness for sulfur heterocycles** and a flag for your most important monomer classes. Mitigation: per-class calibration and validation against TD-DFT/experiment for S-containing families.

**Standard mitigations:** (a) range-separated functional for the TD-DFT calibration reference; (b) linear calibration of xTB→DFT scale; (c) conformer averaging/lowest-energy selection; (d) optional ML nonlinear calibration (Adamson et al. 2022: reduced xTB-sTDA MAE from 0.38 eV to 0.14 eV vs TD-DFT).

### A.4 Precedent: high-throughput conjugated-polymer screens using this route

The **Zwijnenburg group (UCL)** is the canonical precedent and validates this exact workflow:

- **Wilbraham, Berardo, Turcani, Jelfs & Zwijnenburg, *J. Chem. Inf. Model.* 2018, 58, 2450 (DOI 10.1021/acs.jcim.8b00256):** "A High-Throughput Screening Approach for the Optoelectronic Properties of Conjugated Polymers." Pipeline: GFN-xTB (geometry) + IPEA-xTB (IP/EA) + sTDA-xTB (optical gap), calibrated by **linear regression to (TD)DFT (B3LYP/DZP, with CAM-B3LYP and LC-ωHPBE checks)**. Reported quantitative accuracy:
  - IP/EA: strong linear correlation (R²=0.99); IPEA-xTB-vs-DFT MAD **0.37 V (IP) and 0.16 V (EA) before** calibration, "reduced to 0.08 and 0.06, respectively" **after** calibration.
  - **Optical gaps:** pre-calibration MADs were **0.72, 0.20, and 0.18 eV** (B3LYP / CAM-B3LYP / LC-ωHPBE, aqueous), "significantly reduced through calibration (0.15, 0.10, and 0.08 eV in an aqueous environment; 0.15, 0.10, and 0.09 eV for the nonpolar (benzene) environment)." The large B3LYP→0.15 eV improvement reflects removal of the self-interaction/length artifact.
  - The authors explicitly state the workflow is intended to generate data to train ML models — directly aligned with your longer-term goal.
- **Heath-Apostolopoulos, Wilbraham & Zwijnenburg, *Faraday Discuss.* 2019 (DOI 10.1039/C8FD00171E):** Applied to thousands of co-polymer sequences; demonstrated ~0.1 eV conformer insensitivity.
- **Saunders, Wilbraham, Prentice, Sprick & Zwijnenburg, *Sustainable Energy Fuels* 2022, 6, 2233 (DOI 10.1039/D2SE00027J):** High-throughput virtual screening of **3,240 conjugated alternating binary co-polymers and homo-polymers** (GFN1-xTB geometries, IPEA-xTB for IP/EA, sTDA-xTB for optical gap) — the scale and chemistry of your intended screen. (The set was built from a monomer library; the precise library size should be confirmed against the primary text.)
- **DPP-dye screen (DOI 10.1039/D0SE00985G):** ~45,000 DPP-based D–A dyes screened with the same calibrated-xTB approach, with ωB97X TD-DFT calibration; the most common A-site monomer is pyrrole.

Other precedent: the 747-molecule TADF benchmark (DOI 10.1021/acs.jcim.5c02978) confirms sTDA-xTB/sTD-DFT-xTB as valid screening tools with >99% cost reduction and strong internal consistency (Pearson r≈0.82).

### A.5 Computational cost at hexamer (n=6) scale

A hexamer of typical conjugated monomers is ~50–200 atoms, well within sTDA-xTB's comfortable regime (500–1000 atoms in minutes). Concrete per-molecule numbers (Intel Xeon Gold 6136; arXiv:2511.00922): conformer search ~20–27 min; GFN2-xTB optimization ~1 min; **sTDA-xTB excited-state single point ~11 s** (sTD-DFT-xTB ~33 s). A second reference (arXiv:2502.20410) reports sTDA ~20.7 s and sTD-DFT ~43.7 s per molecule, vs **>15 h (~54,000 s) for full TDA** on the same systems — a **3–4 order-of-magnitude speedup**. A conventional TD-DFT (CAM-B3LYP/def2-TZVP) calculation ≈ **50 CPU hours** per molecule, so the excited-state step is reduced by **>99%** with sTDA-xTB.

**Bottom line on cost:** the rate-limiting step is conformer search + geometry optimization (tens of min/molecule), NOT the sTDA-xTB excitation (seconds). A screen of thousands of hexamers is entirely feasible on a modest cluster.

---

## PART B — ML / GNN predictors for polymer band gap

### B.1 Models and public datasets

| Resource | Type | What it predicts | Band-gap training data | Conjugated coverage |
|---|---|---|---|---|
| **PolyInfo (NIMS)** | Experimental DB | ~100 props (experimental) | ~367,711 property points from 18,015 monomers; band gap a minor subset | Broad but commodity-dominated |
| **Khazana / Polymer Genome (Ramprasad)** | DFT+exptl DB + ML | DFT chain gap (Egc), bulk gap (Egb), dielectric, etc. | Egc=3,380; Egb=561 (Patterns 2021) | Dielectric/energy-storage-oriented |
| **polyBERT (Kuenneth & Ramprasad 2023)** | Transformer fingerprint + multitask | 29 props incl. Egc, Egb (DFT) | Egc=4,224; Egb=597 | Same Khazana corpus |
| **polyGNN (Gurnani et al. 2023)** | Multitask GNN | Egc, Egb (DFT) + 30+ props | ~3,380 (Egc proxy); Egb ≤300 | Same corpus |
| **TransPolymer (Xu et al. 2023)** | RoBERTa LM | Egc, Egb among 8–10 tasks; pretrained on PI1M (~1M) | Khazana Egc/Egb sets | Commodity-dominated |
| **Haciefendioglu & Yildirim 2025** | KPLS/QSPR | DFT Eg (B3LYP/6-311+G(d)) + λh | **3,120 D–A conjugated polymers** | **Conjugated-specific** |

### B.2 Per-model property, accuracy, size, applicability domain

- **PolyInfo (NIMS)** — the largest experimental polymer database (~367,711 property points, 18,015 monomers; Otsuka et al., IEEE iiWAS 2011; "PoLyInfo (I)," Ishii et al. 2024, describes ~half a million data points). **Experimental** and **commodity-dominated** (thermal/mechanical/electrical); band gap is a small fraction and not curated for electropolymerizable conjugated monomers. Access requires registration; scraping prohibited.
- **Khazana / Polymer Genome (Ramprasad)** — the foundational DFT polymer dataset (Huan et al., *Sci. Data* 2016, DOI 10.1038/sdata.2016.12) is **1,073 polymers** with band gaps at **HSE06** (and GGA), assembled to design **high-dielectric energy-storage polymers**; chemical space spans organic + organometallic + reference compounds, NOT conjugated semiconductors. **Property = DFT *fundamental* band gap (HSE06) of the periodic chain/crystal — NOT the optical gap.** Polymer Genome (Kim et al., *J. Phys. Chem. C* 2018, DOI 10.1021/acs.jpcc.8b02913; Doan Tran et al., *J. Appl. Phys.* 2020, DOI 10.1063/5.0023759) offers band gap among predictable properties.
- **polyBERT (Kuenneth & Ramprasad, *Nat. Commun.* 2023, 14, 4099, DOI 10.1038/s41467-023-39868-6)** — Property = DFT **chain gap Egc (4,224 points, range 0.02–10 eV)** and **bulk gap Egb (597 points)**. Accuracy reported as **R²** (Fig. 5): overall dataset-wide R²=0.80 (polyBERT) vs 0.81 (handcrafted Polymer Genome fingerprint). **Band-gap-specific MAE/RMSE in eV are only in Supplementary Tables S1–S5, not the main text** (I did not fabricate them). Same Khazana/energy-storage corpus → domain skews dielectric/commodity.
- **polyGNN (Gurnani et al., *Chem. Mater.* 2023, 35, 1560, DOI 10.1021/acs.chemmater.2c02991)** — Multitask GNN over 13,388 polymers / 21,000+ data points. Property = DFT Egc, Egb. **Reported accuracy (Table 1, multitask polyGNN, unseen test data): RMSE 0.445 ± 0.018 eV (Egc), 0.468 ± 0.066 eV (Egb)**, in eV. Egb has ≤300 data points. **Only RMSE reported (no MAE).** Same corpus → same domain limitation.
- **TransPolymer (Xu, Wang & Barati Farimani, *npj Comput. Mater.* 2023, DOI 10.1038/s41524-023-01016-5)** — RoBERTa LM, pretrained on ~5M augmented PI1M sequences, fine-tuned on Egc/Egb among 10 tasks. Strong R² on Khazana band-gap sets but **inherits the commodity-skewed domain**.
- **Haciefendioglu & Yildirim, *J. Chem. Inf. Model.* 2025, 65, 5360 (DOI 10.1021/acs.jcim.5c00345)** — the **only conjugated-specific public effort.** Manually curated **3,120 D–A conjugated polymers from 60 donors × 52 acceptors**, band gaps at **B3LYP/6-311+G(d)** (Jaguar). Best model (KPLS, radial fingerprints): **R²=0.899 (train), Q²=0.900 (test)**; a numerical-descriptor model reported training **RMSE ≈ 0.194 eV** (the binary-fingerprint RMSE=0.007 figure appears to be on a scaled target and is not credible as an eV error). Donor families include thiophene-, benzothiophene-, and pyrrole-based units; **explicit coverage of EDOT, carbazole, fluorene, and CPDT is likely but unconfirmed from the primary text.** A **single study**; the trained model is not distributed as a turnkey tool.

**Calibration context:** crystal/molecular GNNs (CGCNN, MEGNet, ALIGNN) reach band-gap MAEs of ~0.22–0.39 eV on large inorganic datasets (tens of thousands of points), so ~0.45 eV RMSE on a few thousand heterogeneous polymer points is consistent with data-limited performance and improves systematically with dataset size.

### B.3 Off-the-shelf vs. fine-tune/train — and the data-availability constraint

- **Off-the-shelf is not viable.** Public turnkey models (polyBERT, polyGNN, Polymer Genome, TransPolymer) predict the **DFT fundamental/chain gap, not the optical gap**, and their training domains are dominated by non-conjugated commodity/dielectric polymers. Applying them to EDOT, CPDT, or low-band-gap D–A systems is out-of-domain extrapolation; errors will exceed the reported ~0.45 eV RMSE and be unreliable for ranking low-gap candidates.
- **Labeled, in-domain data is the binding constraint.** Public conjugated-polymer band-gap labels are scarce: ~3,380 DFT chain gaps in Khazana (mixed chemistry) plus the 3,120 D–A DFT gaps of Haciefendioglu & Yildirim (not released as a model). PolyInfo's band-gap entries are sparse and not conjugated-curated. **There is no large, public, optical-gap-labeled, electropolymerizable-monomer dataset.**
- **Fine-tune/train is the realistic path — and it depends on generating your own labels.** A GNN or fine-tuned transformer needs on the order of several thousand to tens of thousands of consistent in-domain gaps to beat a calibrated physics method inside your chemistry. That dataset is exactly what **Route A can manufacture**, which underpins the staged recommendation below.

---

## PART C — Tradeoffs and recommendation

### C.1 Comparison

| Dimension | Route A: Oligomer + sTDA-xTB (calibrated) | Route B: ML / GNN predictor |
|---|---|---|
| **Accuracy (screening-grade)** | ~0.27–0.5 eV vs reference raw; **0.08–0.15 eV vs DFT after linear calibration** (Zwijnenburg). Vertical-approx & sulfur caveats. | DFT-gap RMSE **~0.45 eV** (polyGNN); conjugated-specific R²≈0.90 (single study). Off-domain for low-gap D–A in public models. |
| **Property actually predicted** | **Optical gap** (lowest dipole-allowed vertical excitation) — matches your descriptor | Mostly **DFT fundamental/chain gap**, NOT optical gap (mismatch) |
| **Effort to stand up** | Moderate: oligomer builder (SMILES→3D), conformer search, xTB+sTDA pipeline, one-time TD-DFT calibration set. Published recipe exists. | Low if off-the-shelf (but wrong domain); **high** if training in-domain (requires data you don't yet have) |
| **Compute cost** | ~tens of min/molecule (conformer-search dominated); sTDA step ~seconds. Scales to thousands. | Inference ~ms once trained; training modest — but **labeling cost is the real cost** |
| **Robustness across YOUR monomer classes** | Uniform applicability to any drawable monomer (thiophene, EDOT/ProDOT, pyrrole, furan, selenophene, aniline, carbazole, fluorene, CPDT, D–A). **Flags: sulfur heterocycles, low-gap CT states** → handle with RSF calibration | Only as good as training coverage; public data thin on EDOT/CPDT/D–A. Brittle out-of-domain |
| **Durability / fit for ML-foundation direction** | Generates the in-domain labeled dataset needed downstream; physics-grounded, no retraining as chemistry expands | The eventual goal for fast generative-loop scoring; durable only once trained on adequate in-domain data |

### C.2 Recommendation — "Do A now, B later"

**Stage 1 (now → ~3 months): Stand up calibrated sTDA-xTB as the band-gap axis.**
- Build the pipeline: SMILES → oligomer assembly (n=6 for homopolymers; n=4–6 for D–A) → conformer search (ETKDG/MMFF or CREST) → GFN2-xTB optimization → sTDA-xTB optical gap. Adopt the published Zwijnenburg recipe directly.
- Build a **calibration set of 50–150 oligomers spanning all 10 monomer classes**, compute reference optical gaps with a **range-separated functional (CAM-B3LYP or ωB97X-D)** to handle D–A CT states, and fit a per-class (or class-aware) linear calibration. **Explicitly include sulfur-heterocycle (thiophene/EDOT/CPDT) and D–A subsets** given the documented sulfur weakness.
- Use length extrapolation (2nd-order polynomial in 1/n, or PBC spot-checks) where absolute gaps matter; for a 1-of-5 ranking axis, calibrated n=6 vertical gaps suffice.

**Stage 2 (parallel/continuous): Harvest the labels.** Every screened candidate yields a calibrated optical gap. Store these systematically — this becomes your in-domain training corpus.

**Stage 3 (once ~5,000–20,000 in-domain calibrated gaps exist): Train Route B as a surrogate.** Fine-tune a polymer GNN (polyGNN architecture) or transformer (polyBERT/TransPolymer embeddings) on your labels for millisecond-scale inference inside the generative/ML design loop. Route B earns its keep here — as the fast scorer for inverse design, not as the primary screen.

### C.3 Benchmarks/thresholds that would change the staging
- **Adopt B as primary sooner** if (a) a public, optical-gap-labeled conjugated-polymer dataset of >10,000 entries covering your classes is released, or (b) the Haciefendioglu/Yildirim model (or equivalent) is published as a validated, distributable predictor covering EDOT/CPDT/D–A with held-out MAE < 0.2 eV.
- **Escalate Route A fidelity** (move from sTDA-xTB to direct TD-DFT for a subset) if calibrated xTB gap error vs experiment for any monomer class exceeds ~0.3 eV in validation — especially sulfur heterocycles or strong D–A systems.
- **Trigger Stage 3** when your accumulated in-domain dataset lets a held-out GNN beat calibrated-xTB error on your chemistry (validate on a frozen test set).

### C.4 Main risks
- **Route A:** sulfur-heterocycle inaccuracy (documented); CT-state errors for strong D–A if the calibration reference is a global hybrid (mitigate with a range-separated functional); reliance on one research group's calibration approach (mitigate by validating against experimental gaps for known polymers per class — e.g., PEDOT, P3HT, PCPDTBT).
- **Route B:** domain mismatch (most public models predict fundamental, not optical, gap on commodity chemistry); data scarcity; single-study evidence for the only conjugated-specific dataset; overfitting on small band-gap subsets (Egb ≤300 points).

---

## Caveats (sourcing and confidence)

- The "0.08–0.15 eV after calibration" optical-gap accuracy comes from the Zwijnenburg group (multiple papers, but one research group). Treat as well-documented for their workflow, not as an independently replicated universal number.
- polyBERT and the Patterns-2021 multitask model report band-gap errors as R² / normalized RMSE in their main text; absolute eV MAEs sit in Supplementary tables that could not be independently extracted — I have **not** fabricated those numbers. polyGNN's 0.445/0.468 eV RMSE figures are explicit in its main-text Table 1.
- The "n≈6 homopolymer / n=4–6 D–A" claim is *defensible for screening*, but the absolute-convergence literature (Zade/Bendikov) shows true convergence needs longer oligomers or PBC — flagged accordingly.
- The Haciefendioglu & Yildirim binary-fingerprint RMSE=0.007 value is internally inconsistent (likely a scaled target) and should not be cited as an eV error; the descriptor-model RMSE≈0.194 eV is the physically plausible figure.
- The Saunders et al. 2022 screen covers **3,240** conjugated co/homo-polymers; the monomer-library size should be verified against the primary text before being quoted as a fixed number.
- All ML band-gap accuracies above are for **DFT-computed** gaps (a property mismatch with the optical gap you want), reinforcing the recommendation to treat Route B as a downstream surrogate rather than a primary descriptor.