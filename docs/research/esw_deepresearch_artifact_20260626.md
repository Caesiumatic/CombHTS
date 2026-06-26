# 电化学稳定窗口(ESW)一手文献数据整理：NMP、THF、Sulfolane(用于电聚合计算筛选基准)

## TL;DR
- **THF 是三种溶剂中唯一打通了通往水相 Ag/AgCl 换算路径的溶剂**：Connelly & Geiger (Chem. Rev. 1996, DOI 10.1021/cr940053x) Table 1 给出 Fc/Fc⁺ 在 THF 中相对 SCE 的电位(0.1 M [NBu₄][PF₆]=0.56 V；0.1 M [NEt₄][PF₆]=0.53 V)；经 SCE→Ag/AgCl(+0.045 V，Pavlishchuk & Addison 2000)可得 Fc/Fc⁺ ≈ +0.605 / +0.575 V vs Ag/AgCl。但该值源自二手汇编,其一手测定可回溯至 Shalev & Evans 对 THF/100 mM TBAPF₆ 体系的参比测定——定稿前应核对该一手原文。
- **NMP 与 Sulfolane 的缺口依旧成立**：未找到任何在这两种溶剂中、以四烷基铵为支持电解质、在玻碳/铂上、相对 SCE/SHE/真实水相 Ag/AgCl 的可换算溶剂窗口一手行。现有数据要么是全电池电压(vs Li/Li⁺,属两电极电池电压,不可用作门控),要么相对 Fc/Fc⁺ 或裸银赝参比,均不可换算。
- 最有价值的待办是直接获取三篇已确认存在、但本次不可访问的一手原文(Coetzee & Simon 1972、Armstrong 等 1976、Izutsu/Mann 表),以填补 sulfolane 的窗口值与 Fc 偏移；在取得原始数值之前,这些行严格保持 NOT FOUND,绝不臆造。

## Key Findings
1. **THF 的 Fc/Fc⁺ vs SCE 偏移已定位**(Connelly & Geiger 1996,DOI 10.1021/cr940053x,Table 1)。这是本任务最有价值的换算常数发现,使 THF 由"不可换算"转为"有条件可换算"。Table 1 标题经核实为 "Formal Potentials (V) for the Ferrocene⁺¹/⁰ Couple vs SCE in Selected Electrolytes"。
2. **该 THF Fc 值的一手出处可回溯**：据 IntechOpen 章节 "Effects of Electrolyte on Redox Potentials" 明确陈述 "Here we applied Connelly and Geiger's finding that Fc(THF, TBAPF6) is 0.56 V vs. SCE… Our measurements… used the determinations of Shalev and Evans to reference our measurements to Fc in THF with 100 mM TBAPF6." 即原始测定可追溯至 Shalev & Evans。
3. **La Pierre 等 (Inorg. Chem. 2026,DOI 10.1021/acs.inorgchem.5c05041) 已确认存在**,题为 "A Guide to Nonaqueous Electrochemistry of f-Element Complexes",65(7), 3758–3770。其 THF 溶剂窗口与 Fc/Fc⁺ 数据均相对**裸银 Ag⁰ 丝赝参比**(fritted bare Ag⁰ wire),Fc/Fc⁺ 在这些体系中相对 Ag⁺/⁰ 漂移于 +0.76 至 +1.26 V——本质不可换算,与任务陈述一致。
4. **Sulfolane 一手电压窗口的最佳候选**为 Coetzee & Simon (Anal. Chem. 1972, 44(7), 1129–1133, DOI 10.1021/ac60315a012, "Voltammetry in methanol, ethanol, and sulfolane as solvents"),但具体阳极/阴极限值未能从原文提取,标记 NOT FOUND(可访问性问题,非不存在)。
5. **Sulfolane 中 Fc/Fc⁺ 的一手研究**为 Armstrong, Quinn & Vanderborgh, "Heterogeneous charge transfer rates of the ferrocene oxidation in sulfolane," J. Electrochem. Soc. 1976, 123, 646–649,但半波电位数值未能提取,标记 NOT FOUND。
6. **NMP 未找到任何符合条件的一手溶剂窗口行**,也未找到 NMP 中的 Fc/Fc⁺ vs SCE/Ag-AgCl 内标交叉标定。现有 NMP 数据均为 Li-空气/Li 电池(vs Li/Li⁺)。
7. **Izutsu/Mann 汇编的 Pt 溶剂窗口表(被 ALS-Japan 技术资料复制)明确以 vs Fc/Fc⁺ 为基准**:其原文为 "Table 8 Limits of measurable potentials of Pt in various solvents (V vs. Fc/Fc⁺) … The supporting electrolyte type at a current density of 10 µA/mm² is shown in parentheses."。因此,即便取出该表中 NMP/sulfolane 的数值,仍须先有这两种溶剂中的 Fc 内标偏移才能换算——而该偏移在 NMP/sulfolane 中均 NOT FOUND。

