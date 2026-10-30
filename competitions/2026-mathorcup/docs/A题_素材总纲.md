# MathorCup 2026 A 题 · 队友产出素材总纲（可用性判定 → 挂接 math-modeling-contest Step 0–11）

> 生成日期：2026-10-25
> 本文件是**唯一事实源**：与 `mathorcup.md`、`2026A题坑点汇总.md`、`MathorCup_A_文献整理2026-10-24.md`、
> `A题_Markdown版/`、`A2600001附件/` 冲突时，一律以本文件第 1 章为准。
> 第 1 章全部数字由 `verify_facts.py` 直连 `附件/` 复算得出（**140 项断言全部 OK**），不是采信队友文档。
> 五份源文件一律**保持原样、不删不改**。

---

## 第 0 章 · 用法与三色标记

| 标记 | 含义 | 怎么用 |
|---|---|---|
| 🟢 **直接照抄** | 内容正确、口径一致、有实测出处 | 复制进对应 Step 的产出文件，不需改动 |
| 🟡 **改口径后抄** | 骨架/方法/表结构可用，但某处数字或定义必须替换 | 按"必改项"栏逐条替换后再用 |
| 🔴 **必须重跑** | 结论建立在错误口径上 | 只能当**反例**或占位，**不得进论文** |

三条使用铁律：

1. **不要复制队友论文正文里的任何数字**。队友 `Q1_报告.txt` / `Q2_报告.txt` / `Q3_pareto.json` 里的运行日志数字（π、Jaccard、R²、Pareto 点）是**真实跑出来的**，可用作"上限参照"；但论文正文（`00_论文全文.md`）里的聚合数字有 ≥10 处与代码/日志不符，一律不采。
2. **每抄一个数，先在本文件第 1/3/4 章找到它的判定行**。找不到 = 不抄。
3. **判定为 🟡 的，必须把"必改项"一并抄过去**。只抄骨架不抄修正，等于把错误原样搬进自己的稿子。

---

## 第 1 章 · 数据事实卡（Step 2 的权威输入）

> 复现命令：`OPENBLAS_NUM_THREADS=1 PYTHONIOENCODING=utf-8 python verify_facts.py`
> 输出 `verify_facts_report.md`，逐行可对账。

### 1.0 一次跑完全部断言的核对结果

| 项 | 结果 |
|---|---|
| 断言总数 | 140 |
| OK | **140** |
| MISMATCH | 0 |

> 这一行本身就是反 AI 评审要的"结论可复现"证据：把脚本和报告一起交，数字不是编的。

### 1.1 八附件清单

| 附件 | 实测规模 | 角色 | 可用性 | 唯一坑 |
|---|---|---|---|---|
| `1.csv` | 250 × 234 = `beer` + `beer_id` + 风格 + **231 化学列** | 特征 X | **226 个真特征**（231 = 226 + 5 派生） | 混合量纲；142 列共享 LOD 地板值；9 列 73 个真 NA |
| `2.csv` | 231 × 231 | 化合物相关图 | 全可用 | **是 Spearman**（非题面 PDF 所称 Pearson）；对角全 1、严格对称 |
| `3.xlsx` | 13 sheet（`beer_1..beer_12` + `summary`） | 评分卡**模式** | **不提供任何真值** | 1260 条公式缓存值全 0；sheet 内 1–6 是**列头图例** |
| `4.csv` | 250 × 53 = 3 meta + **50 感官** | 标签 Y | 可用（50 维） | 仅中心化的连续强度，**不可精确反解 0–6** |
| `5.csv` | 50 × 50 | 感官间相关 | 可用 | Spearman；行列名用论文**长名** |
| `6.csv` | **44 × 50**（题面说 46×50） | 化学 × 感官交叉相关 | 可用 | Spearman；长名，需字典映射 |
| `7.csv` | 250 × 189 = 3 meta + **186 描述符** | 外部感官视图 | **183 维可用** | 3 列全空；**只有它才是真 z 分数** |
| `8.xlsx` | 7 sheet | 字典 + 阈值 + 反变换对照 + **诱饵** | 阈值/字典/Calibrated 极有用 | MDI/SHAP 是"现成答案"，抄 = 丢分 |

### 1.2 「226 / 231 / 250」三数辨析（题目把 226 说成啤酒数，是误译）

- **250** = 啤酒样本数（1/4/7/8-Calibrated 全部 250 行）
- **231** = 化学列总数 = **226 实测 + 5 派生**
- **226** = 实测化学指标数 = 建模特征数
- **5 个派生列**：`kcalperc, esters_sum, aroma_hops_sum, acids_sum, sulfur_sum`
  - ⚠️ **`kcalperc` 在 8.xlsx `Calibrated chemical dataset` 里也有一列**，所以"Calibrated 交集"要分两个口径数（见 1.3）

### 1.3 量纲三分（**全篇最硬的口径卡**）

判据：用 8.xlsx `Calibrated chemical dataset` 与 1.csv 逐列对拍，**分类前必须先剔除 Calibrated 中 `b==0` 的格**（否则 `10^a / 0` 溢出，会把列误判成"两边都不像"）：

- 若 `median(|10^a − b| / b) < 1e-3` 且线性误差 ≥1e-3 → **该列是 log10**
- 若 `median(|a − b| / |b|) < 1e-3` → **该列是原始线性**

**实测结果（零歧义）**：

| 口径 | Calibrated 交集 | LOG10 | LINEAR | 歧义 |
|---|---|---|---|---|
| 231 化学列口径 | **70**（含派生列 `kcalperc`） | **37** | **33** | **0** |
| 226 实测特征口径 | **69** | **36** | **33** | **0** |

- `kcalperc` 判为 **LOG10**（不在 33 线性名单里）
- **33 列线性名单中 0 个零值格**（这也是一个可用的一致性检查）

**231 列全局口径**：**175 列 min<0 / 56 列 min≥0**。56 列可完全拆清（闭合检查）：

| 来源 | 列数 | 判据 |
|---|---|---|
| 33 线性名单 | **33** | Calibrated 逐列对拍，线性误差 <1e-3 |
| Calibrated 已验 log10、但原始浓度 >1 | **7** | `DMS`、`color.EBC.`、`betaglucan.mg.L.`、`lactic_acid.mg.L.`、`pH`、`unfermentables`、`kcalperc` |
| 无 Calibrated 对照 | **16** | 推定 log10 |
| **合计** | **56** | |

175 列 min<0 同理：**30 列 Calibrated 已验 + 145 列无对照 = 175**。两侧相加 175 + 56 = 231，完全闭合。

**其余 157 列**（226 特征里没有 Calibrated 对照的）：
- **142 列 min<0** → 必为 log10（负值只能来自对数域）
- **15 列 min≥0** → 仍是 log10，只是因为原始浓度全部 >1，`log10(c)>0`

> 口径提醒：**142 + 15 = 157 是 226 特征口径**；**145 + 16 = 161 是 231 化学列口径**。两者差 4 列，是三个不进 Calibrated 的派生列（`esters_sum`、`acids_sum`、`sulfur_sum` 的 min<0，进 145）加 `aroma_hops_sum`（min≥0，进 16）；`kcalperc` 在 Calibrated 里所以两边都不计。**两个口径不要混着写。**

**五个"号称保留原始量纲"的理化列，实测也全是 log10**（题面 PDF 说它们保留原始量纲，是错的）：

| 列（1.csv 真实列名） | 1.csv 中位 | 10^中位 | Calibrated 中位 | 判定 |
|---|---|---|---|---|
| `pH` | 0.616 | **4.13** | 4.133 | LOG10 |
| `ethanol..v.v.` | 0.857 | **7.19** %vol | 7.193 | LOG10 |
| `color.EBC.` | 1.261 | **18.22** EBC | 18.225 | LOG10 |
| `bitterness` | 1.259 | **18.16** IBU | 18.162 | LOG10 |
| `CO2.PSI.` | 0.362 | **2.30** PSI | 2.500 | LOG10 |

逐列对拍误差：`err_log ≈ 5e-10`（全命中）/ `err_lin ≈ 0.85–0.93`（全不命中）→ 五列零歧义。

