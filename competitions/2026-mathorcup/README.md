# 2026 MathorCup 大数据竞赛 · 赛道 A

**题目**：啤酒风味代谢数据的感官预测、关键化合物归因与受约束配方重构
**状态**：53 页 / 正文 31 页（**超赛规上限 1 页，待压**）/ 0 error 0 overfull / `audit_paper.py` 126-126
**队号**：待填（`paper/main.tex` 与 AI 声明里的 `MCB260XXXX`）

---

# 队友先看这里

**你负责的只有一件事：改图的画法。** 数字我已经全部重算过，图的**内容**不用你动，`code/figures.py` 直接从 `results/` 读数，没有一处硬编码。

## 你的四步

### 第 1 步：拉代码

```bash
git clone https://github.com/LESIMP-star/mathmodel-competitions.git
cd mathmodel-competitions/competitions/2026-mathorcup
git checkout -b feat/<你的名字>-figures
```

### 第 2 步：读两个文件

先读 `docs/队友任务_改画图逻辑.md`，里面按 A/B/C 三类列了 4 处必改、6 处建议改、4 处**不要改回去**的地方。

再读 `code/figures.py` 开头的 docstring，那里有一张「哪个函数画哪张图」的索引表。

### 第 3 步：改完重画

```bash
python code/figures.py
# 期望输出：共 21 图 / 42 个文件 → paper/figures/
```

**只改 `code/figures.py`，不要改 `paper/sections/*.tex`。** 正文文字由另一个人改，同一时间改会冲突。

### 第 4 步：自检再提 PR

```bash
python code/tools/audit_paper.py     # 必须 126/126
cd paper && xelatex -interaction=nonstopmode main.tex   # 跑 3 遍，必须 0 error
```

`audit_paper.py` 会核对「图上/正文里的数字」和 `results/` 是否一致。**它报错说明图画错了，不是你代码写错。**

---

## 四个「不要改回去」

这四条是前几轮反复调出来的，改回去评审会直接看出来：

| # | 规则 | 为什么 |
|---|---|---|
| 1 | **图内不要加总标题** | `code/_notitle.py` 负责屏蔽 matplotlib 默认标题，**这个文件不能删、import 不能动** |
| 2 | **子图标题只写 `(a)`/`(b)`** + 三五个字 | "(a) 真实缺失列" 可以，"(a) 真实缺失列（含 LOD）" 不行——括号说明一律移到图注 |
| 3 | **参考线用图例，不要在图上写字** | `fig_q1_r2_dist` 原来在图内旋转 90° 写"中位数 0.1469"，遮挡严重，已改成 `Line2D` 图例 |
| 4 | **A1 附录的分级大表是 25 列 × 2 张** | 试过合成一张 50 列，`	iny` + `	abcolsep 0.8pt` 仍超宽 325pt |

---

## 画图时的锚点数字

改图过程中如果你要确认某个数对不对，以下表为准。**如果图和这张表不一致，是图错了。**

| 指标 | 值 | 来源 |
|---|---:|---|
| Q1 R² 中位 / 均值 | 0.1469 / 0.2223 | `results/q1_run_log.json` |
| Q1 QWK | 0.3400 | `results/q1_grade_summary.json` |
| Q2 阈值 / 入选条数 | 0.5022 / 10 | `results/q2_run_log.json` |
| Q3 Pareto 点数 | 7 | `results/q3_pareto.csv` |
| Q3 最优 f1 | 20.2063 | 同上 |
| Q3 基线 f1 | 48.9620 | `results/q3_run_log.json` |
| Q3 降幅 | 58.7% | 计算 |
| Q3 支配 NSGA-II | 92.17%（106/115） | `q3_run_log.json` → `compare` |
| Q3 超体积 | 757.78 对 299.12 | 同上 |
| Q3 迁移降幅 | 72.14% | `results/q3_transfer_run_log.json` |
| γ 灵敏度极差 | 21.5730 | `results/q3_sensitivity_span.csv` |

---

## 目录

```
competitions/2026-mathorcup/
├── code/        16 个求解脚本（q0 → q1 → q2 → q3）+ 审计/构建工具
├── paper/       LaTeX 源 + 编译好的 main.pdf
│   ├── sections/  16 个章节 tex
│   └── figures/   42 个图文件（21 张 × PNG + SVG）
├── results/     76 个结果文件，论文每个数字的源头
└── docs/        修复说明、核对清单、队友任务、赛题要求核对表
```

`docs/` 里给你的是这两份：

- `队友任务_改画图逻辑.md` —— 具体改哪几处
- `赛题要求核对表.md` —— 题面 15 条要求逐条核对（13 完成 / 2 有偏差），改图时能对照

---

## 六条数据口径（别改错）

1. **化学维数是 231**，不是 226。附件2 是 231×231 相关矩阵，含 5 个派生总量。226 只作消融对照。
2. **样本量是 250**。题面「226 种啤酒」是笔误。
3. **附件4 不是 0–6 整数**，是按品评员 z-score 后再按啤酒平均的连续强度。
   所以负值 = 低于该品评员的平均，**不是"没有尝到"**；全文用"左尾"不用"未感知"。
4. **缺失有两种**：`-1.817819` 是检出限地板值（保留），`NaN` 是真缺失（按列中位数填补）。
   地板值占比 ≥30% 的列是 **40 列**（不是 34）。
5. **Q3 的 PLS 训练集必须裁到 `[p1,p99]`**，否则线性浓度列独占协方差，成分数塌到 2。
6. **Q3 的 `f3` 三处必须同用 `lam * wj`**：目标向量 `c`、`ε3` 约束、`metrics_of`。
   任一处漏 `wj` 就会让"求解的目标"≠"报告的 f3"。

---

## 别的分工

| 谁 | 负责 |
|---|---|
| 队友（你） | **只改 `code/figures.py`** 的画法 |
| 另一人 | 改 `paper/sections/*.tex` 的表述 |
| 已完成 | 全部数值修正、Q1 预处理修复、Q3 目标口径修复、21 图按新结果重绘 |

改代码前跑一次：

```bash
python code/audit_consistency.py   # 全链路口径一致性，必须 0 不一致
```
