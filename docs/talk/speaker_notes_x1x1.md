# CombHTS 汇报讲稿 / Speaker notes — x1x1.pdf
> 结构化中英双语逐页讲稿。Generated 2026-06-30;数字均已对仓库核验。

## ⚠️ 上台前必改(4 个硬错误 / blockers)

| # | 页 | 现在 | 应改为 |
|---|----|------|--------|
| 1 | **S3 步3** | "GBSA implicit solvation" | **ALPB** (`xtb --alpb`);xtb_gbsa_name 仅历史遗留 |
| 2 | **S5 漏斗** | Tier-1 **2,718** / 36% | **3,275** / **43.7%**(6/29 切 relaxed;2,718 是旧 strict) |
| 3 | **S5 漏斗** | Tier-2 **2,354** / 87% | 删(由过时 2,718 反推)→ "partial (in progress)",已精修 **1,610** 折叠行,不给% |
| 4 | **S4 步4** | `2 M⁺ → [M-M]²⁺ + 2H⁺` | `2 M⁺· → M–M(中性) + 2H⁺`(电荷平衡;dication 多算一次氧化,仓库已否定) |

次要修订见各页 **⚠️ 改图** 段:S3 构象 50-200→固定 100;S5 勾选 "29 Peak"→"30 anchors/29 LOO-CV"、"Calibration finished"→拆 exp-anchored 完成/xTB→DFT n=15 partial;S6 图注补 "(small-core;D-A pending 418096)";S7 n=30 vs n=29 加注;S9 加 Pareto 5D→2D 说明+保留率 43.7%。

---


## S1 · Screening Pipeline: Methods
**核心** — 漏斗式三层:越往右每个候选越贵,每层先压数量再加精度。*Funnel — cheaper-first; cut count before adding accuracy.*
**流程** — Target Space (monomer × solvent × electrolyte 三元组) → Rapid Pre-Screen (Tier-1 xTB, 3 硬约束 → Hard-Constraints Survivors) → DFT Refinement (Tier-2 ORCA B3LYP/6-31G(d,p)/SMD, 复核同物理量 + 自旋密度/二聚) → 二次硬约束 → Composite Scoring (五轴加权) → shortlist → Downstream Experiments。*Combinatorial triads, funneled stage by stage to a downstream shortlist.*
**方法(原理 → 匹配描述符 → 近似掉什么)**
- **GFN2-xTB** — GFN紧束缚法(最小价基 + 密度涨落二阶 + 自洽多极静电 + 内置D4,无双电子积分/无精确交换);真空3D几何优化。几何=崎岖扭转面上构型排序,要相对位阻/静电次序非绝对电子能 → 毫秒级库规模够用。近似掉精确交换+真实基组 → 绝对电子能不可靠,作几何源足够。*Tight-binding; vacuum geometry as config-ordering; abs. energy unreliable, geometry-grade.*
- **IPEA-xTB** (`xtb --vipea`) — GFN1 Hamiltonian 上独立参数化 + 经验IP/EA位移,直出含位移垂直IP/EA。描述符:monomer/solvent 的 IP/EA → 经线性标定得 E_ox(Tier-1 最关键硬约束);solvent 介电经 ALPB。比 GFN2 HOMO 代理准——IP/EA 本就是氧化起始的物理量,§4.1 明确要求(非泛用 GFN2 HOMO)。近似掉显式带电态 ΔSCF → 单次中性 + 固定经验位移;化学相近 monomer 误差近常数斜率+截距,线性标定可回收大部分。*Purpose-fit IP/EA via GFN1+shift; §4.1-mandated; systematic error → linearly calibratable.*
- **sTDA-xTB** — xTB 基态上简化 Tamm-Dancoff TD,能量窗截断组态空间 + 单极(Mulliken跃迁电荷)替完整 TD-DFT 响应核。描述符:六聚体(N=6)光学带隙——聚合物带隙用 oligomer 激发近似,带隙随链长收敛,6 单元为外推点。给真激发态能(非基态轨道差),代价低到全库可跑 6-mer。相对 CAM-B3LYP TD-DFT 简化掉完整 XC 响应核 + 截断CI + xTB 基态 → 对发色团类近均匀压缩绝对激发能,近常数斜率/截距,线性标定适用。*Simplified TDA on xTB; N=6 oligomer→polymer gap extrapolation; true excited-state energy; calibratable.*
- **COSMO-RS** — 表面电荷密度统计热力学:各分子先 COSMO 得 σ-profile,混合物化学势由 σ-profile 间成对表面段相互作用自洽平均。描述符:monomer-solvent ΔGsolv(溶解度/溶剂化硬约束轴)。优于单一介电连续介质(SMD/ALPB)——从第一性 σ-profile 解析特定溶质-溶剂表面相互作用(含氢键),给溶剂特异 ΔGsolv。关键解耦:相互作用是两 σ-profile 成对泛函,单分子昂贵量化(σ-profile)与配对无关,算一次全配对复用 → 成本 O(m×s)→O(m+s)。本仓库 ORCA 6.1 σ-profile,DECOUPLED 每物种一份,覆盖 468 monomer × solvent 对:解耦约 44 CPU-hr vs 成对约 560 CPU-hr,约 13×。*Statistical thermo over σ-profiles; H-bond-aware ΔGsolv; decoupled 44 vs 560 CPU-hr (~13×).*
- **B3LYP/6-31G(d,p)** — 杂化泛函,约 20% 精确(HF)交换混入 GGA(Becke88 + LYP + B3 三参数);6-31G(d,p) 双 zeta 价基带极化。描述符:Tier-2 氧化还原电位/自旋密度/二聚化 ΔG——即 Tier-1 各 xTB 描述符校准锚定的参考。精确交换纠正纯 GGA 前线轨道自相互作用误差,双zeta+极化是定量描述孤对/π 极化的最小基组,验证规模有机氧化还原 monomer 的代价/精度甜点。这正是 xTB 近似掉的(无精确交换/最小基),故 xTB→B3LYP 误差系统性。*Hybrid + double-ζ polarization; the Tier-2 reference; xTB→B3LYP error is systematic.*
- **SMD** — 基于密度的溶剂化:溶质电荷密度极化连续介质(IEF-PCM型),原子中心半径叠加成空腔 + 非静电 CDS 项(空化/色散/溶剂结构),由溶剂描述符(ε、折射率、Abraham 氢键酸碱、表面张力)参数化。描述符:DFT 氧化还原层每溶剂隐式连续介质。显式非静电项使绝对 ΔG_solv 够定量,可把溶剂化氧化还原电位放上电化学窗口比较——ALPB 代理做不到。诚实标注:4 溶剂(硝基苯/苯腈/硝基甲烷/环丁砜)可直接命名,PC/GBL/NMP 需自定义 Generic,Read 块,3 离子液体 + Reline DES + BFEE 被排除(结构化/离子/Lewis 酸介质连续介质表达差;BFEE 共价配位降低氧化电位,须按显式加合物建模)。*Density-based continuum + CDS; quantitative ΔG_solv; 4 named, 3 PC/GBL/NMP custom, IL/DES/BFEE excluded.*
- **TD-DFT/CAM-B3LYP** — 线性密度响应传播得激发能;CAM-B3LYP 距离分离(库仑衰减)杂化,交换混入随电子间距增大(短程约 19% HF → 长程 65% HF),恢复 B3LYP 缺失的正确 −1/r 渐近交换势。描述符:oligomer 带隙收敛(n=1-6)参考光学/带隙 + 电荷转移激发能——sTDA-xTB 六聚体带隙的验证锚。共轭 oligomer 激发(尤其长程 CT)在普通杂化下灾难性坍塌(CT 能过低),因缺长程精确交换;距离分离核修复,是 sTDA 近似的聚合物带隙正确参考。*Range-separated hybrid restores −1/r; fixes CT collapse; the sTDA validation anchor.*
**统一逻辑** — 为何"便宜方法 + 线性标定"成立:每个 xTB 层方法相对 DFT 对应物丢同样物理(精确交换/真实基组/逐体系重参数化),每项缺失对给定化学只平移近常数斜率/截距,非随机噪声 → 两参数仿射拟合吸收主导系统误差,残余 MAE 即不可约随机部分。*Same dropped physics → constant slope/offset → affine fit absorbs it; residual MAE is irreducible.*
**⚠️ 改图(口头补充)**
- 表格无错,但 B3LYP 行需补一句:现状 — dG_dimerization 列为描述符,当前 proton-referenced / screening-grade / 未标定(§5 f4 DFT 项替换前);应为 — 讲到该格明说诊断级、未标定,勿被听成已验证定量值。*B3LYP dimerization cell: flag diagnostic & uncalibrated aloud.*