> ⚠️ **列名坑**：1.csv 里乙醇列叫 **`ethanol..v.v.`**，不叫 `ethanol`；`CO2.PSI.`、`color.EBC.` 同理带尾点，`betaglucan.mg.L.`、`lactic_acid.mg.L.`、`protein.g.L.` 也是。手写列名必错，一律从 `1.csv.columns` 取。

**15 列"看起来像线性、其实是 log10"易误判名单**（🆕 必须写进论文的坑）：
`n.pentanol, X2.methyl.1.butanol, isopentyl.formate, X3.methyl.2.butenal, X3.methyl.2.hexanol, X3.furanmethanol, n.heptanol, ethyl.hex..3E..enoate, n.octanol, terpinolene, nonan.2.ol, isoborneol, ethyl.benzoate, trans.dihydro.alpha.terpinyl.acetate, X.E..beta.ionone`

**33 列原始线性名单**（精确，别手抄错）：
```
X2.3.butanedione, X3.methylbutanal, ethyl.isobutyrate, ethyl.butyrate,
X2.methyltetrahydrofuran.3.one, methylpyrazine, furfural, X3Z.hexenol,
n.hexanol, styrene, ethyl.pentanoate, amyl.acetate, benzaldehyde,
X5.methylfurfural, X2.ethyl.3.methylpyrazine, hexyl.acetate, benzyl.alcohol,
phenylacetaldehyde, X.E..beta.ocimene, linalool, X.E..2.nonenal,
diethyl.succinate, X1.alpha.terpineol, ethyl.nicotinate, citronellol,
geraniol, X.E.E..2.4.decadienal, eugenol, gamma.nonalactone,
X.E..beta.damascenone, E.caryophyllene, alpha.humulene, Z.nerolidol
```

> ⚠️ **队友口径错在哪**：`01_数据体检与陷阱清单.md` T2 与 `04_Brainstorming` 都写"198 列 log10 / 33 列线性"。
> 实际上 198+33+5 = 236 ≠ 231，**本身就不自洽**；而且"198 列经校验为 log10"没有任何依据——
> Calibrated 只覆盖 70 列，其中确认 log10 的是 **37 列**（231 口径），其余 161 列是**推定**，不是"验证"。
> 正确表述（231 口径）：**33 线性（验证）/ 37 log10（验证）/ 161 列无 Calibrated 对照（145 列 min<0 必为 log10 + 16 列 min≥0 推定 log10）**，共 231。
> 若按 226 特征口径：**33 线性 / 36 log10 / 157 列无对照（142 min<0 + 15 min≥0）**。

### 1.4 LOD 地板值与真 NA（🆕 **本轮重要修正**）

**共享地板值** `-1.817819`（≈ 10^-1.818 ≈ 0.0152，即 15.2 ppb 的统一检出下限）：
- 精确出现 **6807 格**
- 覆盖 **142 列**（⚠️ 早期说法"69 列"是错的，实测 142 列）

**专属地板值**（每列自己的最低值，且 ≠ 共享值）：**33 列 / 793 格**，其中重复 ≥3 的 14 列、重复 ≥8 的 10 列：

| 列 | 重复格数 | 该列 LOD（log10） |
|---|---|---|
| CS2 | 209 | −2.1463 |
| X4VG | 168 | −2.0132 |
| octyl_acetate | 110 | −3.4550 |
| ethyl_2.methyl_butyrate | 85 | −3.1955 |
| ethyl_isovalerate | 83 | −4.4870 |
| CO2.PSI. | 39 | −0.2310 |
| DES | 29 | −1.9053 |
| ethyl_propionate | 10 | −2.4428 |
| H2S | 10 | −1.5861 |
| isobutyl_acetate | 8 | −3.2656 |

**真 NA**：**73 格 / 9 列**（0.13%）

| 列 | NA 数 |
|---|---|
| `amyl.acetate` | 27 |
| `aroma_hops_sum` | 13 |
| `methylpyrazine` | 12 |
| `X2.3.butanedione`（双乙酰） | 9 |
| `X3.methylbutanal` | 7 |
| `ethyl.nicotinate` | 2 |
| `ethyl.isobutyrate` | 1 |
| `furfural` | 1 |
| `phenylacetaldehyde` | 1 |

> **两种缺失必须分开叙事**：LOD 走"删失/hurdle"叙事（真实值存在但低于检测限），NA 走"插补"叙事（未测）。
> 混为一谈会被评审抓住。队友 T10/T11 分开写了，这处 🟢 可用。

### 1.5 🆕 `beer_id` 已损坏 → 只能用 `beer` 列对齐

| 文件 | `beer_id` 唯一值 | 说明 |
|---|---|---|
| `4.csv` | **96** / 250 行 | 154 行重复，被存成 `5.41023E+12` 科学计数串 |
| `7.csv` | **96** / 250 行 | 同上 |
| `1.csv` | **250** / 250 行 | 完整 13 位字符串，正常 |

`beer` 列（1..250 序号）顺序在 **1/4/7 三表完全一致**（已断言 True）。→ **唯一安全对齐键 = `beer`**。
队友 T1 已正确指出，🟢 直接抄。

### 1.6 4.csv vs 3.xlsx `summary` 列序（后 20 位全乱）

对齐 `4.csv[0:50]` 与 `summary[1:51]`（跳过 `Beer` 列）：

- **同位置相同：30 个**（前 30 位 A_/F_ 描述，另有一处拼写差 `A_ester_fruity` vs `A_esters_fruity`）
- **同位置不同：20 个**（30–48 位整段乱序）
- 最后一位两边都是 `overall`

summary 的顺序：`body, bitternes, co2, aftertaste, alcohol, sweetness, acidity, dms, metallic, 4vg, t2n, diacetyl, stale_hops, orange, coriander, clove, lactic, acetic, barnyard, overall`
4.csv 的顺序：`acidity, bitternes, sweetness, X4vg, diacetyl, dms, metallic, stale_hops, t2n, orange, coriander, clove, lactic, acetic, barnyard, alcohol, aftertaste, body, co2, overall`

→ **必须按列名 + 归一化（大小写 / `X4vg→4vg` / `esters→ester`）对齐，禁按位置拼接**。队友 T9 🟢 可用。

### 1.7 3.xlsx 真相（⚠️ 两处必改）

- **13 个 sheet**：`beer_1` … `beer_12` + `summary`（题面说 10 张，实测 12 张 beer sheet）
- **公式总数 = 1260**：每个 beer sheet **54 条**（×12 = 648）+ `summary` **612 条** = 1260
- **缓存值全为 0**（`summary` 12 行也全 0）
- **sheet 内那排 1–6 是列头图例**，实测坐标：`E8=1, G8=2, I8=3, K8=4, M8=5, O8=6`（Aroma 栏）与 `U8=1, W8=2, Y8=3, AA8=4, AC8=5, AE8=6`（Flavour 栏），另有 `S3=1`（Beer#）
- `summary` 的 A 列值 1–12 **只是行号**

> ⚠️ 必改：队友 T5 写"每 sheet 54 条公式"——**这只是单张 sheet 的数**，总数是 1260。
> 本仓库 `2026A题坑点汇总.md` 已修正为 1260，但队友文档未改，抄的时候别抄错。

### 1.8 8.xlsx 七表

| sheet | 形状 | 关键事实 |
|---|---|---|
| `Sensory thresholds` | 261 × 11 | **仅 43 行有阈值数值**：mg/L 33、g/L 4、ug/L 4、IBU 1、v/v 1；`off_flavors` 仅 **7** 行、`aging` 26 行；`origin_paper` **257/261** 有值 |
| `Sensory names` | 101 × 8 | `Trained panel` **50** 行 + `Ratebeer` **51** 行；Trained panel 里 **numeric 26 / categorical 24** |
| `GBM importance MDI` | 231 × 2 | 列名 `['Unnamed: 0', 0]`（0 = importance, Unnamed: 0 = 化合物名）；**是诱饵** |
| `GBM SHAP Values` | 500 × 236 | `data` 列把 SHAP(250) 与 concentration(250) 拼在一起；**`base_prediction` 列必须剔除** |
| `Calibrated chemical dataset` | 250 × 73 | 70 个化学列（含 `kcalperc`）；**815 个 0 格** |
| `Beer Prices` | 250 × 11 | 价格列缺 43–204/250（`Price_Colruyt_Belgium` 缺 170、`Price_BeerHawk_UK` 缺 204）；**ABV 完整** |
| `Sheet2` | **0 × 0** | 空表（⚠️ 不在 3.xlsx 里，在 8.xlsx 里） |