## Deliverable A — 一手 ESW 行(CSV)

```
solvent,anodic_limit_V,cathodic_limit_V,native_reference,supporting_electrolyte,working_electrode,cutoff_criterion,source_DOI,exact_locator,verbatim_quote,confidence,converted_to_Ag/AgCl
THF,unconvertible (reported vs Fc/Fc+ on bare Ag),unconvertible,"bare Ag0 wire pseudo-reference (fritted, in electrolyte)","0.1 M TBABPh4; also 0.1 M TBAPF6 (0.10 M)","glassy carbon 3 mm; CE Pt wire 0.5 mm",practical CV edge at 200 mV/s (NOT a current-density window),10.1021/acs.inorgchem.5c05041,"Table 1 / Fig. 1 / Table S1","\"WE: GC, 3 mm; RE: bare Ag0 wire, fritted, in electrolyte solution; CE: Pt wire, 0.5 mm. Scan rate: 200 mV/s ... the potential of the ferrocene Fc+/0 couple ranges from +0.76 V to +1.26 V vs Ag+/0 in these systems\"",high (for ref-type)/NA (value),BLANK — unconvertible (bare-Ag pseudo-ref; no in-solvent Fc-vs-Ag/AgCl tie in this paper)
Sulfolane,NOT FOUND (value not extractable),NOT FOUND,"likely aqueous SCE (Coetzee–Simon convention, UNCONFIRMED)",not extracted,Pt (voltammetry),not extracted,10.1021/ac60315a012,"Coetzee & Simon, Anal. Chem. 1972, 44(7), 1129–1133 — useful-potential-range table","NOT EXTRACTED (primary paper confirmed real but inaccessible)",low,BLANK — value NOT FOUND
NMP,NOT FOUND,NOT FOUND,NA,NA,NA,NA,NA,NA,NA,BLANK — no qualifying primary three-electrode solvent window located
```

注:Izutsu/Mann Table 8(Pt,vs Fc/Fc⁺,10 µA/mm²)被确认为含 NMP 与 sulfolane 行的汇编来源,但本次未能取出 NMP/sulfolane 具体阳极/阴极限值(表格页不可访问),故未列入上表;即便取得,其基准为 vs Fc/Fc⁺,仍需对应溶剂的 Fc 偏移才能换算(见 Deliverable B)。

## Deliverable B — 换算常数(CSV)

```
solvent,couple,offset_value_V,reference_scale,conditions,primary_or_compilation,source_DOI,exact_locator,verbatim_quote,confidence
THF,Fc/Fc+,0.56,vs aqueous SCE,"0.1 M [NBu4][PF6], 25 °C",compilation (lead; traces to Shalev & Evans / Geiger lab),10.1021/cr940053x,"Table 1 'Formal Potentials (V) for the Ferrocene+1/0 Couple vs SCE in Selected Electrolytes'","\"THF 0.56 [NBu4][PF6] ... 0.53 [NEt4][PF6]\"",medium
THF,Fc/Fc+,0.53,vs aqueous SCE,"0.1 M [NEt4][PF6], 25 °C",compilation (lead),10.1021/cr940053x,"Table 1","\"THF ... 0.53\"",medium
THF,Fc/Fc+,+0.605 (derived = 0.56 + 0.045),vs aqueous Ag/AgCl (sat. KCl),"derived via SCE→Ag/AgCl +0.045 V; 0.1 M NBu4PF6",derived from compilation,10.1021/cr940053x + 10.1016/S0020-1693(99)00407-7,"Table 1 + allowed constant","derived value",medium/low
SCE→Ag/AgCl,conversion constant,+0.045,SCE to aqueous Ag/AgCl (sat. KCl),"25 °C; per task-allowed constant",primary,10.1016/S0020-1693(99)00407-7,"Pavlishchuk & Addison, Inorg. Chim. Acta 2000, 298(1), 97–102 (NB: Corrigendum 2024, Inorg. Chim. Acta 578, 122468, DOI 10.1016/j.ica.2024.122468 — verify before finalizing)","conversion constant per task spec",high
Sulfolane,Fc/Fc+,NOT FOUND (value not extractable),—,"Armstrong et al. studied Fc oxidation in sulfolane (primary)",primary (value not extracted),"J. Electrochem. Soc. 1976, 123, 646–649 (no DOI extracted)","Armstrong, Quinn & Vanderborgh 1976, 'Heterogeneous charge transfer rates of the ferrocene oxidation in sulfolane'","NOT EXTRACTED",low
NMP,Fc/Fc+,NOT FOUND,—,—,—,—,—,—,—
Sulfolane,Li/Li+,NOT FOUND,—,—,—,—,—,—,—
```