## S2 · Screening Pipeline: Calibration and Validation
**核心(标定 vs 验证)**
- **标定 Calibration** — 治便宜方法的系统误差:xTB 相对 DFT 系统丢精确交换/真实基组/逐体系参数化 → 描述符平移近常数斜率+截距;两参数仿射映射把 xTB 校到 DFT 质量。directive 定义此段为 xTB→DFT。*Affine map cheap→expensive; xTB→DFT leg.*
- **验证 Validation** — 治锚定现实:再精确的链也须对实验负责;把 DFT 算出量对照文献实验值。directive 定义为两条 →experiment 腿(DFT→exp、组合 xTB→DFT→exp)。*Aligns expensive→reality; two →exp legs.*
- 一句区分:标定让便宜对齐昂贵,验证让昂贵对齐现实。*Calibration: cheap→expensive. Validation: expensive→reality.*
**两 xTB 方法各简化了什么**
- **IPEA-xTB vs B3LYP 氧化还原**(显式带电态 ΔSCF + SMD) — 用单次中性 + 固定经验 IP/EA 位移替对 cation/anion 各做 SCF 的显式 ΔSCF,并丢精确交换。*Neutral+shift replaces explicit ΔSCF; drops exact exchange.*
- **sTDA-xTB vs TD-DFT/CAM-B3LYP 激发** — 单极(Mulliken跃迁电荷)耦合替完整 XC 响应核,能量窗截断 CI,建于 xTB 基态。*Monopole coupling + truncated CI on xTB ground state.*
- 为何线性标定够:对给定化学类,两种简化误差主导成分系统性(近常数斜率/截距平移)非随机 → 两参数拟合吸收主导系统部分,残余随机散点定标定 MAE。*Systematic-dominant error → 2-param fit absorbs it; scatter sets MAE.*
**四个验证目标(各测什么)**
- (1) Tier-2 monomer Eox MAE < 0.15 V — DFT 层氧化电位对实验绝对精度。*DFT-tier abs. accuracy vs exp.*
- (2) Tier-1 monomer Eox MAE < 0.3 V — 经标定 xTB 层氧化电位是否够作硬约束筛选门槛。*Calibrated xTB gate adequacy.*
- (3) 溶剂 ESW 两层均 MAE < 0.3 V — 电化学窗口描述符(驱动 window_margin 约束)精度。*ESW descriptor accuracy, both tiers.*
- (4) 聚合可行性准确率 > 85% — 能否分开"真偶联成膜"与"仅氧化分解"的 monomer。*Couples-to-film vs decomposes.*
**当前状态(诚实)**
- Tier-1 xTB→DFT 标定(§7 step 1,记录在案):dft_Eox = 0.7675·xtb_Eox − 0.5789,R² 0.883,MAE 0.122 V,n=15。partial — 小分子核心已完成,大 donor-acceptor 化合物(ORCA run SGE 418096)仍在算,n=15 须明说 partial。*Calibration of record; n=15 partial, large D-A still running.*
- DFT→exp 验证(peak,n=10):raw MAE 0.496 V(约 0.5 V 系统性参考偏移);线性 DFT→exp 拟合消掉后残差降至 0.151 V。*Raw 0.496→0.151 after offset removed.*
- 组合 xTB→DFT→exp = 0.648/0.116,与在用实验标度线 0.730/0.093 在约 0.1 V 内一致 → 交叉验证两段链。*Composed chain cross-validates within ~0.1 V.*
- sTDA-xTB 一侧:TD-DFT 结果尚未就绪以标定 sTDA-xTB(中性事实状态)。*TD-DFT not yet ready to calibrate sTDA.*
**🔑 关键问题(Problem solved)**
- 问题 — 在用生产线是 experiment-anchored Tier-1 氧化标定(relaxed 30-peak:slope 0.7304、intercept 0.0929、LOO-CV MAE 0.198 V、R² 0.559、n=29 groups / 30 rows、IPEA-xTB),而 directive 明确规定标定应是 xTB→DFT、把 →experiment 留给验证;真实方法偏离,须讲清。*Production line is exp-anchored, directive wants xTB→DFT.*
- 思路 — DFT 基准批次落地前,xTB→experiment 直拟合是显式临时替身:机读、诚实,但把 DFT 应承担的 →experiment 角色压到 xTB 标定上,且把 ≥30 净组负担错放到标定纯度而非验证覆盖。*Interim stand-in; misplaces →exp role & ≥30-group burden.*
- 解决 — xTB→DFT 标定已开始落地(n=15 partial,R² 0.883,MAE 0.122 V),组合链 xTB→DFT→exp(0.648/0.116)对在用实验线(0.730/0.093)在约 0.1 V 内交叉验证;待 D-A monomer DFT 算完,再决定是否把生产标定从 experiment-anchored 切到 xTB→DFT 记录线。*xTB→DFT landing; switch decided once D-A DFT done.*
**⚠️ 改图**
- 验证目标 "Tier-2 monomer Eox MAE < 0.15 V":现状 — 易被当作有把握达到的目标;应为 — 加口径,此类氧化还原预测物理精度地板约 0.20-0.35 V,0.15 V 处于或低于该地板,讲成"directive 设定但很可能触物理地板"(即 Slide 10 提出的问题)。*Frame 0.15 V as likely hitting the ~0.20-0.35 V physical floor (Slide 10).*
- 脚注引 J. Chem. Inf. Model. 2018, 58, 2450-2459(IPEA-xTB 线性模型来源):讲到 IPEA-xTB→B3LYP 质量映射时点名即可。*Cite the IPEA-xTB source at the IPEA→B3LYP mapping.*

## S3 · T1-Rapid Pre-Screen: Plan (5 steps)
**核心** — 半经验 xTB 廉价初筛全库(试点 7,488 triad),砍明显不可行者,存活者交 DFT。*Cheap xTB over whole library; discard infeasible, pass survivors to DFT.*
**逻辑** — 每步出一个判定描述符,严格次序:先几何 → 再电子结构 → 最后筛选量。*Each step yields a decision descriptor: geometry → electronic structure → screening quantities.*

**第 1 步 结构生成**
- 目的 — 给所有下游量子计算一个干净低能起始几何;几何错则一切错。*Clean low-E starting geometry; bad geometry corrupts all descriptors.*
- 手段 — SMILES → RDKit ETKDGv3(实验扭转角偏置的纯几何嵌入)→ MMFF94(经典价键力场:键/角/二面角+vdW+库仑,无电子)优化取最低能构象;聚合物用 stk 装 n=2–6 寡聚物。*ETKDGv3 embed + MMFF94 classical FF; stk for n=2–6 oligomers.*
- 为何力场 — 选构象是崎岖扭转面上的相对立体/静电排序采样,定工作构象的是相对排序非绝对电子能 → 毫秒力场恰当,库规模 QM 优化负担不起。*Conformer pick = relative ordering, not abs. energy; ms-FF right, library-scale QM unaffordable.*

**⚠️ 改图**
- 现状 — 幻灯片写"MMFF94 conformer search 50-200"。*Slide says "50-200".*
- 应为 — 实际固定 100 构象(configs/tier1.yaml:53–55, n_conformers=100, method=mmff94);改为"MMFF94 构象搜索(每单体 100 个 ETKDGv3 构象);保留最低能量者"。*Fixed 100, not a range; reword to "100 ETKDGv3 conformers per monomer; keep lowest-E".*