**关键阈值（同单位直接除，不做换算）**：

| 物质 | `threshold_mean` | `threshold_median` |
|---|---|---|
| DMS | **17.25 µg/L** | 19.0 |
| Diacetyl | **0.29925 mg/L** | 0.09 |
| 4VG | **0.206333 mg/L** | 0.20 |
| **t2n（(E)-2-nonenal）** | **行存在，但两个阈值列全空** | — |

> t2n 阈值必须引文献补，**不能假装表里有**。

### 1.9 4.csv 的性质（三条独立证据）

| 证据 | 实测 | 推论 |
|---|---|---|
| 每列 sd | min **0.3697** / median **0.5536** / max **0.8585** | **不是 z 分数**（z 分数逐列 sd 必为 1） |
| 取值范围 | **−2.151 ~ 6.172**；负值占 **60.9%** | 不是 0–6 原始分 |
| 每列不同取值数 | min **106** / median **229** / max **250** | 不是 1/k 面板均值（面板均值会有大量重复） |
| 列均值 | −0.049 ~ 0.063 | **只做了中心化** |
| 全列 NA | 0 | 输出侧无缺失 |

**1/k 网格检验（联合搜索 μ、s 后的最优残差 / 随机水平步长/4）**：

| k | 最优残差 | 随机水平 | 比值 |
|---|---|---|---|
| 6 | 0.1397 | 0.3000 | 0.466 |
| 12 | 0.0976 | 0.1364 | 0.716 |
| 16 | 0.0859 | 0.1000 | 0.859 |
| 20 | 0.0634 | 0.0789 | 0.803 |
| 32 | 0.0404 | 0.0484 | 0.835 |

> **正确读法**（这是本轮对旧说法的修正）：残差**没有塌到 0**（若真存在 1/k 网格，联合最优拟合应接近 0），
> 但也**不是完全等于随机水平**（0.72–0.86 说明仿射变换后确实略有对齐）。
> 稳健的结论只有一句：**"不存在可辨识的 1/k 面板均值网格"**，不能写成"完全等于随机水平"。
> 队友 T4 的"err≈0.2 = 随机水平"是旧口径（未联合优化 μ、s），数值不采，结论方向对。

→ **定性：4.csv 是"仅中心化的连续强度"**，转 0–6 只能走**保序分位映射**，且必须声明局限。

### 1.10 7.csv 才是真 z 分数

- 186 个描述符列；sd 中位数 **1.0030**；**164/186 列 sd > 0.99**
- 3 列全空：`palate_acetaldehyde`、`palate_acetate`、`palate_dentist` → 入模前删除，剩 **183 维**
- 与 4.csv 是**两套标签体系**，同概念列相关性弱（如 `A_malt_all ~ aroma_malt` 仅 r≈0.45）→ **不能混用，只能作对照/辅助**

### 1.11 相关结构与有效秩

| 指标 | 实测 |
|---|---|
| PCA PC1 解释率 | **14.3%** |
| 前 10 主成分 | **48.3%** |
| 前 50 主成分 | **80.7%** |
| 达 90% 方差所需主成分 | **79 个** |
| Pearson \|r\| 中位数 | **0.097** |
| \|r\| > 0.9 的变量对 | **仅 4 对** |
| VIF > 10 的列 | **226 / 226（全部）** |
| VIF 中位数 | 33.72 |
| VIF 最大值 | 1267.9（E-caryophyllene） |

- **2.csv \|ρ\|≥0.30 → 3918 条边**（平均度 33.9）；0.40 → 1660；0.50 → 645
- 谱聚类：12 模块，**模块内平均 \|ρ\| = 0.187 vs 模块间 0.120，比值 1.56×**，且最大模块吞掉 183 节点 → **社区结构是噪声级，不能当作"化合物模块"解释**；改用 `origin_paper` 分组

> ⚠️ **VIF 用法警告**：p/n ≈ 0.92，VIF 全 >10 是**结构性必然**，不是"该删变量"的信号。
> 按"VIF>10 就删"→ 226 列全删光。正确用法是**报 PCA 有效秩 79**，并改用正则化/降维。

### 1.12 风格分布（22 类）

| 风格 | n | 风格 | n |
|---|---|---|---|
| Blond | 31 | Low/No alcohol | 8 |
| Tripel | 28 | Fruitbeer | 8 |
| Strong ale | 18 | West Flanders ale | 7 |
| Hoppy | 17 | Brett/cofermented | 6 |
| Stout/Porter | 13 | Flanders old brown | 5 |
| Wheat | 12 | Scotch | 5 |
| Amber | 12 | Brut | 4 |
| Brown | 12 | **Faro** | **3** |
| Pils/Lager | 11 | | |
| Lambic | 11 | | |
| Dubbel | 10 | | |
| Kriek | 10 | | |
| Saison | 10 | | |
| Christmas | 9 | | |

- 最小类 **Faro = 3**；≤5 例的 4 类合计占 6%
- `tasting_category_fine`（1/7.csv）与 `tasting_category`（Beer Prices）是**大小写变体**，先归一化

### 1.13 缺失的真实分布（按风格，🆕 必写）

| 列 | 总缺失 | 最集中的风格 |
|---|---|---|
| `amyl.acetate` | 27/250 | Dubbel 4/10 = 40%；Kriek 3/10 = 30%；Blond 6/31 = 19.4%；Tripel 3/28 = 10.7% |
| `aroma_hops_sum` | 13 | Hoppy 6/17 = 35.3% |
| `methylpyrazine` | 12 | — |
| `X2.3.butanedione` | 9 | West Flanders ale 2/7 = 28.6% |

→ **缺失不是随机的**，全局均值填充会抹平风格差异。必须"风格内中位数 + 缺失指示变量"。

### 1.14 已核验的 Spearman 值（6.csv 抽查，精确到 4 位）

| 化学 | 感官 | ρ |
|---|---|---|
| ethanol | alcohol | **0.8171** |
| ethanol | body | **0.7191** |
| lactic_acid | acidity | **0.3187** |

其余已核（前轮）：`bitterness ~ bitternes` **0.6822**、`color.EBC ~ A_malt_all` **0.5415**、`GFS ~ sweetness` **0.3730**、`ethyl_acetate ~ A_malt_all` **0.2561**。

### 1.15 `origin_paper` 覆盖 226/226（🆕 修正队友的 154/231）

用**归一化名匹配**（小写、去标点、`alpha→a / beta→b / gamma→g / delta→d`）后：

| 来源 | 特征数 |
|---|---|
| Yeast | 78 |
| Hops | 77 |
| Spices | 23 |
| Malt | 21 |
| Others | 20 |
| Wild flora | 6 |
| Internal standard solution | 1 |
| **合计** | **226 / 226** |

> 队友 `Q2_报告.txt` 写"origin_paper 命中 154/231"，是**直接字符串匹配**的残留，不是真实覆盖率。
> 用归一化匹配后 **100% 覆盖** → Q2 可以放心用化学来源分组做条件置换。

### 1.16 传感器口径：2/5/6.csv 都是 Spearman

- 2.csv 对角全 1、严格对称（已断言）
- `数据说明.txt` 写 Spearman（**正确**），题面 PDF 写 Pearson（**错**）
- 论文里要**把这次口径核验写成证据**，而不是悄悄用 Spearman

### 1.17 6.csv 是 44×50（题面说 46×50）

行 = 44 个化合物（论文长名，如 `Ethyl acetate`），列 = 50 个感官（长名，如 `Malt aroma - overall`）。
**行列名都不是 1.csv/4.csv 的短名**，必须过 8.xlsx `Sensory names` 的映射。

---

## 第 2 章 · 本轮新增的五个关键发现

> 这四条**两份队友文档都没提**，是本次整理的最大增量。