## Details

### THF（有条件可换算）
Connelly & Geiger 的 Chem. Rev. 1996 综述 Table 1 明确列出 THF 中 Fc/Fc⁺ 相对水相 SCE 的电位:0.1 M [NBu₄][PF₆] 为 **0.56 V**,0.1 M [NEt₄][PF₆] 为 **0.53 V**。文中关于方法学说明:"Conversions from the SCE scale to [FeCp2]+/0 were based on values compiled in our laboratories or reported in the literature for different solvents (Table 1)." 这是一份汇编(lead),而非一手测定。据 IntechOpen 章节交叉印证,该 THF/TBAPF₆ 的 Fc 参比值原始测定可回溯至 **Shalev & Evans**(原文:"used the determinations of Shalev and Evans to reference our measurements to Fc in THF with 100 mM TBAPF6")。严格按反臆造规则,定稿前应取得 Shalev & Evans 原文确认该一手数值。

换算:取 0.56 V(NBu₄PF₆ 体系)经任务允许的 SCE→Ag/AgCl(+0.045 V,Pavlishchuk & Addison 2000,DOI 10.1016/S0020-1693(99)00407-7)→ **Fc/Fc⁺ ≈ +0.605 V vs Ag/AgCl(sat. KCl)**；NEt₄PF₆ 体系 0.53 V → +0.575 V。需注意 2024 年该文有勘误(Corrigendum,Inorg. Chim. Acta 578, 122468),定稿前须核对偏移值是否受影响。

这意味着任务中已暂存的两行 THF Fc 数据(La Pierre 2026,TBAPF₆ 与 TBABPh₄)若使用 TBAPF₆ 且为 THF,**理论上可借 Connelly–Geiger 偏移转换**;但 La Pierre 2026 的 Fc 是相对**裸银 Ag⁰ 赝参比**(且其 Fc vs Ag⁺/⁰ 在 +0.76~+1.26 V 大幅漂移),并非相对 SCE/Ag-AgCl,故其自身 CV 数据仍不可直接换算——除非以 Connelly–Geiger 的 THF Fc-vs-SCE 偏移作为外部桥接(此为间接、跨论文换算,置信度中/低,且违反"同论文系绳"严格要求,只能作为参考估计而非门控)。

### Sulfolane（缺口仍在）
Coetzee & Simon 1972(Anal. Chem.,DOI 10.1021/ac60315a012)是 sulfolane 中伏安可用电位范围的最一手来源,Armstrong 等 1976(J. Electrochem. Soc. 123, 646–649)是 sulfolane 中 Fc/Fc⁺ 的一手研究,二者均经确认真实存在,但具体数值因原文不可访问而未能提取,严格标记 NOT FOUND。

现有可见的 sulfolane "宽窗口"绝大多数为锂电池全电池电压(如 ">5 V vs Li/Li⁺",见 oaepublish energymater.2022.38 等),属**两电极/全电池电压,不是三电极溶剂 ESW**,按整合规则不可用作门控。同样,任务中提到的 Xing 2014 / Wang 2019 / Sheina 2018 性质均为 Li/Li⁺ 全电池或凝胶聚合物全电池窗口,不可换算。

### NMP（缺口仍在）
未找到符合条件的一手三电极溶剂窗口行;已知数据为 Li-空气/Li 电池(vs Li/Li⁺),不可换算。也未找到 NMP 中 Fc/Fc⁺ vs SCE/Ag-AgCl 的内标交叉标定。Tsierkezos 的 Fc 循环伏安研究(J. Solution Chem. 2007,DOI 10.1007/s10953-006-9119-9)覆盖 ACN/ACE/NMF/DMF/DMA/PEN/DMSO/DCM,但**不含 NMP 与 sulfolane**。