**第 2 步 xTB 几何优化**
- 目的 — 把力场粗几何升到量子级,并备好三电荷态供氧化/还原描述符。*Upgrade to QM geometry; prepare 3 charge states for redox.*
- 手段 — GFN2-xTB(几何-频率-非共价紧束缚,近似DFT,最小价基,能量展到密度涨落二阶,自带D4)真空中分别优化中性/阳离子自由基/阴离子。*GFN2-xTB approx-DFT, minimal basis, 2nd-order density fluctuations, D4; vacuum, 3 charge states.*
- 为何 — 无精确交换、无真实基组,但毫秒-秒级可承担整库;相对 DFT 误差系统性(压缩轨道谱+色散偏置)→ 单线校准的物理基础。*No exact exchange/real basis but cheap; systematic error → single-line calibratable.*

**第 3 步 氧化还原电位 IP/EA**
- 目的 — 产出本层最重要硬约束:单体氧化电位 E_ox(氧化起始由 IP/EA 直接决定)。*Most important hard constraint: E_ox from IP/EA.*
- 手段 — IPEA-xTB(`xtb --vipea`,GFN1+经验IP/EA能移)直接算垂直IP/EA,非 GFN2 HOMO Koopmans 代理;directive §4.1 明确要求,专拟参数化精度高于 HOMO 代理。*Purpose-fit IPEA-xTB, not HOMO proxy; mandated by §4.1.*
- 换算 — 隐式溶剂用 ALPB(各候选溶剂介电);IP 经绝对 SHE 钉点 4.28 V、Ag/AgCl 偏移 −0.197 V 换算成电位。*ALPB solvation; IP→potential via SHE 4.28 V, Ag/AgCl −0.197 V.*

**关于隐式溶剂(给非专家)**
- 概念 — 不放真实溶剂分子,把溶剂当连续可极化介电,用 ε 概括对溶质电荷的屏蔽:便宜、可微、宜筛选。*Continuous dielectric, ε screens charge; cheap, differentiable.*
- ALPB — 解析线性化 Poisson–Boltzmann,给静电溶剂化自由能 + 基于溶剂可及表面积的非极性项。*Analytical linearized PB; electrostatics + SASA non-polar term.*
- 对比 GBSA — 前身 GBSA 用经验 Still 型广义-Born 成对插值近似同套静电;ALPB 扎根线性化 PB 算子(带电物种/低-ε 更好),且保持闭式、梯度便宜。*ALPB > GBSA: PB-grounded, better for charged/low-ε, still closed-form.*

**⚠️ 改图**
- 现状 — 幻灯片第 3 步写"GBSA implicit solvation"。*Slide says GBSA.*
- 应为 — 引擎实际调 ALPB(`solvent_flag` 返回 `["--alpb", xtb_gbsa_name]`,src/eps/engines/xtb.py;变量名为历史遗留,解析为 ALPB);改为"ALPB implicit solvation(`xtb --alpb`), solvent-specific epsilon"。*Engine uses ALPB; legacy var name only; reword to ALPB.*

**关于校准线要诚实(给 PI)**
- 在线 — 实验锚定"宽松"30 峰校准:slope 0.7304, intercept 0.0929, LOO-CV MAE 0.198 V, R² 0.559, n=29 组/30 行。*Active: exp-anchored 30-peak; 0.7304/0.0929, LOO 0.198, R² 0.559, n=29/30.*
- 定位 — 真实但筛选级:R²~0.56,MAE 近此类氧化还原 ~0.20 V 物理下限,且实验锚定而 directive 规定 xTB→DFT 链。*Screening-grade; MAE near ~0.20 V floor; exp-anchored vs directive's xTB→DFT.*
- xTB→DFT — 记录线 dft_Eox = 0.7675·xtb_Eox − 0.5789, R² 0.883, MAE 0.122 V, n=15;部分完成(小单体核心已算,大 D-A 仍在算,ORCA SGE 418096)。*Record line 0.7675/−0.5789, R² 0.883, MAE 0.122, n=15; partial.*
- 交叉验证 — 组合 xTB→DFT→exp = 0.648/0.116 与在线 0.730/0.093 在 ~0.1 V 内一致;仍按筛选级呈现,非已验证真理。*Composed 0.648/0.116 agrees w/ 0.730/0.093 within ~0.1 V; still screening-grade.*

**第 4 步 溶剂化自由能 COSMO-RS**
- 目的 — 产出溶解度/溶剂化硬约束轴 ΔGsolv,每对单体×溶剂。*Solubility hard-constraint ΔGsolv per monomer×solvent.*
- 手段 — openCOSMO-RS(ORCA 6.1 sigma-profile),按物种解耦,覆盖 468 对,硬过滤 ΔGsolv ≤ −3.0 kcal/mol。*openCOSMO-RS decoupled per-species; 468 pairs; filter ≤ −3.0 kcal/mol.*

**🔑 关键问题(COSMO-RS 解耦)**
- 问题 — 朴素成对 = O(单体×溶剂) DFT,成本压垮:30 大单体×25 溶剂×45 min ≈ 560 CPU-时,超整个 Tier-1 预算。*Naive pairwise O(M×S) DFT ≈ 560 CPU-hr, over budget.*
- 思路 — COSMO-RS 用统计热力学:每分子一次 COSMO 算出 sigma-profile p(σ)(溶剂可及面屏蔽电荷密度直方图);混合物化学势由表面段成对相互作用(错配静电+氢键)自洽统计平均得到;相互作用是两 profile 的成对泛函,故一分子的 p(σ) 与配对无关、算一次可复用。*p(σ) computed once, reusable across all pairings; interaction is pairwise functional of two profiles.*
- 解决 — 成本降至 O(单体+溶剂):每物种一次 sigma-profile DFT,每对 ΔGsolv 只是毫秒级无 DFT 统计积分;生产路径(~30 大 + ~100 中小单体 + ~25 溶剂)≈ 44 CPU-时,令人尴尬地并行,几挂钟小时,落在 §9 预算内——约 13× 差距,不可行变可行。*O(M+S): 44 CPU-hr, embarrassingly parallel; ~13× vs 560, infeasible→feasible.*

**为何不用单一介电** — SMD/ALPB 只给均匀介电;COSMO-RS 从第一性 sigma-profile 解析特定溶质-溶剂表面相互作用(含氢键),给溶剂特异 ΔGsolv 而成对边际成本近零——每对溶解度硬约束所需。*COSMO-RS resolves specific H-bonding interactions; solvent-specific ΔGsolv at ~0 marginal cost.*
**状态** — 引擎已实现并端到端验证(SGE 417990:解耦 thiophene/MeCN ΔGsolv −4.154 vs 试点 −4.132 kcal/mol);余 Tier-1 接线 + 整库 sigma-profile 收割。*Engine validated (−4.154 vs −4.132); remaining: wiring + full harvest.*

**第 5 步 光学带隙 sTDA-xTB**
- 目的 — 聚合物光学/带隙代理,供 band_gap_deviation 排序(非硬过滤,仅排序/报告)。*Optical-gap proxy for ranking only, not a hard filter.*
- 手段 — 六聚体(N=6,共轭聚合物外推点)上 sTDA-xTB(xTB 基态上简化 Tamm–Dancoff TD,能量窗截断组态空间,Mulliken 跃迁电荷单极近似代替完整 TD-DFT 响应核)取最低单重态激发能为光学带隙,对照 TD-DFT 校准。*sTDA-xTB on hexamer; monopole approx replaces TD-DFT kernel; lowest singlet = gap.*
- 状态 — TD-DFT 尚未就绪以校准,该光学描述符目前未校准、筛选级/诊断量出库(中性状态陈述)。*TD-DFT not ready; ships uncalibrated/diagnostic.*

**读图 — Tier-1 硬过滤 ↔ 描述符** (configs/tier1.yaml,共三条)
- ① 窗口裕度 — 单体 AIP < 溶剂阳极极限 − 0.3 V(window margin > 0.3 V),保证单体在溶剂电化学窗口内可氧化;源自第 3 步 E_ox。*Window margin > 0.3 V; from step-3 E_ox.*
- ② 阴离子稳定性裕度 — 阴离子氧化电位 > 单体 AIP + 0.2 V(margin > 0.2 V),保证支持电解质阴离子不先于单体被氧化;源自第 3 步校准氧化电位。*Anion margin > 0.2 V; from step-3 potentials.*
- ③ 溶剂化 — 单体 ΔGsolv < −3.0 kcal/mol;源自第 4 步 COSMO-RS。*ΔGsolv < −3.0 kcal/mol; from step-4.*
- 非硬过滤 — 带隙、二聚化只进排序/报告;留存率 ~10–20%。*Band gap & dimerization ranking-only; retention ~10–20%.*