### 2.1 🔴 **50 个 Q1 目标里 24 个是 `categorical`（有/无），不是 0–6 强度**

8.xlsx `Sensory names` 的 `DataType` 列，`Trained panel` 50 行分布：

- `numeric` **26**
- `categorical` **24**

24 个 categorical 精确名单（**全部是 14 个 Aroma 子描述 + 10 个 Flavour 子描述**）：

```
A_esters_ethac, A_esters_flower, A_esters_fruity, A_esters_isoaa,
A_hops_citrus, A_hops_noble, A_hops_tropical, A_hops_woody,
A_malt_bread, A_malt_burn, A_malt_cara, A_malt_grain,
F_esters_ethac, F_esters_flower, F_esters_fruity, F_esters_isoaa,
F_hops_citrus, F_hops_noble, F_hops_tropical, F_hops_woody,
F_malt_bread, F_malt_burn, F_malt_cara, F_malt_grain
```

**后果（直接推翻队友的呈现方式）**：

- 不能对 24 个 categorical 维算 R² / 做 0–6 分位映射 / 算 QWK —— 它们是二分类
- Q1 必须拆成 **26 维回归 + 24 维二分类**
- 指标表必须分两块：回归块报 MAE/R²/Spearman；分类块报 AUC/AP/Brier/准确率
- 队友 `02_结果表/01_Q1_逐维指标.md` 的 "50 维 × 3 模型 × 6 指标" 表**整体呈现方式是错的**（🟡 骨架可用，口径必改）
- 队友 `03_报告/Q1_报告.md` 里 `F_esters_flower R² = −0.080` 这种"最差维"，很可能正是因为**把一个二分类目标当连续回归**——这本身就是一个可写进论文的发现

### 2.2 🟢 **Calibrated 表的 0 就是官方 LOD 解码器**

- `Calibrated chemical dataset` 共 **815 个 0 格**
- 其中 **763 格（93.6%）** 可由 1.csv 该列的地板值精确解释
- 剩 52 格：全部落在**真 NA 的列**上（`amyl.acetate` 27、`methylpyrazine` 12、`X2.3.butanedione` 9、`X3.methylbutanal` 7、`ethyl.nicotinate` 2、`ethyl.isobutyrate`/`furfural`/`phenylacetaldehyde` 各 1）

**用法**：`Calibrated[i,j] == 0` ⟺ `1.csv[i,j]` 是该列 LOD 地板值（或该格是 NA）。
→ LOD 处理有了**官方依据**，不需要自己猜"哪些 -1.817819 该删"。
→ 这也是检验"你的 LOD 识别做对了没"的自动断言。

### 2.3 🟢 **`origin_paper` 覆盖 226/226**（见 1.15）

### 2.4 🔴 **Q3 Pareto 表出自 L-BFGS-B 降级分支，不是 Gurobi**

**证据链（三重，互相独立）**：

1. **本机实跑**：`import gurobipy` → `ModuleNotFoundError: No module named 'gurobipy'`。队友脚本 `q3_moo_gurobi.py` 第 27–32 行是 `try: import gurobipy / HAS_GUROBI=True except: HAS_GUROBI=False`，所以运行输出 `HAS_GUROBI: False`。
2. **数值不可能**：Gurobi 分支 `f3 = Σ_j γ_j·y_j + λ·Σ_j (xp_j + xn_j)`，`gamma` 默认 `{}.get(j, 1.0) = 1.0`。只要有一个 `y_j = 1`，就有 `f3 ≥ 1`。而 Pareto 表 4 个点的 f3 = **0.046 / 0.148 / 0.299 / 0.599**，**全部 < 1** → 不可能是 Gurobi 分支产出。
3. **f1 量纲不同**：Gurobi 分支 `f1 = Σ_s w_s (u⁺_s + u⁻_s)` 是 **L1**；降级分支 `f1 = Σ_s w_s (a_s + B_s·v − t_s)²` 是 **L2**。所以表里的 f1 值（0.907 → 0.148）是 L2 尺度，与其他任何 L1 结果不可比。

**降级分支实际做了什么**（`q3_moo_gurobi.py` 第 220–245 行）：
- `f1` = 加权**平方**偏差
- `f3` = `λ · Σ|x|`（**没有 y 项**）
- `f2` 只是把软约束违反量加总
- ε 约束变成**惩罚项**（`pen += 50 * max(0, ...)`），不是真约束
- 求解器 `scipy.optimize.minimize(method='L-BFGS-B')`

→ **队友论文里"Gurobi MILP / ε-约束"的说法在本机从未成立过**。必须重跑。

### 2.5 🔴 **五个"号称保留原始量纲"的理化列其实也全在 log10 域**（见 1.3 表）

题面 PDF 明写 pH / ethanol / color / bitterness / CO2 这五列"保留原始量纲"。用 8.xlsx `Calibrated chemical dataset` 逐列对拍后，五列**全部判为 LOG10**（`err_log ≈ 5e-10` / `err_lin ≈ 0.85–0.93`，零歧义）：

- `pH` 0.616 → 4.13（啤酒 pH 4.1–4.2，合理；按线性读成 0.62 则荒谬）
- `ethanol..v.v.` 0.857 → 7.19 %vol
- `color.EBC.` 1.261 → 18.22 EBC
- `bitterness` 1.259 → 18.16 IBU
- `CO2.PSI.` 0.362 → 2.30 PSI

**两条后果**：

1. **不存在"哪些列要还原、哪些不要"的选择题**——除 33 列线性名单外，全部要还原。任何"只还原 35/37 列"的写法都是漏的。
2. **`bitterness` 有负值**（min = −1.144）→ 这是 log10 域的必然结果（10^-1.144 ≈ 0.072 IBU），不是异常值，不能当离群点删。

> 这也是本文件"**一切以实测为准、不以题面文字为准**"这一原则最直接的例证，值得原样写进论文的数据体检章。

---

## 第 3 章 · **Step 0–11 取材清单（核心交付）**

> 每行四列：`Step / Gate` → `该步产出（skill 契约）` → `从队友哪个文件抄什么` → `判定 + 必改项`。
> Step 与 Gate 的对应见 `math-modeling-contest/SKILL.md` 的 "Step ↔ Gate Mapping"。