### 每溶剂结论性说明
- **THF:** 出现了一条有条件可换算的路径(Connelly–Geiger Fc-vs-SCE 偏移 0.56/0.53 V → Ag/AgCl +0.605/+0.575 V),但属二手汇编,须回溯 Shalev & Evans 一手原文方可正式定稿;La Pierre 2026 的原始 CV 仍因裸银赝参比而不可直接换算。**缺口部分弥合,但尚未完全闭合。**
- **Sulfolane:** 干净的 Ag/AgCl 可换算窗口**仍不存在**;一手候选(Coetzee & Simon 1972 窗口值、Armstrong 1976 Fc 偏移)已定位但数值未取得,标记 NOT FOUND。
- **NMP:** 干净的 Ag/AgCl 可换算窗口**仍不存在**;既无合格的三电极溶剂窗口一手行,也无 NMP 中的 Fc 内标系绳。**缺口完全成立。**

## Recommendations
**第一阶段(立即,可解锁最大价值):** 直接获取三篇已确认存在但本次不可访问的一手原文:
1. Coetzee & Simon 1972,DOI 10.1021/ac60315a012,提取 sulfolane 的可用电位范围表(阳极/阴极限值、参比电极、支持电解质浓度、电流密度判据、扫速)。
2. Armstrong, Quinn & Vanderborgh 1976,J. Electrochem. Soc. 123:646,提取 sulfolane 中 Fc/Fc⁺ 半波电位及其原生参比(若为 SCE/Ag-AgCl 即可换算)。
3. Izutsu《Electrochemistry in Nonaqueous Solutions》溶剂电位窗口表 / Mann 1969(Electroanalytical Chemistry Vol. 3, p. 57),取出 NMP 与 sulfolane 的 Pt 正/负限值,并记录其 vs Fc/Fc⁺ 基准;同时回溯每个数值的原始一手论文。

**第二阶段(THF 定稿):** 回溯 Shalev & Evans 对 THF/100 mM TBAPF₆ 的 Fc 参比一手测定。若确认为真正一手且原生参比可追溯到 SCE/Ag-AgCl,则 THF 可正式标记为"可换算",采用 Fc/Fc⁺ = +0.605 V vs Ag/AgCl(NBu₄PF₆);否则保持"二手汇编派生,置信度中/低"。同时核对 Pavlishchuk & Addison 2024 勘误对 +0.045 V 常数的影响。

**门控阈值(决定是否换算并用作筛选门):** 仅当某行同时满足(i)三电极**溶剂窗口**(非全电池电压)、(ii)四烷基铵支持电解质、(iii)GC/Pt 工作电极、(iv)native 参比为 SCE/SHE/真实水相 Ag/AgCl,**或**同一论文给出同体系 Fc/Li 系绳,方可换算并用作门控。任何相对裸银赝参比或仅 vs Fc/Fc⁺ 而缺该溶剂 Fc 偏移者,一律保持 unconvertible。优先采用电流密度判据窗口(如 1 mA/cm²、5 mV/s),并在每行标注其为"current-density 判据"还是"practical CV edge"。

## Caveats
- 本次 web 检索预算耗尽,sulfolane/NMP 的关键一手数值未能提取,均严格标记 NOT FOUND,绝不臆造数值或 DOI。"NOT FOUND"在此处含义为"论文已确认真实存在但数值本次不可提取",而非"不存在"。
- Connelly & Geiger 与 Izutsu/Mann 均为二手汇编;ALS-Japan 复制的 Izutsu Pt 窗口表(Table 8)以 **vs Fc/Fc⁺** 为基准,故 NMP/sulfolane 即便取值,仍因缺少这两溶剂中的 Fc 偏移而不可换算。
- 派生的 THF Fc/Fc⁺ vs Ag/AgCl(+0.605 V)依赖于接受二手汇编偏移并跨论文桥接,置信度中/低;在用作正式门控前必须以一手原文(Shalev & Evans)确认。
- La Pierre 2026 Inorg. Chem. 论文的 THF 窗口为"practical CV edge"(裸银赝参比、200 mV/s),非电流密度判据窗口,且本质不可换算,不得直接用作门控阈值。
- 区分原则已贯彻全程:三电极溶剂窗口 vs 两电极/全电池电压(后者均已标记不可用作门控);中性态 vs 掺杂/氧化态测定;一手 vs 二手汇编(所有数值均尝试回溯一手)。