## S4 · T2-DFT Refinement: Plan (8 steps)
**核心** — 只对 Tier-1 存活者跑 ORCA B3LYP/6-31G(d,p)/SMD,把廉价半经验描述符升为验证级 DFT 量并收紧过滤。*ORCA B3LYP/6-31G(d,p)/SMD on survivors; upgrade descriptors, tighten filters.*
**校准锚** — 本层是校准 xTB 的锚;xTB 系统误差正是相对此级被一条仿射线吸收。*Tier-2 is the anchor; xTB systematic error absorbed by one affine line.*

**第 1 步 DFT 几何优化**
- 目的 — 产出参考几何,溶剂中备好各电荷态。*Reference geometries; charge states in solvent.*
- 手段 — B3LYP/6-31G(d,p) + SMD,优化中性/阳离子自由基/阴离子(溶剂与离子的带电态也算)。*B3LYP/6-31G(d,p)/SMD; all charge states incl. solvents/ions.*
- 为何 — B3LYP 混入 ~20% 精确(HF)交换的杂化泛函,6-31G(d,p) 带极化双 zeta 价基——正是 xTB 近似掉的,故 xTB→DFT 误差系统性。*~20% HF exchange + polarized double-zeta = what xTB drops → systematic error.*

**第 2 步 绝热 ΔSCF 氧化还原电位**
- 目的 — 验证级绝热氧化电位:Tier-1 垂直-IP 筛的物理严格版 + 校准锚。*Validation-grade adiabatic E_ox; rigorous version + anchor.*
- 手段 — E = [G(阳离子) − G(中性)]/F − E_ref,同一 SHE/Ag/AgCl 尺度(绝对 SHE 4.28 V,再 −0.197 V 到 Ag/AgCl),加 298 K 热校正与 ZPE。*ΔG/F − E_ref; SHE 4.28 V, −0.197 V Ag/AgCl; 298 K thermal + ZPE.*

**关于绝热 ΔSCF(给非专家)**
- ΔSCF — 中性与阳离子(或阴离子)各做独立 SCF,取自由能之差。*Separate SCF per charge state, take ΔG.*
- 绝热 — 每电荷态弛豫到自身平衡几何(非冻在中性几何);加热校正+ZPE = 真实 CV 所测的弛豫自由能氧化电位。*Each state relaxes; = relaxed free-E potential a CV measures.*
- 对照 — Tier-1 垂直(冻几何)IPEA-xTB 快;Tier-2 绝热准。*Tier-1 fast/vertical, Tier-2 accurate/adiabatic.*

**第 3 步 自旋密度分析(Hirshfeld)**
- 目的 — 阳离子自由基反应位点图,预测电聚合偶联区域化学。*Reactive-site map; predict coupling regiochemistry.*
- 手段 — 单体阳离子自由基上用 Hirshfeld(stockholder)把自旋密度(α−β 布居)分到各原子,标出未配对电子/自由基反应性定域处。*Hirshfeld partitions α−β spin onto atoms; marks reactive sites.*

**关于 Hirshfeld 自旋密度与 α-α/α-β 耦合(给非专家)**
- 定义 — 自旋密度 = α 布居 − β 布居;Hirshfeld 按各原子自由原子密度份额加权,把 α−β 差分摊到原子。*Spin density = α−β; Hirshfeld weights by free-atom density share.*
- 耦合 — 符号/图样区分 α-α 耦合(同号自旋、同位点离域、铁磁型)与 α-β 耦合(异号)。*α-α: same-sign/same-site (ferromagnetic-type); α-β: opposite.*
- 物理 — 电聚合经阳离子自由基在最高自旋位点偶联,故自旋定域直接预测偶联位置(如噻吩 α-α 连接),并标出自旋离域到不反应位点的假阳性单体。*Coupling at highest-spin site (e.g. thiophene α-α); flags false positives.*

**第 4 步 二聚化热力学**
- 目的 — 聚合引发热力学驱动力;氧化性(E_ox)必要不充分,二聚化把"能成聚合物"与"氧化后分解"区分开。*Driving force; E_ox necessary not sufficient — dimerization separates formers from decomposers.*
- 手段 — B3LYP/6-31G(d,p)/SMD 下算链引发偶联步 ΔG;幻灯片写 2 M⁺ → [M-M]²⁺ + 2H⁺,要求放热,ΔG < −10 kcal/mol 视为强烈有利。*Coupling ΔG; slide reaction 2 M⁺→[M-M]²⁺+2H⁺; ΔG < −10 kcal/mol strongly favorable.*

**⚠️ 改图(两点)**
- (a) 现状 — 二聚化项出库为质子参考、未校准、筛选级/诊断量(src/eps/analysis/plots.py, summary.py);绝对值含公共质子常数偏移,仅 min-max 归一化排序下安全(偏移精确抵消)。应为 — 若展示绝对 ΔG 阈值(−10 kcal/mol),加注"筛选级、质子参考、未校准"。*Proton-referenced, uncalibrated; ranking-safe only under min-max; annotate the −10 threshold.*
- (b) 现状 — 幻灯片写 2 M⁺ → [M-M]²⁺ + 2H⁺(双阳离子产物),多算一次氧化,曾产生一个大的虚假吸热(双阳离子重复计入一次氧化)。应为 — 对齐代码已修正的中性二聚体再芳构化 2 M⁺· → M–M(中性) + 2H⁺(电荷与电子均平衡)。*Dication product double-counts an oxidation → large spurious endotherm; align to corrected neutral-dimer rearomatization.*

**第 5 步 寡聚体带隙收敛**
- 目的 — 聚合物带隙 DFT 参考,作 sTDA-xTB 六聚体带隙的校准锚。*DFT band-gap reference; anchor for sTDA-xTB hexamer.*
- 手段 — TD-B3LYP 或 CAM-B3LYP 沿 n=1–6 算激发,带隙随链长收敛(D-A 约 n=4–6,同聚物约 n=6)。*Excitations n=1–6; converges n≈4–6 (D-A), n≈6 (homopolymer).*
- 为何 CAM-B3LYP — 共轭寡聚体 CT/长程激发在普通杂化下灾难性坍塌(CT 过低,缺长程精确交换);CAM-B3LYP 交换混入随电子间距增大(~19% 短程→65% 长程),恢复 −1/r 渐近交换势,正好治病。*Range-separated; ~19%→65% exchange restores −1/r asymptote, fixes CT collapse.*

**第 6 步 重组能 λ**
- 目的 — 每单体动力学保护描述符。*Per-monomer kinetic-protection descriptor.*
- 手段 — λ ≈ 垂直 IP − 绝热 IP;阳离子从中性几何弛豫到自身平衡几何释放的能量(Marcus 内层重组能)。*λ ≈ vertical IP − adiabatic IP; inner-sphere Marcus.*
- 物理 — Marcus 理论中电子转移速率随 λ 增大而降,大 λ 减慢逆反应/副反应,动力学保护活泼阳离子自由基;取同方法两 IP 之差还抵消大部分共享 xTB 系统误差,故最廉价且物理有意义的把手。*Larger λ slows back/side reactions; same-method difference cancels xTB error.*

**🔑 关键问题(λ 实现状态)**
- 问题 — directive §3.2 要求"使用"λ,但 monomer_lambda_ox_eV / solvent_lambda_ox_eV 已计算并 join,却既不进硬过滤也不进 composite,目前 report-only。*§3.2 wants λ used; currently report-only.*
- 思路 — 诊断显示 λ 与偶联可行性无干净可用信号(可行性翻转由偶联位点位阻/拓扑封堵决定,vertical−adiabatic IP 对此物理盲),且仅有信号方向机制错(封堵基团反降 λ)。*No clean feasibility signal; only signal runs wrong way.*
- 解决 — report-only 是经验证决定:为正当含义(电荷输运/极化子自陷)保留 λ,不误用做可行性过滤;既遵 §3.2"计算并报告 λ",又不把噪声轴塞进排序。*Validated: keep λ for transport meaning, honor §3.2, no noisy axis in ranking.*