| Step | Gate | 该步产出 | 取材来源 | 判定 + 必改项 |
|---|---|---|---|---|
| **0** | G1 | `requirements.md`、`material_library_index.json` | `01_文档/06_提交规范核对表.md` 的 A1–A9（格式）+ B1–B5（提交）+ C1–C6（AI 规定），共 20 条，每条都对应官方 2 份 PDF 与模板 DOCX | 🟢 **直接照抄**。这是队友最有价值的一件：20 条全部有官方出处、逐条给了证据位置。抄成 requirements.md 时补上"本届官方模板"路径 |
| **1** | G1 | `paper/` 主文件与导言区 | 队友走 DOCX 路线（`论文初稿_啤酒风味_v2.docx`，26 页 / 12606 字 / 14 表 / 15 图 / 27 引）；skill 优先模板族 | 🟡 **章节骨架可抄**（封面表→摘要→目录→正文→参考文献→AI 声明）；模板改走 `math-modeling-contest/templates/zh/<contest>/` 或 `scripts/build_docx.py`，**不沿用其自排版** |
| **2** | G1 | 数据体检报告 | `01_文档/01_数据体检与陷阱清单.md` 的 T1–T16 总表 + §3 两张口径卡（Python 读数据写法 / 一句话记忆） | 🟡 **16 条中 13 条成立**。必改 3 条：① T2 量纲（198/33 → 37/33/161，见 1.3）；② T5 公式数（54 → **1260**）；③ T4 的 1/k 检验数值（见 1.9）。另**新增 5 条**：categorical 24、Calibrated 0 解码、origin_paper 226/226、beer_id 之外的对齐风险、五个理化列全在 log10 |
| **3** | G1 | `problem_analysis.json` + 依赖 DAG | `01_文档/02_三问任务与工作量清单.md` 的三问定义表、输入/输出维度、工作量与依赖链 | 🟢 **依赖 DAG 直接抄**："Q1 标签反演不落地 → Q2/Q3 全部悬空"。🟡 Q1 输出维度必改：**50 维 → 26 回归 + 24 分类**；工作量估计（3 / 3.5 / 4.5 天）可作参考不作承诺 |
| **4** | G1 | 每问 ≥2 篇已验证文献 + `references.bib` | 我方 `MathorCup_A_文献整理2026-10-24.md`（11 条）⊕ 队友 `01_文档/05_文献档案与参考文献.md`（28 条，带证据等级 A/B/C） | 🟡 **去重合并后约 27 条**（见第 5 章）。须补 bibtex 字段、按 Q1/Q2/Q3 分组标"直接应用 / 方法可迁移 / 不可照搬"，并核 DOI |
| **5** | G2 前置 | 2–3 方案 + **五大路径标注** + 公式雏形 | `01_文档/04_Brainstorming_创新点与实验清单.md` 的 8 个创新点（Ⅰ–Ⅷ）、消融 A1–A5 / B1–B6 / C1–C6、12 图 5 表清单 | 🟡 **创新点内容可用，但一条都没标 skill 要求的五大路径**（①参数适配 ②多模型比较 ③求解器升级 ④同域融合 ⑤跨域迁移）。本步必须逐条补标，**标不上的降级为"普通建模"，不写成创新**。另：Ⅷ 的"已有 Pareto 结果"依据作废（见 2.4） |
| **6** | **G2** | `model_route.json`、`rubric_alignment.json` | 无现成件。骨架取 `mathorcup.md` 第二部分 8 章 + 队友 `02_三问任务…md` 的三问表 | 🔴 **必须自己产出**。数学结构（f1/f2/f3 三种形式、Gurobi 结构对应表 LP/QP/MILP/MIQP、ε-约束流程）从 `mathorcup.md` §5 抄，但**f1 用 L1 还是 L2、f3 是否含 y 项必须在本步一次性定死**（这是 2.4 事故的根因） |
| **7** | **G3** | `code/`、`results/`、`figures/`、`quality_notes.md` | `07_源代码/q1_model.py`、`q2_pilot_v2.py`、`q3_moo_gurobi.py` | 🟡 **三段逻辑可抄**，各有必改项 → 见 §3 附 |
| **7.2** | G3 | `diagrams/` SVG + PNG | 队友 `images/fig01.png` 的技术路线三泳道图**设计**（数据阶段→代理模型→三问） | 🟡 **只抄设计**。按 skill 要求必须走 `fireworks-tech-graph`（SVG+PNG+验证门），**禁用 matplotlib / draw.io 顶替**；Mermaid 只能作聊天预览 |
| **7.3** | **G4** | `robustness/Qx/qx_robustness_report.md` | 队友的遮挡实验（5%/10%/20% 输入遮蔽）、灵敏度龙卷风（`06_Q3_Pareto与灵敏度.md` 的 5 参数 × lo/hi/span）、相关阈值敏感性 0.3/0.4/0.5 | 🟡 **设计可抄**。但龙卷风表里 `稀疏惩罚 λ` 的 span = 0（完全不敏感），这本身要么是 bug、要么说明 λ 被约束架空 → **必须重跑并解释**，不能原样搬 |
| **7.4** | G4 | results / figure / table / tasks 索引 | 无 | 🔴 **新建** |
| **7.5** | G4/G6 | `qa_report.json` | 无 | 🔴 **新建**（跑 `scripts/quality_gate.py`） |
| **8** | **G5** | 论文草稿 | `06_提交规范核对表.md` §三的 **15 图 D-A-C 映射表**（每图为什么/说明什么/支撑什么）；`03_报告/Q2_报告.md` 的 S0–S7 全流程日志写法 | 🟡 **图表叙事结构可抄**（这是队友文档质量最高的部分之一），但**全部数字换成冻结后的新值**。`00_论文全文.md` 的正文数字不要抄 |
| **8.5** | G5 | 附录代码 | 队友附录 A（软件版本 + 7 条复现命令）、附录 B（31 文件清单 + 7 个核心脚本全文） | 🟢 **格式照抄**；脚本内容按 §3 附 的必改项替换 |
| **9** | G5 | `\cite` 标注 + 参考文献表 | 第 5 章合并表 | 🟡 按 skill 的"正文引用次序"规则重排；书籍条目须补页码 |
| **10** | **G6** | 润色稿 + `changelog.md` | 走 `agents/polisher.md`；队友 12606 字初稿只作**对照** | 🔴 **重写**。字数下限 9000 是"实质内容"下限，靠删改队友稿达不到，必须自己写够证据密度 |
| **11** | **G6** | PDF/DOCX/提交包 + 最终验证报告 | `06_提交规范核对表.md` 的待办 T1–T7（承诺书 / 打包 / AI 说明 PDF / 逐图 AI 声明 / 改名） | 🟢 **待办清单照抄**；页数上限（≤30 页正文）与 AI 披露条款按官方规则重核 |

### §3 附 · 三个脚本的「抄哪几行 / 改哪几处」

#### `q1_model.py`（🔴→🟡 重写后可用）

**可直接抄的**：

- `PRIORS`（第 44–48 行，三套先验做敏感性）：
  ```python
  uniform  = [1/7]*7
  zeroinfl = [0.50, 0.18, 0.12, 0.09, 0.06, 0.035, 0.015]
  mildzero = [0.35, 0.20, 0.16, 0.13, 0.09, 0.05, 0.02]
  ```
- `quantile_to_grade(z, prior)`（第 50–60 行）：`r = rank/n` → `cdf = cumsum(prior)` → `g = searchsorted(cdf, r, side='left')` → `clip(g,0,6)`。**保序分位映射，实现正确**
- `qwk(y_true, y_pred, k=7)`（第 62–72 行）：二次权重 `w = (i−j)²/(k−1)²`，标准加权 kappa 公式，**实现正确**

**必改三处**：

1. 🔴 **QWK 虚高**。第 155–160 行先 `gt = grade['zeroinfl'][:, j]`（真值用分位映射得到的等级），再 `pr = quantile_to_grade(pred, PRIORS['zeroinfl'])`（预测又用同一先验映射一次）。
   这是**对预测做单调变换后再与自己同分布的真值比**，QWK 结构上退化到 ≈Spearman，系统性虚高。
   → 正确做法：真值与预测必须在**同一映射**下比；或干脆只用 Spearman/MAE 报连续指标，QWK 另设"真标签可得时"的口径并**声明当前不可用**。
2. 🔴 **24 个 categorical 维不能进 QWK**（见 2.1）。必须拆成二分类，指标换 AUC/AP/Brier。
3. 🟡 **均值基线 Spearman = −0.0738**（`Q1_报告.txt` 打印）：常量预测的秩相关**无定义**（std=0），这个数不能报。改成"基线的 R² = −0.0054，不报 Spearman"。

**队友实测聚合（已复算，可作上限参照）**：

| 模型 | 平均 MAE | 平均 R² | 平均 Spearman |
|---|---|---|---|
| ElasticNet | 0.3751 | **0.1367** | 0.3700 |
| GBR | 0.3421 | **0.2224** | 0.4094 |
| 均值基线 | 0.4167 | **−0.0054** | （不报） |

- GBR 优于均值基线：**41 / 50**
- GBR R² > 0：**41 / 50**（⚠️ 队友论文正文写"38 维"，**复算为 41**，正文错）
- ElasticNet R² > 0：**33 / 50**；GBR > ElasticNet：**44 / 50**
- GBR 最强维：`alcohol` **0.730**、`acidity` **0.726**、`lactic` 0.677、`bitternes` 0.634、`acetic` 0.623
- GBR 最弱维：`F_esters_flower` **−0.080**、`clove` −0.060、`barnyard` −0.046、`coriander` −0.045、`A_esters_flower` −0.038
- 消融（33 列不取 log10 vs 取）：**0.0982 → 0.1028**，但**只跑了单折**，与 5 折的 0.1367 **不可比** → 🟡 只可作"方向一致"的旁证，不能作定量结论

#### `q2_pilot_v2.py`（🟡 参数必改后可用）

**可直接抄**：

- Bootstrap 主循环骨架：重采样 → 三模型（GBR / ET / RF）→ 逐维 Top-K → 入选频率 π_j → 跨方法 Jaccard
- `DERIVED` 派生列剔除（第 32 行）：`['kcalperc','esters_sum','aroma_hops_sum','acids_sum','sulfur_sum']`，第 92 行 `FEAT = [c for c in CHEM_ALL if c not in DERIVED]`
- 跨方法 Jaccard 定义 `J(A,B) = |A∩B| / |A∪B|`

**必改三处**：

1. 🟡 `N_BOOT = 30`（第 60 行）→ **≥200**（题面建议）。⚠️ 队友论文写"B=40"，与代码不符。
2. 🟡 试点只跑 **16 维**（`body, bitternes, alcohol, sweetness, overall, acidity, A_malt_all, aftertaste, F_malt_all, A_hops_all, A_hops_citrus, A_esters_all, F_esters_all, dms, diacetyl, stale_hops`）→ 正式版要跑 **50 维**（其中 24 维 categorical 改走分类重要性）
3. 🟡 `TOPK_JAC = 10` 的 Jaccard 与 Top-3 结论口径不同，报告里要说明"Jaccard 用 Top-10 衡量稳定性，Top-3 是最终输出"

**队友试点结果（真实运行，可作参照）**：

- 跨方法平均 Jaccard **0.342**（GBR-RF 0.389 / ET-RF 0.379 / GBR-ET **0.258 最差**）
- 入选频率 π≥0.5 的稳定条目 **23/48**
- 最稳维：`aftertaste` 0.449、`alcohol` 0.425、`body` 0.406；最不稳：`stale_hops` 0.248、`A_hops_citrus` 0.259
- 与 8.xlsx MDI Top-20 交集 **9 个**（方向一致但不可替代）
- 运行环境：`N_BOOT=30, TopK=10, 6 进程`，耗时 **118.1 s**（→ 200 次 × 50 维 ≈ 需 3–4 h，排期要算进去）

#### `q3_moo_gurobi.py`（🔴 结构性重写）

**可直接抄的结构**：

- `|x|` 线性化 `x = xp − xn`，`xp, xn ≥ 0`（第 166–167 行）
- big-M 稀疏化：`−M·y ≤ x ≤ M·y`（第 175–176 行）
- 偏差松弛：`expr − target = up − um`，`up, um ≥ 0`（第 179–181 行）
- ε-约束扫描外层（`solve_epsilon_constraint`，第 132–157 行）
- 上下界：`bounds = {lo: Xlog.quantile(.01), hi: Xlog.quantile(.99)}`（第 275 行）

**必改五处**：

1. 🔴 **硬约束只有 2 条**：第 295 行 `K_hard = [k for k in theta if k in ('DMS','X4VG')]`，其余全进 `K_soft`（含**双乙酰**）。队友论文写"3 个硬约束"是错的。→ 要么补双乙酰为硬约束，要么如实写"2 硬 1 软"并解释理由（例如双乙酰阈值中位 0.09 与均值 0.299 差 3 倍，取均值还是中位会翻转结论）。
2. 🔴 **阈值分位 = p95**（第 293 行 `Xlog[...].quantile(.95)`），不是论文写的 p90。→ 口径二选一，在论文里明写。
3. 🔴 **f1 的 L1/L2 必须在两分支间统一**。Gurobi 分支是 L1（`Σ w_s(u⁺+u⁻)`），降级分支是 L2（`Σ w_s(dev²)`），**两套数字永不可比**。
4. 🔴 **f3 必须在两分支间统一**。Gurobi 是 `Σγy + λΣ|x|`（γ=1，f3≥1），降级是 `λΣ|x|`（f3<1）。→ 统一后重跑，并**报 x=0 时的基线 f1**（L2 基线 1.0984 / L1 基线 5.7574），否则无法判断前沿点是否优于"什么都不改"。
5. 🔴 **`HAS_GUROBI=False` 时不得声称 MILP**。要么装 Gurobi 重跑，要么全程在论文里写"连续松弛 + L-BFGS-B"，并把 y_j 明确标注为"事后阈值化的伪二元变量（|x|>0.05），非优化变量"。

---

## 第 4 章 · 队友产出「可用 / 不可用」逐条判定

### 4.1 🟢 可直接用（判定依据已在本轮复现）

| 条目 | 出处 | 依据 |
|---|---|---|
| 量纲三分对拍**流程**（用 Calibrated 逐列中位相对误差判 log/linear） | `01_数据体检…md` T2、`04_Brainstorming` Ⅰ | 流程正确，只是**列数结论错**（见 4.2）；方法照抄，数字用本文件 1.3 |
| 4.csv 三假设检验**设计**（sd≠1 / 非离散 / 无 1/k 网格） | ebm T4、`04_Brainstorming` Ⅱ | 三条证据方向都对，sd 与取值数复现一致；1/k 数值按 1.9 更新 |
| 7.csv 才真 z 分数 | T4 | sd 中位 1.0030、164/186 列 sd>0.99 |
| `beer` 列作唯一对齐键 | T1 | 96 唯一 / 154 重复；1/4/7 `beer` 顺序全同 |
| 4.csv ↔ summary 后 20 列乱序（禁按位置拼） | T9 | 30 同 / **20 异**，精确一致 |
| 6.csv 实测 44×50 | T7 | 精确一致 |
| 2/5/6.csv 是 Spearman | T3 | 对角全 1、对称；与 `数据说明.txt` 一致 |
| 8.xlsx MDI/SHAP 是诱饵，只能当基线 | T13 | **SHAP 500×236 的 `base_prediction` 列必须剔除**（mean\|SHAP\| 最大） |
| 阈值单位不换算（OAV 同单位直接除） | T15 | 酿造学反证成立；DMS 17.25 µg/L、Diacetyl 0.299 mg/L、4VG 0.206 mg/L |
| 共表达图社区结构弱（1.56×）→ 改用 origin_paper 分组 | T16、`Q2_报告` S1 | 模块内 0.187 / 间 0.120；且 origin_paper 实测覆盖 **226/226** |
| **OAV 三档证据分级**（>1 可信 / 0.5–1 需解释 / <0.5 需化学论证） | `Q2_报告` S5、`04_Brainstorming` Ⅵ | 29 条可核验：超阈值 17、接近 7、远低 5。**主动否掉自己的结果是最高级可信度信号** |
| **ε-约束 + big-M + 龙卷风**设计 | `04_Brainstorming` Ⅷ、`06_Q3_Pareto与灵敏度.md` | 结构正确（只有实现有 bug） |
| **6 条最干净的归因**（见下表） | `Q2_报告` S4/S5 | π 与 OAV 双高，化学上讲得通 |
| **提交规范 20 条**（A1–A9 / B1–B5 / C1–C6） | `06_提交规范核对表.md` | 每条都有官方 PDF/DOCX 出处 |
| **AI 工具使用详情说明模板**（4 项内容 + 关键交互记录） | `01_文档/07_AI工具使用详情说明.md` | 直接对应 C5 要求 |
| **15 图 D-A-C 叙事结构** | `06_提交规范核对表.md` §三 | 每图都写了"为什么/说明什么/支撑什么" |
| **附录格式**（软件版本 + 复现命令 + 31 文件清单 + 核心脚本全文） | 队友附录 A/B | 对应 A8 要求 |

**6 条最干净归因（可直接作为 Q2 的锚点结论）**：

| 感官维度 | 化合物 | π | OAV | 化学意义 |
|---|---|---|---|---|
| `alcohol` | ethanol | **1.00** | 4.09 | 乙醇就是酒精感的物理来源 |
| `bitternes` | bitterness | **0.93** | 3.63 | 异构 α-酸（IBU）直接对应苦度 |
| `acidity` | lactic_acid | **0.99** | 0.33 | 乳酸是主要酸化剂；OAV<1 但感官上酸味有叠加效应 |
| `A_malt_all` / `F_malt_all` | color.EBC | **1.00** | — | 色度是麦芽焙烤程度的代理，与麦芽香气同步上升 |
| `sweetness` | GFS | **1.00** | 0.065 | GFS（发酵度）决定残糖；OAV 低是因为阈值表单位口径 |