**第 7 步 精修过滤**
- 目的 — DFT 级收紧 Tier-1 判据,提高存活者质量。*Tighten Tier-1 criteria at DFT level.*
- 手段 — 窗口裕度从 0.3 V 收紧到 0.5 V(AIP < 溶剂阳极极限 − 0.5 V),用 DFT 量重核所有判据。*Window margin 0.3→0.5 V; re-check all with DFT.*
- 逻辑 — 与 Tier-1 同物理轴,只是更准描述符 + 更严裕度,进一步剔除临界 triad。*Same axes, more accurate + stricter, removes borderline triads.*

**第 8 步 排序**
- 目的 — 对 DFT 精修存活者产出最终排序。*Final ranking of refined survivors.*
- 手段 — 按 §5 composite score(configs/scoring.yaml,各项 min-max 归一化):S = 0.30·window_margin + 0.20·anion_stability + 0.20·solubility + 0.15·dimerization + 0.15·band_gap_deviation,目标带隙 1.8 eV。*Composite S = 0.30/0.20/0.20/0.15/0.15; target gap 1.8 eV.*
- 权重 — 窗口裕度最高(0.30),阴离子稳定性与溶解度各 0.20,二聚化与带隙偏差各 0.15;与"硬过滤靠前三轴、带隙/二聚化只进排序"一致。*Window margin highest; consistent with hard-filter-first-three logic.*

## S5 · General Status (现状总览 / Funnel)

**核心** — 项目"诚实体检表":左勾选项 / 中分节状态表 / 右漏斗须三者一致。*Honest health check — checkmarks, status table, funnel must agree.*

**框架**
- 三层计算高通量筛选;主标尺水相 Ag/AgCl(饱和 KCl)。*3-tier computational HTS; master scale aqueous Ag/AgCl (sat. KCl).*
- **Tier-1** 半经验 xTB 扫全库 → 已实现、试运行跑通。*xTB full-library sweep; implemented, test run done.*
- **Tier-2** DFT(B3LYP/6-31G(d,p)/SMD)精修幸存者 → 进行中(部分精修)。*DFT validation of survivors; partial, in progress.*
- **Tier-3** 可选高精度层 → 计划中。*Optional high-accuracy layer; planned.*

**分节状态表(诚实陈述核心:实现/进行/计划如实标)**
- 已实现:§2 库、§3 性质、§4.1 Tier-1 xTB、§5 综合评分、§8 输出。*Implemented.*
- 进行中:§4.2 Tier-2 DFT、§7 验证。*In progress.*
- 计划中:§4.3 Tier-3 高精度。*Planned.*
- 测试套件 391 项通过(基础设施 + 科学不变量回归)→ 支撑"已实现"非空话。*391 passing tests back the "implemented" claims.*

**读图(逐级走漏斗)**
- **顶端** ~50,000 目标三元组(monomer × solvent × electrolyte ≈ 100×25×20)。*Full-scale target.*
- **试运行** 7,488 = 36 单体 × 13 溶剂 × 16 电解质;50k→7,488 是规模选择,非过滤。*Scale choice, not a filter.*
- "15% retained" 标注实为试运行占目标比例,易误读为保留率。*Label = test-run fraction of target, not retention.*
- **Tier-1 过滤** 7,488 → 幸存者;三条硬过滤(configs/tier1.yaml)。*Three hard filters.*
- 窗口裕度 > 0.3 V — 单体氧化电位须低于溶剂阳极极限 0.3 V,否则溶剂先分解。*Window margin; else solvent decomposes first.*
- 阴离子稳定裕度 > 0.2 V — 阴离子氧化电位须高于单体 0.2 V,否则电解质先氧化。*Anion margin; else electrolyte oxidizes first.*
- 溶剂化自由能 < -3.0 kcal/mol — 单体须足够可溶。*Solubility floor.*
- 带隙、二聚化非硬过滤,仅进排序/报告。*Band gap & dimerization → ranking only.*
- 筛掉大半因电化学窗口约束(权重最高 0.30)严苛。*Cut >half; window constraint dominant (w=0.30).*
- **底端** 40 个短名单送 CV([2% retained]):是实验吞吐量约束,非科学截断;从综合评分排序后人工挑选。*40 = bench-throughput limit, not a cutoff.*
- 综合评分(configs/scoring.yaml):S = 0.30·window_margin + 0.20·anion_stability + 0.20·solubility + 0.15·dimerization + 0.15·band_gap_deviation;target_gap 1.8 eV;全部 min-max 归一化。*Composite score formula.*

**口头补充** — dimerization 描述符为 screening-grade、质子参考、未校准,且 dication 双重计入一次氧化会产生一个很大的虚假吸热,勿当定量值。*Say aloud: dimerization term uncalibrated; dication double-counts an oxidation → large spurious endotherm.*

**⚠️ 改图 — Tier-1 幸存者数字过时(STALE)**
- 现状:漏斗显示 2,718 幸存 / [36% retained],是过时 strict 标定。*Stale strict number.*
- 应为:3,275 幸存 / 43.7%(3,275/7,488);源 outputs/tier1_relaxed/survivors.csv,与 §9 一致。*Update to relaxed run.*
- 加脚注:标定 2026-06-29 由 strict(2,718,LOO 0.246 V)切换至 relaxed(3,275,LOO 0.198 V),per directive §7;slope 0.7304 / intercept 0.0929。*Calibration switch footnote.*

**⚠️ 改图 — Tier-2 数字基于过时基数**
- 现状:2,354 / [87% retained] 均由 stale 2,718 反推(0.87×2,718≈2,365≈2,354),两数失效。*Both back-computed from stale base.*
- 应为:锚定新基数 3,275,本级标"部分精修(进行中)",不写会被误读为最终幸存数的单一数字。*Anchor 3,275; label "partial (in progress)".*
- 脚注给已精修计数 1,610 折叠行(outputs/tier1_relaxed/tier2_refined_partial.csv,全 tier2_dft_pending=False),不给折算百分比;绝不保留任何从 2,718 推出的数。*Footnote refined-so-far 1,610; no fabricated %.*

**⚠️ 改图 — 勾选项 "Benchmark 29 Peak" 对齐 §7**
- 现状:"Benchmark 29 Peak Eox(monomer)",易与 §7 的 n=30/29 显冲突。*Looks contradictory vs slide 7.*
- 应为:"Benchmark: 30 peak anchors / 29 LOO-CV groups";30 锚点与 n=29 LOO-CV 是同一数据集两视角(重复测量折叠成 29 组,留一法)。*Same dataset, two views; match §7 parity (n=30) & MAE (n=29).*

**⚠️ 改图 — 勾选项 "IPEA-xTB Calibration finished" 措辞过宽**
- 现状:单一勾"IPEA-xTB Calibration finished",与 §6 的 n=15 部分 xTB→DFT 标定打架。*Too broad; clashes with slide 6.*
- 应为:拆两条 —(1)实验锚定线(production: agagcl_peak_relaxed,n=30/29,IPEA-xTB)已完成;(2)directive §7 step-1 xTB→DFT 标定(calibration of record)仍部分,n=15(ORCA SGE 418096:小分子核心已完,大 donor-acceptor 仍在算)。*Split: experiment-anchored done; xTB→DFT partial (n=15).*

**🔑 关键问题 — freeze-then-scale 与 scale_guard:为什么 50k 全规模被刻意闸住**
- 问题 — 缓存按每物种/每方法组织,改任一方法即令该性质整缓存失效;方法未冻结就触发 50k harvest + 全量 Tier-2 DFT,会把数百至上千 CPU-hr 押在可能即改的方法上,不可逆浪费。*Per-method cache; premature launch wastes 100s–1000s CPU-hr.*
- 思路 — directive §2 与 AGENTS.md 均规定 freeze-then-scale:先冻结每方法,再提交全规模 harvest;把"全规模"做成显式闸门。*Mandate: freeze every method first; gate full scale.*
- 解决 — scale_guard(commit 6aca1be):eps run-tier1 在三元组超 scale_guard.max_triads(默认 12,000;当前 7,488)抛 ScaleGuardError,除非 --allow-large-scale;tier2-plan 超 500 任务同样拦截。*Explicit safety gate; needs flag to override.*
- 即漏斗顶端 50k→7,488 的真实机制:非科学过滤而是有意安全闸,保证全规模发射仅在方法冻结签字 + 显式 flag 后发生;已在运维中救场,锁住试运行规模。*Real mechanism behind top step; already proven operationally.*