> ⚠️ **范畴警告**：`protein.g.L.`、`color.EBC.`、`pH`、`iron`、`GFS`、`bitterness` 都是**理化指标**，不是"香气化合物"。
> 它们可以作**解释变量/机制代理**，但**不能写进"关键香气化合物 Top-3"**——这是队友 Q2 表里的范畴错误，必须改。

### 4.2 🔴 不可用（每条附复算证据）

| 条目 | 队友说法 | 实测/代码事实 | 证据位置 |
|---|---|---|---|
| **Q3 Pareto 表 4 个点 + 正文"基线 0.52"** | "Gurobi MILP，ε-约束扫出 4 个 Pareto 点" | f3 ∈ [0.046, 0.599] **全 <1**，而 Gurobi 分支 f3 ≥ 1（γ=1）；本机 `gurobipy` 未安装；f1 是 L2 尺度 | `q3_moo_gurobi.py:194, 225, 242`；见 2.4 |
| **"B = 40"** | 论文参数表 | 代码 `N_BOOT = 30` | `q2_pilot_v2.py:60` |
| **"198 列 log10 / 37 列还原"** | 论文"一句话卖点" | 198+33+5 = 236 ≠ 231；实测 **37/33/161** | 见 1.3 |
| **"38 维 R²>0"** | 论文 Q1 结论 | 逐维表复算 **41 / 50** | `Q1_报告.txt` §3 表 |
| **"三个硬约束"** | 论文 Q3 模型 | 代码 `K_hard` 只有 `DMS`、`X4VG` **2 个**；双乙酰在 `K_soft` | `q3_moo_gurobi.py:295-296` |
| **"90 分位"** | 论文 Q3 阈值 | 代码 `quantile(.95)` | `q3_moo_gurobi.py:293` |
| **"231 化合物"** | 多处 | 应为 **226 实测 + 5 派生** | 见 1.2 |
| **"origin_paper 命中 154/231"** | `Q2_报告` §0 | 归一化匹配后 **226/226** | 见 1.15 |
| **QWK = 0.4081** | 论文 Q1 指标 | 双重分位化后 ≈ Spearman，系统性虚高 | `q1_model.py:155-160`；见 §3 附 |
| **消融 0.1028 vs 5 折 0.1367** | 论文"消融验证有效" | 消融**只跑单折**，与 5 折不可比 | `Q1_报告.txt` §4 |
| **均值基线 Spearman = −0.0738** | 论文基线条 | 常量预测秩相关**无定义**（std=0） | `Q1_报告.txt` §3 |
| **"226 种啤酒"** | 题面（不是队友的错） | 250 行 | 1.2 |
| **把 protein/color/pH/iron/GFS/bitterness 当"关键化合物"** | Q2 Top-3 表 | **范畴错误**：理化指标 ≠ 香气化合物 | `Q2_报告` S4 |
| **"3.xlsx 每 sheet 54 条公式"** | T5 | 单张 54，**总数 1260** | 见 1.7 |
| **"1/k 网格 err ≈ 0.2 = 随机水平"** | T4 | 联合优化 μ,s 后残差为随机水平的 0.47–0.86，**尚未塌到 0 但也不是纯随机** | 见 1.9 |

### 4.3 🟡 可用作「上限参照」/「反例」

| 条目 | 怎么用 |
|---|---|
| GBR 平均 R² **0.2224**、ElasticNet **0.1367**、GBR 优于基线 **41/50** | 作"树模型 R²≈0.22 是本数据上限"的参照（呼应文献 [1] 的 0.21）。**必须自己重跑一遍确认**再写进论文 |
| 最强维 alcohol 0.730 / 最弱 F_esters_flower −0.080 | 可作"哪些维有信号"的预期；但 24 个 categorical 维拆分后数值会变 |
| Q2 试点 π 与 Jaccard（16 维 × 30 次） | 可作"B=200 时大概什么量级"的预期；**不能直接当结果** |
| 消融 0.0982 → 0.1028 | 只作"方向一致"旁证 |
| 15 图清单与 EDA 9 图清单 | 作**图型选择**的参考（skill 有 `references/chart-decision.md`，最终以那里为准） |
| 12 图 5 表规划 | 作 Step 5 的产出骨架 |

---

## 第 5 章 · 文献合并表（Step 4 用）

> 我方 11 条（`MathorCup_A_文献整理2026-10-24.md`，编号 [1]–[11]）
> ⊕ 队友 28 条（`01_文档/05_文献档案与参考文献.md`，编号 [1]–[28]，带证据等级）
> → 去重后 **27 条**（我方 [1] 与队友 [1]、[7]/[10] 与队友 [24] 等有重叠）。下表用**新编号 B1–B27**，抄进 `references.bib` 时重新排。

### 5.1 核心基准（Q1/Q2/Q3 共用，证据等级 **A**）

| 编号 | 文献 | 支撑哪一步 | 用法 |
|---|---|---|---|
| B1 | Schreurs et al. 2024, *Nature Communications* 15:2368 | 全文基准 | **直接应用证据**：同一数据集原始论文；R²≈0.21 的上限参照 |
| B2 | Meinshausen & Bühlmann 2010, *JRSS-B* 72(4):417-473 | Q2 稳定性选择 | **方法可迁移**：π 阈值可由 FDR 界反推 |
| B3 | Strobl et al. 2008, *BMC Bioinformatics* 9:307 | Q2 条件置换 | **方法可迁移**：相关特征下普通置换会失真 |
| B4 | Langfelder & Horvath 2008, *BMC Bioinformatics* 9:559 | Q2 软阈值 WGCNA | **方法可迁移**：β 扫描 |
| B5 | Ahn et al. 2011, *Scientific Reports* 1:196 | Q2 风味网络 | **方法可迁移**：食材共现网络思路 |
| B6 | Barber & Candès 2015, *Ann. Statist.* 43(5):2055-2085 | Q2 FDR 控制 | **方法可迁移**：knockoff |

### 5.2 Q1 相关

| 编号 | 文献 | 等级 | 用法 |
|---|---|---|---|
| B7 | Cohen 1968, *Psychological Bulletin* 70(4):213-220 | C | **直接应用**：加权 kappa 定义（QWK 的出处） |
| B8 | van Buuren & Groothuis-Oudshoorn 2011, *JSS* 45(3) | C | 方法可迁移：MICE 插补 |
| B9 | Stekhoven & Bühlmann 2012, *Bioinformatics* 28(1):112-118 | C | 方法可迁移：MissForest |
| B10 | Wold et al. 2001, *Chemom. Intell. Lab. Syst.* 58(2):109-130 | C | 方法可迁移：PLS 化学计量学基线 |
| B11 | Zou & Hastie 2005, *JRSS-B* 67(2):301-320 | C | **直接应用**：ElasticNet |
| B12 | Hastie et al. 2009, *ESL*, Springer（书，需页码） | C | 方法可迁移：GBR / 交叉验证 |

### 5.3 Q2 相关

| 编号 | 文献 | 等级 | 用法 |
|---|---|---|---|
| B13 | Lundberg & Lee 2017, *NeurIPS* 30:4765-4774 | A | **方法可迁移**：SHAP（**只保证模型内归因，不是因果**） |
| B14 | Grosch 1994, *Flavour Fragr. J.* 9(2) | C | **直接应用**：OAV = 浓度/阈值 的定义 |
| B15 | Kishimoto et al. 2018, *J. Biosci. Bioeng.* 126(3):330-338 | C | **直接应用**：76 个气味活性物可重建 Pilsner 香气 |
| B16 | Kursa & Rudnicki 2010, *JSS* 36(11) | C | 方法可迁移：Boruta 全相关特征选择 |

### 5.4 Q3 相关

| 编号 | 文献 | 等级 | 用法 |
|---|---|---|---|
| B17 | Xu et al. 2019, *NeurIPS* 32:7335-7345（CTGAN/TVAE） | A | 方法可迁移：条件生成；**只作对照，250 样本不适用** |
| B18 | Kotelnikov et al. 2023, *ICML* 202（TabDDPM） | A | 同上；**只作对照** |
| B19 | Snoek et al. 2012, *NeurIPS* 25:2951-2959 | A | 方法可迁移：贝叶斯超参优化 |
| B20 | Deb et al. 2002, *IEEE TEC* 6(2):182-197（NSGA-II） | C | 方法可迁移：与 ε-约束互证 |
| B21 | Mavrotas 2009, *Appl. Math. Comput.* 213(2):455-465 | C | **直接应用**：ε-约束法 + AUGMECON |
| B22 | Sánchez-Lengeling & Aspuru-Guzik 2018, *Science* 361(6400):360-365 | C | 方法可迁移：逆向设计框架 |
| B23 | Ledoit & Wolf 2004, *J. Multivariate Anal.* 88(2):365-411 | C | **直接应用**：收缩协方差（小组生成） |
| B24 | Boyd & Vandenberghe 2004, *Convex Optimization*, CUP（书） | C | 方法可迁移：凸性判断 |

### 5.5 工具与数据

| 编号 | 资源 | 用法 |
|---|---|---|
| B25 | Gurobi Optimization LLC, *Reference Manual* | **直接应用**：多目标仅支持线性目标（这是选 ε-约束的技术理由） |
| B26 | Pedregosa et al., scikit-learn 文档 | 方法可迁移 |
| B27 | Schreurs et al., Zenodo `records/10653704` | **直接应用**：数据来源 |

### 5.6 合并时必须做的三件事

1. **核 DOI**：B1–B27 里有 8 条我方/队友都没给 DOI，Step 4 要补；补不到的**降为"网络资源"格式**，不要伪造。
2. **标"不可照搬的结论"**：B17/B18 都是大数据集验证的生成模型，**250 样本 / 22 类 / 最小 3 例不适用**——这句话必须出现在论文的局限性里，否则等于自曝"照搬"。
3. **按正文引用次序重排编号**（官方 A6 要求），不能直接用 B1–B27 的顺序。

---

## 第 6 章 · 提交与 AI 合规（Step 11 / G6 用）

### 6.1 可勾选清单（从队友 20 条转写）

**A. 论文格式（9 条）**

- [ ] A1 赛道与内容一致（A 题）
- [ ] A2 第一页 = 题目 + 摘要 + 关键词；第二页 = 目录；目录后起正文
- [ ] A3 正文起编页码，页脚居中，阿拉伯数字从 1 连续
- [ ] A4 无页眉；无姓名/学校等身份信息
- [ ] A5 中文；正文 **≤30 页**（附录不限）
- [ ] A6 正文标注 + 参考文献列出；书籍注明页码；按**引用次序**编号
- [ ] A7 参考文献按书籍 / 期刊 / 网络资源三种格式
- [ ] A8 附录含**软件名称、命令、全部源程序**
- [ ] A9 排版美观（字号不做统一要求）

**B. 提交（5 条）**

- [ ] B1 电子版论文 + 承诺书 + 支撑材料 + 计算结果
- [ ] B2 论文 PDF，命名 `A<队号>.pdf`
- [ ] B3 承诺书每名队员签名后转 PDF，命名 `A<队号>承诺书`
- [ ] B4 支撑材料打包 `A<队号>附件.zip`（或 .rar）
- [ ] B5 题面未要求单独交计算结果文件 → 按"不适用"处理，但在 README 里写明

**C. AI 工具使用规定（6 条）**

- [ ] C1 核心建模/算法/求解/分析由队员独立完成（写明"未使用环节"）
- [ ] C2 对 AI 生成内容负责，须验证并修正（**要写出实际修正了什么**）
- [ ] C3 在**参考文献之后**声明并详述
- [ ] C4 参考文献列出 AI 工具：`[编号] 工具名, 版本/型号, 开发机构, 使用日期`
- [ ] C5 支撑材料附《AI 工具使用详情说明》PDF（四要素：工具/环节/关键提示词与回复/采纳与修改）
- [ ] C6 程序注释说明 AI 辅助；**图表处注明 AI 贡献**

### 6.2 队号到手后必须改名的三个文件

| 现名 | 改成 |
|---|---|
| `draft.pdf`（任意当前稿） | `A<队号>.pdf` |
| `承诺书.pdf` | `A<队号>承诺书.pdf` |
| `支撑材料.zip` | `A<队号>附件.zip` |

### 6.3 本轮新增的合规建议（队友没写的）

- **把 `verify_facts.py` 及其输出报告放进支撑材料**，作为"数据口径结论可复现"的硬证据
- **每个"不可用判定"都要在论文里体现为"我们核验后发现了差异"**——主动暴露并修正队友/题面的错误，是 AIGC 检测最强的反证
- **图注末尾统一加**：「（本图由 `figXX.py` 生成，AI 辅助绘制，数据与结论经队员核验）」——对应 C6

---

## 第 7 章 · 执行顺序（与 skill 的 Gate 严格对齐）

```
G1  Step 0  收比赛信息与格式要求      → requirements.md
    Step 1  选/建论文模板              → paper/  编译通过
    Step 2  数据体检                  → 用本文件第 1 章，跑 verify_facts.py
    Step 3  审题拆解                  → problem_analysis.json + 依赖 DAG
    Step 4  文献检索                  → 第 5 章合并表 → references.bib
         🔴 CHECKPOINT：人工确认
G2  Step 5  创新探索                  → 8 个创新点 + 补标五大路径
    Step 6  模型大纲                  → model_route.json + rubric_alignment.json
         🔴 CHECKPOINT：人工确认（f1/f3 形式在此定死）
G3  Step 7  代码求解                  → q1/q2/q3 + quality_notes.md
    Step 7.2 流程图                   → fireworks-tech-graph
         🔴 CHECKPOINT：人工确认
G4  Step 7.3 稳健性                   → robustness/Qx/*.md（逐问必做，缺一即失败）
    Step 7.4 证据索引
    Step 7.5 QA 门禁                  → qa_report.json
         🔴 CHECKPOINT：结果冻结
G5  Step 8  论文撰写                  → 从冻结结果写，不从记忆写
    Step 8.5 附录代码
    Step 9  文献标注
G6  Step 10 学术润色                  → changelog.md
    Step 11 收尾与终验                → 提交包 + 验证报告
         🔴 CHECKPOINT：交付确认
```

### 硬前置关系

1. **Q1 标签反演不落地 → Q2/Q3 全部悬空**（Q2 的标签、Q3 的代理模型都依赖它）
2. **Step 2 的量纲口径不定 → Q1 必错**（33 列做 10^x 会爆到 1e12596）
3. **24 个 categorical 维不拆分 → Q1 指标全错**（这是队友两版文档都漏掉的）
4. **f1 的 L1/L2 形式不定 → Q3 数字永不可比**（这是 2.4 事故的根因）
5. **Step 6 不做完就开始 Step 7 → 一定返工**（队友就是直接跳到了 Step 7）

### 建议排期（在队友 11 天估计基础上压缩）

| 阶段 | 内容 | 估计 |
|---|---|---|
| G1 | Step 0–4 | 1 天（材料已齐） |
| G2 | Step 5–6 | 0.5 天 |
| G3 | Step 7–7.2（Q1/Q2/Q3 全重跑，B=200） | 2 天（Q2 bootstrap 需 3–4 h 纯算力） |
| G4 | Step 7.3–7.5 | 1 天 |
| G5 | Step 8–9 | 1.5 天 |
| G6 | Step 10–11 | 0.5 天 |
| **合计** | | **6.5 天** |

---

## 附录 A · 与本文件相关的其他文件

| 文件 | 关系 |
|---|---|
| `verify_facts.py` | 第 1 章全部数字的复现脚本（140 项断言） |
| `verify_facts_report.md` | 上述脚本的输出（140/140 OK） |
| `mathorcup.md` | 主建模参考；第 2 部分 8 章 → 本文件 Step 6 的骨架来源 |
| `2026A题坑点汇总.md` | 16 条坑；本文件第 1/2 章已全部吸收并修正量化 |
| `MathorCup_A_文献整理2026-10-24.md` | 11 条文献；已并入第 5 章 |
| `A题_Markdown版/` | 队友文档；判定见第 3/4 章 |
| `A2600001附件/` | 队友结果与脚本；判定见第 3/4 章 |

**以上五份源文件均未被修改**（只读引用）。