## S6 · Tier-1 xTB Calibration (IPEA-xTB → DFT)
**核心** — 第七节 Step-1 "校准记录线";纯计算问题:xTB Eox 如何映射到 B3LYP/6-31G(d,p)/SMD Eox。*Directive §7 Step-1 "calibration of record"; pure-compute map xTB Eox → DFT Eox.*
**拟合** — dft_Eox = 0.7675·xtb_Eox − 0.5789,R² 0.88,MAE 0.12 V,n=15。*Fit coeffs; R² 0.88, MAE 0.12 V, n=15.*
**为何最干净** — 两轴都是计算量,无参考电极噪声/液接电位/动力学不可逆位移 → 检验 xTB 系统误差结构最干净的尺子。*Both axes computed; no electrode/junction/kinetic noise — cleanest ruler for xTB error structure.*
**斜率与截距的物理含义(非拟合偶然)**
- **斜率 0.767 < 1** — xTB 前线轨道谱相对 B3LYP 过窄,IP 响应被放大,故乘 <1 因子压回。*Compressed frontier spectrum exaggerates IP response; <1 scales back.*
- **截距 −0.579 V** — 吸收两层级绝对能量原点固定差(缺失精确交换 + 经验 IPEA 常数偏置)。*Absorbs fixed absolute-origin diff: missing exact exchange + IPEA bias.*
- **"为何线性就够"** — xTB 丢的物理对某化学类别是近似恒定标度+偏移,非随机噪声 → 仿射拟合吸收系统误差,残差 MAE 0.12 V 即不可约随机部分。*Dropped physics ≈ constant scale+offset per chemistry → affine fit absorbs systematic; 0.12 V is irreducible.*
**诚实补充** — n=15 是部分数据:仅小核心单体(单环/小杂环);大型 D-A 单体(α-六联噻吩、D-A 共聚、DPP)仍在 ORCA 计算(SGE 418096,15/37 完成)。R²/MAE 来自化学多样性受限子集,大分子补齐后系数可能移动 → 存为记录线,不启用为生产线。*n=15 partial — small-core only; large D-A pending (SGE 418096, 15/37 done); coeffs may shift; kept as record, not production.*
**侧栏** — "TD-DFT not ready for sTDA-xTB" 仅中性状态:光学通道校准未就绪,光学轴作诊断/未校准量;不影响此 Eox 线。*Side note neutral: optical calibration pending, optical axis diagnostic; no bearing on Eox line.*
**⚠️ 改图** — 现状 "n=15 partial" → 应为 "n=15 partial(小核心单体;大型 D-A 单体待 SGE 418096 完成)"。*Expand caption so partial-result status is obvious.*

## S7 · Tier-1 xTB Validation (parity + three MAE legs)
**核心** — 左奇偶图:校准后 xTB Eox vs 实验,n=30 锚点,±0.3 V 容差带 = Tier-1 目标精度(< 0.30 V),带内即筛选级合格。右三柱 MAE 讲两阶段校准链的核心科学故事。*Left parity: calibrated xTB vs exp, n=30, ±0.3 V band = Tier-1 target; right 3 MAE bars carry the story.*
**三根 MAE 柱**
- **① xTB→exp 直接** — LOO-CV MAE 0.198 V(n=29 留一);已达 Tier-1,生产实际启用的实验尺度线(slope 0.7304,intercept 0.0929)。*Direct route, LOO-CV 0.198 V (n=29); active production line 0.7304/0.0929.*
- **② DFT→exp 原始** — MAE 0.496 V(n=10);DFT 看似更差,正是要点:绝对 Eox 带约 0.5 V 系统参考偏移(连续溶剂化偏置 + ΔSCF 绝对原点 + 参考电极换算的固定常数)。*Raw 0.496 V (n=10); worse on purpose — ~0.5 V fixed reference offset.*
- **③ DFT→exp 线性校** — 吸收固定偏移,残差降至 0.151 V。*Linear fit absorbs offset → 0.151 V.*
- **结论** — DFT "误差"几乎全是可被一条线移除的系统偏移,非随机散布;xTB 经实验锚定本就直接达标。*DFT error ≈ line-removable offset; xTB passes directly once anchored.*
**诚实补充(已近物理下限)** — 此校准为筛选级;氧化电位诚实精度区间 0.20–0.35 V。限制非模型质量,而是计算量(热力学单电子 E1/2)与基准量(动力学、不可逆 Epa/onset,叠加自由基跟随化学、吸附、成核位移)的根本类型错配 + 液接/参考噪声 → 约 0.15 V 硬下限。0.198 V 已踩地板;指令 Tier-2 < 0.15 V 实际在此类预测物理下限之下。*Screening-grade, near floor; honest band 0.20–0.35 V; type mismatch (computed E1/2 vs kinetic Epa) + junction noise → ~0.15 V floor; Tier-2 < 0.15 V is below it.*
**🔑 关键问题(§7 两阶段公案)**
- 问题 → 把原始 xTB→DFT 线直接对实验伏特尺度的电位窗口闸门做判定(跨尺度:校准线在 DFT 尺度,闸门在实验尺度,隔约 0.5 V DFT 偏移)。*Applied raw xTB→DFT line against an exp-volt window gate — cross-scale by ~0.5 V.*
- 后果 → 幸存者从 3,275 膨胀到 4,211,§7 判定从 PASS 翻 FAIL。*Survivors 3,275 → 4,211; verdict PASS → FAIL.*
- 思路 → 分开两个角色:窗口闸门活在实验伏特,过滤器必须用实验尺度电位;xTB→DFT 线仅作记录。*Separate roles: filter on experimental scale; xTB→DFT line as record only.*
- 解决 → 生产过滤器留在实验尺度线(0.7304/0.0929);xTB→DFT 线存为记录(enabled=false)。组合链 xTB→DFT→exp 得 0.648/0.116,与生效线 0.730/0.093 在约 0.1 V 内吻合 → 交叉验证同一物理。*Filter 0.7304/0.0929; record enabled=false; composed 0.648/0.116 ≈ active 0.730/0.093 within ~0.1 V — cross-validated.*
**🔑 关键问题(基准 strict n=9 → relaxed n=30)**
- 问题 → 早先用严格基准(仅 tier-A 纯净峰电位,n=9);n=9 太薄,样本内→LOO-CV MAE 跳 +37%,拟合过度依赖少数点。*Strict n=9 too thin; in-sample→LOO-CV jumped +37%.*
- 思路 → 决策用 LOO-CV(泛化误差,非样本内拟合优度)。*Decide on LOO-CV generalization, not in-sample fit.*
- 解决 → 放宽集(30 峰)LOO-CV 0.198 V 优于严格集 0.246 V,故切换。R² 降至 0.559,但 R² 跨不同 n/样本范围不可比,降的是更宽电位范围+更杂标签,非泛化能力;以 LOO-CV MAE 而非 R² 决策正为避免被误导。*Relaxed LOO-CV 0.198 V beats strict 0.246 V; R² 0.559 not comparable across n; decided on LOO-CV to avoid being misled.*
**⚠️ 改图** — 现状 "n=30 anchors" 与 "LOO-CV (n=29)" 看似冲突 → 应为 "n=30 anchors; LOO-CV holds out each, fits on the other 29"(基准 30 行,留一拟合余 29,n_groups=29)。*Reconcile: 30 rows, hold out one, fit on 29.*

## S8 · Tier-1 Descriptors: Where the Filters Bite / 描述符分布:过滤器在哪里"咬合"
**核心** — 把硬过滤器从抽象阈值变成可见物理分布;左侧2个直方图=三条硬约束中的两条的真实描述符轴。*Turns hard filters into visible physical distributions; 2 left histograms = real axes for 2 of 3 Tier-1 constraints.*
**方法(描述符 → 阈值 → 权重)**
- **`window_margin_V`** — 电化学窗口余量 = 溶剂阳极极限 − 单体校准氧化电位;硬阈值 > 0.3 V(`configs/tier1.yaml`);复合评分权重最高 0.30。*Window margin = anodic limit − calibrated monomer E_ox; cut > 0.3 V; heaviest weight 0.30.*
- **`anion_stability_margin_V`** — 阴离子稳定性余量;硬阈值 > 0.2 V;权重 0.20。*Anion-stability margin; cut > 0.2 V; weight 0.20.*
- **代数关键** — 两个余量都是两个氧化电位之差 → 单体校准截距在差值中**精确抵消** → 判定由原始 IP 之差驱动,对外推稳健;这才让阴离子过滤器"活"起来。*Both margins are differences of two E_ox → calibration intercept cancels exactly → governed by raw IP diff, extrapolation-robust → makes anion filter live.*
**读图(左:直方图)**
- 看阈值"咬合"在何处:落在 0.3 V / 0.2 V 左侧的尾部 = 被该约束淘汰的三元组。*Read where threshold bites; left-tail past cut = eliminated triads.*
- 阴离子余量双峰 = 单体分两类:E_ox 远低于配对阴离子(安全,高余量峰)vs E_ox 逼近/超过阴离子(有共氧化风险,低余量峰贴/越阈值);双峰是"单体—阴离子氧化竞争"的指纹,非噪声。*Bimodality = two monomer populations (anion safe vs co-oxidation risk); fingerprint of monomer–anion oxidation competition, not noise.*
- 阴离子绝对校准值=筛选级外推(线仅拟合单体数据),但差值用法、截距抵消 → 排序稳健。*Absolute anion values are screening-grade extrapolation, but difference cancels intercept → ranking robust.*
**读图(右:ΔGsolv 热图)**
- openCOSMO-RS ΔGsolv 热图,覆盖 468 个单体×溶剂对;σ-profile 由 ORCA 6.1 算、按物种解耦。第三条硬约束 ΔGsolv < −3.0 kcal/mol 读在此图;越负(越深)=溶剂化越有利=越可溶。*468 monomer×solvent pairs, ORCA 6.1 σ-profiles, per-species decoupled; 3rd cut ΔGsolv < −3.0 kcal/mol; darker = more soluble.*
- 分区:极性非质子(如乙腈类)×极性/可极化单体 → 强负 → 可溶区;高度非极性单体×低介电溶剂 → 弱负/近阈值 → 不可溶被淘汰。*Polar aprotic × polar monomer → strongly negative, soluble; nonpolar × low-dielectric → near-threshold, cut.*
- COSMO-RS 经 σ-profile 成对表面段相互作用(含氢键)解析**特定**溶质—溶剂相互作用,优于单一介电连续模型(SMD/ALPB) → 正是逐(单体×溶剂)可溶性硬约束所需。*Resolves specific solute–solvent surface-segment interactions (incl. H-bonding) vs single-dielectric SMD/ALPB; right tool for per-pair solubility.*
**🔑 关键问题 — COSMO-RS 解耦:560 → 44 CPU-小时**
- 问题 → 天真逐对算 ΔGsolv 要每个单体×溶剂各跑一次 DFT σ-profile;仅 30 大单体 × 25 溶剂 × 45 min ≈ **560 CPU-小时**,超 Tier-1 预算,不可行。*Naive: one DFT σ-profile per pair; 30 large × 25 solvents × 45 min ≈ 560 CPU-hr, infeasible.*
- 思路 → 相互作用能是两个 σ-profile 的成对泛函,单分子的 p(σ) 与配对对象无关 → σ-profile 算一次复用,成本 O(单体×溶剂) → O(单体+溶剂)。*Pairwise functional of two σ-profiles; molecule's p(σ) pairing-independent → compute once, reuse; O(M×S)→O(M+S).*
- 解决 → 按物种解耦:每分子一次(~30 大单体 45 min + ~100 中小单体 ~10 min + 25 溶剂)≈ **44 CPU-小时,一次性、可尴尬并行**,落在 §9 Tier-1 预算内;每对 ΔGsolv 仅毫秒级无-DFT 统计积分。约 **13×** 节省。*Decoupled: ~44 CPU-hr one-time, embarrassingly parallel; per-pair = ms no-DFT integration; ~13× saving.*
- 逐位验证 → 噻吩 σ-profile(run f9776utv)+ 另一次运行(fuws58nq)的 MeCN profile,精确复现同次 ΔGsolv **−4.132111549377441 kcal/mol**。*Validated to the digit: thiophene (f9776utv) + cross-run MeCN (fuws58nq) reproduces −4.132111549377441 kcal/mol.*

## S9 · Tier-1 Outputs: The Pareto Front and the Chemical-Space Map / Tier-1 产出:Pareto 前沿与化学空间图
**核心** — Tier-1 产出层:**7,488** 三元组 → **3,275** 通过全部三条硬过滤器(IPEA-xTB + openCOSMO-RS)→ 其中 **57** 个 Pareto 最优。*Output layer: 7,488 triads → 3,275 survivors → 57 Pareto-optimal.*
**读图(左:Pareto 前沿)**
- 左图画窗口余量 vs 可溶性的 Pareto 前沿(2D 平面)。*Left: window margin vs solubility, 2D plane.*
- 真前沿是**五维**(window、anion、solubility、dimerization、band-gap deviation),57 点在 5D 中互不支配。*True front is 5D; 57 points mutually non-dominated in 5D.*
- 投影到所画两轴时仅 ~6 点落右上沿 —— 不代表前沿只有 6 点,也非错误点;它们是两轴上恰好非支配的二维可见子集,其余 51 点在另三维非支配、被"压"入前沿内侧。*Only ~6 on upper-right edge of 2D projection ≠ front of 6, not errors; other 51 non-dominated in other 3 dims, pushed inside.*
- 尺寸混淆(诚实声明):可溶性代理随分子尺寸系统性变化,如 dimerization ΔG 与重原子数相关 r=0.67 → "更右上更优"偏向更大分子 → 勿当单坐标纯化学偏好,尺寸是潜在共变量;筛选级诚实边界,下游推荐须披露。*Size-confounding: solubility proxy varies with size (cf. dimerization ΔG r=0.67) → upper-right biased to larger; size a latent covariate, disclose downstream.*
**读图(右:t-SNE 化学空间)**
- t-SNE 化学空间图(perplexity=30),按 `passes_all_tier1_filters`(True/False)着色;聚类=单体家族(噻吩系、咔唑系、吡咯系)。*t-SNE map (perplexity=30) colored by passes_all_tier1_filters; clusters = monomer families.*
- 关键读图=True/False 的**分布**:幸存者散布多个家族,非局限单簇 → 硬约束不偏袒某类化学,而在每家族内按窗口/阴离子/可溶性筛可行成员 → 下游化学多样性好信号,清单不被单一母核垄断。*Survivors spread across families, not one cluster → constraints don't favor one chemistry; good diversity signal, no single-scaffold monopoly.*
**⚠️ 改图 — Pareto 标注与解耦致谢**
- 现状 → Pareto 图无维度标注,易把"只见 ~6 点"误判为绘图错误。应为 → 加听众向标注:"Pareto 最优 n=57(五维前沿:window_margin、anion_stability、solubility、dimerization、band_gap_deviation);所示 2D 投影仅 ~6 点支配上沿,完整 5D 请用交互工具检视。"*Now: no dimensionality label → ~6 points misread as plot error. Should: annotate n=57, 5D front list, inspect full 5D interactively.*
- 现状 → 幸存者占比 **3,275 / 7,488 = 43.7%**,与 Slide 3 标注"保留 ~10–20%"矛盾。应为 → 本页注明放松校准下实测保留率 43.7%,以免前后矛盾。*Now: 43.7% survivor fraction contradicts Slide 3 "~10–20% retained." Should: note measured 43.7% under relaxed calibration.*

## S10 · Questions / 问题与讨论

**优化后的幻灯片要点 / Slide bullets**
> **Open questions for the group**
> 1. **DFT ~0.5 V 系统性偏移** — 参考偏移还是真系统误差?线性 DFT→exp 修正,还是热力学循环参考?*Reference convention or systematic error? Linear DFT→exp fix vs thermodynamic-cycle reference.*
> 2. **干净的 Eox 实验锚点来源** — 优先非水 MeCN 一次 CV(vs Fc/Fc⁺),固定常数转 Ag/AgCl。*Primary MeCN CV vs Fc/Fc⁺, pinned-constant convert to Ag/AgCl.*
> 3. **Tier-2 < 0.15 V 低于 ~0.20-0.35 V 物理下限** — 改为筛选级目标,还是留作长期目标?*Below the physical floor — re-define screening-grade?*
> 4. **验证不达标怎么办** — 同时校准两级(xTB→DFT + DFT→exp),还是放宽接受带宽?*Calibrate both tiers vs widen accepted band.*
> 5. **参考/锚点约定标准化** — 全库统一 Ag/AgCl(sat. KCl)主标尺 + P&A 固定转换常数?*Library-wide Ag/AgCl master scale + pinned P&A constants.*
> 6. **交付物定义与资源排序** — 排序数据库 vs 每物种描述符表?Tier-2 全量 DFT 如何排期?*Ranked DB vs per-species descriptor table; sequence full Tier-2 spend.*

**核心** — 公开摆出关键方法学不确定性,带候选答案征求 PI/组里决策,非空抛问题。*Surface open uncertainties with answer-paths, not bare questions.*

**🔑 关键问题（每条:为何重要 → 答案路径）**
- **Q1 DFT 偏移** — 问题:~0.5 V 是参考还是误差。思路:原始 DFT→exp MAE 0.496(n=10),线性拟合后残差 0.151 → 几乎全系统性。解决:倾向线性吸收(已验证),备选热力学循环(SHE 4.28 V + Ag/AgCl −0.197 V);组合链 xTB→DFT→exp 0.648/0.116 与实验标尺线 0.730/0.093 ~0.1 V 内吻合,两级交叉验证。*Offset is reference-type (intercept-absorbed); chains cross-validate within ~0.1 V.*
- **Q2 锚点来源** — 问题:链质量上限取决于锚点纯度,现基准 n=29/30 偏大分子,对单环单体域外推。思路:干净非水单体 CV 多以 Fc/Fc⁺ 报告。解决:P&A 2000 固定常数 +0.445(仅 MeCN)转主标尺;非 MeCN 标注 ~0.05-0.15 V 液接误差。*Anchor purity caps the chain; convert MeCN CV via pinned +0.445.*
- **Q3 Tier-2 目标** — 问题:< 0.15 V 在/低于物理下限。思路:下限 0.20-0.35 V = 电势类型不匹配(热力学 E1/2 vs 动力学 Epa/onset，~0.15-0.35 V) ⊕ 液接/参考噪声 0.05-0.15 V,正交求和定 ~0.15 V 硬底。解决:重定义为筛选级,报 LOO-CV MAE 并标筛选级精度。*Floor independent of calibration; relabel screening-grade.*
- **Q4 验证不达标** — 问题:验收门可能触不到。思路:决策分叉。解决:优先(a)两级分别校准——xTB→DFT 0.767/−0.579,R² 0.88,MAE 0.12 V,n=15 部分 + DFT→exp 0.151 V;残差仍触底再走(b)放宽带宽到 0.20-0.35 V。*Two-stage calibration first; widen band only if residual hits floor.*
- **Q5 约定标准化** — 问题:标尺不统一从根上污染窗口滤波器(单体 Eox vs 溶剂阳极极限须同标尺)。思路:钉死主标尺。解决:全库 Ag/AgCl(sat. KCl)+ P&A 常数(SCE +0.045、Fc/Fc⁺ +0.445 MeCN、SHE −0.197),peak 与 onset 独立列、永不混拟。*Pin one master scale; never co-fit peak and onset.*
- **Q6 交付物 + 资源** — 问题:主交付物未定 + 全量算力排期。思路:§8 同列排序数据库与描述符/Pareto/shortlist。解决:每物种描述符表为主资产(下游 ML 能重学权重、学不到缺失数据),复合排序作诊断;7,488 → ~50,000 全量 + 全量 Tier-2 是真算力问题(Lop ~320 核),需 PI 拍板花费/顺序,scale_guard 把关先冻结再扩量。*Descriptor table = durable asset; ranking = diagnostic; freeze-then-scale the spend.*

---

## S11 · Next Steps / 下一步计划

**优化后的幻灯片要点 / Slide bullets**
> **Next steps (sequenced by leverage and dependency)**
> 1. **先精修/扩充 Eox 基准** — 杠杆最高的根基修复;锚点向单环目标单体再平衡,补干净 MeCN 数据。门控所有下游校准。*Highest-leverage foundation fix; gates every downstream calibration.*
> 2. **跑完 ORCA xTB→DFT 后重拟** — 补齐待算大 D-A 单体(SGE 418096,现 n=15/37),重拟校准记录线。依赖步骤 1 锚点集。*Finish pending large D-A monomers, refit calibration of record.*
> 3. **分析 Tier-2 测试批次,关闭 §7 验证** — 收割进行中 Tier-2,完成 DFT→exp 验证,对照物理下限如实报告。依赖步骤 2 DFT 线。*Harvest Tier-2, close DFT→exp validation against the honest floor.*
> 4. **光学带隙对 TD-DFT 校准** — 按类锚点让 sTDA-xTB 光学轴从诊断级毕业。并行任务,不在 Eox 关键路径。*Graduate optical axis; parallel, off critical path.*
> 5. **冻结方法,scale_guard 把关下扩量** — 先冻结硬约束方法,再启 ~50,000 三元组 + 全量 Tier-2。由步骤 1-3 门控。*Freeze hard-constraint methods, then scale.*

**核心** — 四条简略要点改写成有序、有依赖的计划,排序原则=杠杆+依赖:先修最底层根基,逐级向上,最后冻结扩量。*Sequenced by leverage + dependency, not a wish list.*

**逐步（每条:理由 → 依赖）**
- **① 精修/扩充 Eox 基准** — 现 Tier-1 Eox 校准是已知薄弱根基(R² 0.56,在 ~0.2 V 物理下限,现行实验锚定而 §7 指定 xTB→DFT),基准偏大分子、对单环单体域外推;纯度/覆盖封顶每条下游线 → 必须先做,门控全部校准。*Weak foundation caps everything; do first.*
- **② 跑完 ORCA xTB→DFT 再重拟** — 记录线 0.767/−0.579,R² 0.88,MAE 0.12 V 现仅 n=15 部分(小分子核心已完,大 D-A 在 SGE 418096 算 15/37);补齐后重拟覆盖目标化学空间。依赖步骤 1 锚点集。*Refit after large monomers land; depends on step 1.*
- **③ 分析 Tier-2,关闭 §7 验证** — Tier-2 测试批次 in progress;收割完成两级链第二段 DFT→exp。纪律=诚实,对照 0.20-0.35 V 物理下限报告,勿当 < 0.15 V 真值。依赖步骤 2 DFT 线。*Harvest completes stage-2; report against floor; depends on step 2.*
- **④ 光学带隙对 TD-DFT 校准** — sTDA-xTB 光学轴现筛选级/诊断级、未校准;毕业靠每类 ≥3 实验锚点的策展,非算力;TD-DFT 尚未就绪,暂留诊断级,与 Eox 主线解耦。并行,不在关键路径。*Needs ≥3 anchors/class curation, not compute; decoupled parallel track.*
- **⑤ 冻结方法后 scale_guard 扩量** — freeze-then-scale 是 §2 硬规则(改任一方法即让该属性整缓存失效),扩到 ~50,000 全量 + 全量 Tier-2 前须先冻结硬约束方法(Eox 校准、ESW 门、阴离子氧化、构象/几何);run-tier1 >12,000 三元组经 scale_guard 拦下(除非 --allow-large-scale),防冻结签字前误启全量。由步骤 1-3 门控。*Freeze before scale; scale_guard blocks >12,000 triads; gated by 1-3.*

**⚠️ 改图** — 现状:原四条要点(Refine benchmark / Optical gap calibration / Analyze test Run Tier-2 / Prepare for scale-up)无依赖结构,读如可并行愿望清单。应为:按杠杆+依赖重排,显式标注门控关系(尤其 freeze-before-scale),呈现为深思熟虑的序列。*Original bullets carry no dependency structure; reorder + annotate gating.*