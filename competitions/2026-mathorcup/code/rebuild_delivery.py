# -*- coding: utf-8 -*-
"""重建全部交付物：支撑材料包 + 交付总包，并解压实测。

结构：
  dist/MathorCup2026A_支撑材料/   选题提交用
  dist/交付包_20261030/           内部交付（论文源码 + 修复说明 + 核查回应）
"""
import io
import os
import shutil
import sys
import zipfile

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.getcwd()
DIST = os.path.join(ROOT, 'dist')
SUP = os.path.join(DIST, 'MathorCup2026A_支撑材料')
PKG = os.path.join(DIST, '交付包_20261030')

# 核心求解脚本（按论文编号）
CODE = ['q0_relations.py', 'q1.py', 'q1_helpers.py', 'q1_grades.py',
        'q1_diagnostics.py', 'q1_ablation_231.py', 'q2.py', 'q2_graph.py',
        'q2_consensus.py', 'q2_confident.py', 'q3.py', 'q3_transfer.py',
        'robustness_q3.py', 'nsga2.py', 'selftest.py']
PLOT = ['figures.py']

print('=' * 60)
print('① 清空并重建支撑材料目录')
for d in (SUP,):
    if os.path.isdir(d):
        shutil.rmtree(d)


def copytree(src, dst, skip=()):
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        if name in skip:
            continue
        s, t = os.path.join(src, name), os.path.join(dst, name)
        if os.path.isdir(s):
            copytree(s, t, skip)
        else:
            shutil.copy2(s, t)


# ---- 代码
os.makedirs(os.path.join(SUP, 'code', '绘图'), exist_ok=True)
n_code = 0
for f in CODE:
    p = os.path.join(ROOT, 'code', f)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(SUP, 'code', f))
        n_code += 1
    else:
        print(f'  ! 缺 {f}')
for f in PLOT:
    p = os.path.join(ROOT, 'code', f)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(SUP, 'code', '绘图', f))
        n_code += 1
print(f'  代码 {n_code} 个')

# ---- 结果
copytree(os.path.join(ROOT, 'results'), os.path.join(SUP, 'results'))
n_res = sum(len(fs) for _, _, fs in os.walk(os.path.join(SUP, 'results')))
print(f'  结果 {n_res} 个文件')

# ---- 图
copytree(os.path.join(ROOT, 'latex模板', 'figures'), os.path.join(SUP, 'figures'))
n_fig = sum(len(fs) for _, _, fs in os.walk(os.path.join(SUP, 'figures')))
print(f'  图 {n_fig} 个文件')

# ---- 附件
copytree(os.path.join(ROOT, '附件'), os.path.join(SUP, '附件'))
print('  附件已复制')

# ---- 论文 PDF
os.makedirs(os.path.join(SUP, '论文'), exist_ok=True)
shutil.copy2(os.path.join(ROOT, 'latex模板', 'main.pdf'),
             os.path.join(SUP, '论文', 'main.pdf'))
for cand in ('AI工具使用说明.pdf', 'AI使用说明.pdf', 'AI说明.pdf'):
    p = os.path.join(ROOT, 'latex模板', cand)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(SUP, '论文', cand))
        break
print('  论文 PDF 已复制')

# ---- 文档
DOCS = ['修复说明_问题一预处理.md', '修复说明_问题三目标口径.md',
        'docs/修复说明_问题一预处理.md']
for d in DOCS:
    p = os.path.join(ROOT, d)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(SUP, os.path.basename(d)))
        print(f'  + {os.path.basename(d)}')

# ---- README
readme = r'''# 2026 MathorCup 大数据 · 赛道 A · 支撑材料

**题目**：啤酒风味代谢数据的感官预测、关键化合物归因与受约束配方重构

## 目录

| 目录 | 内容 |
|---|---|
| `论文/` | 论文 PDF + AI 工具使用说明 |
| `code/` | 求解脚本（`q0`–`q3` 及衍生分析、`selftest.py`） |
| `code/绘图/` | `figures.py`，一键重画全部 21 张图 |
| `results/` | 全部运行结果（CSV / JSON），论文所有数字的唯一来源 |
| `figures/` | 21 张图的 PNG 与 SVG |
| `附件/` | 赛题附件 1–8 |

## 复现

```bash
python code/selftest.py        # 自检：数据读入 + 脚本可导入
python code/q0_relations.py    # ~10 s
python code/q1.py              # ~394 s（嵌套交叉验证）
python code/q1_grades.py       # ~5 s
python code/q2.py              # ~60 s
python code/q3.py              # ~50 s
python code/robustness_q3.py   # ~13 s
python code/绘图/figures.py    # ~40 s，21 图
```

依赖：Python 3.13 + numpy / pandas / scipy / scikit-learn / matplotlib /
networkx / openpyxl / seaborn。Gurobi 可选，缺失时 `q3.py` 自动回退到
`scipy.optimize.milp`。

## 复现的注意点

1. **q3 的 PLS 代理必须把训练集裁到 MILP 可行域 `[p1, p99]`**。
   `X2.methyltetrahydrofuran.3.one` 的 std 是 795、max 12596，
   不裁会让线性浓度列独占协方差，成分数塌缩、CV $R^2$ 转负。
   主脚本与 `robustness_q3.py` 都已裁。
2. **q3 的目标函数、$\varepsilon_3$ 约束、`metrics_of` 三处必须同用 `lam * wj`**。
   任一处漏掉 $w_j$ 都会让"求解的目标"≠"报告的 $f_3$"。
3. **q1 的预处理必须在内层训练折内估参**（中位数填补 + 标准化），
   且缺失值不能当真值 0 参与标准差计算。

## 主要结果

| 项 | 值 |
|---|---|
| Q1 嵌套 CV $R^2$ | 中位 0.1469，均值 0.2223 |
| Q1 分级 QWK | 0.3400（精确同档 0.3812） |
| Q2 Top-3 归因 | 150 项中非香气混入 0 |
| Q2 阈值入选 | $\pi \ge 0.5022$ 共 10 条 |
| Q3 Pareto 点 | 7 个（$f_1$ 20.2063 – 47.2083） |
| Q3 最优 $f_1$ | 20.2063（基线 48.9620，降 58.7%） |
| Q3 支配 NSGA-II | 92.17%（106/115），超体积 757.78 对 299.12 |
| Q3 跨风格迁移 | 47.1450 → 13.1366，降 72.14% |
'''
io.open(os.path.join(SUP, 'README.md'), 'w', encoding='utf-8').write(readme)

listing = ['# 代码清单', '',
           '| 文件 | 作用 | 主要输出 |', '|---|---|---|']
DESC = {
    'q0_relations.py': ('附件间相关矩阵对拍、量纲域判定',
                        'q0_summary.json'),
    'q1.py': ('嵌套交叉验证 + 四模型竞速 + 区间估计',
              'q1_metrics.csv、q1_predictions.csv、q1_run_log.json'),
    'q1_helpers.py': ('Q1 共用工具（树模型封装、自助区间）', '—'),
    'q1_grades.py': ('连续强度→等级的分位映射与 kappa',
                     'q1_grades.csv、q1_grade_summary.json'),
    'q1_diagnostics.py': ('残差结构、左尾分析、外部效度', 'q1_residual_stats.csv、q1_external.csv'),
    'q1_ablation_231.py': ('226 vs 231 列消融', 'q1_ablation.csv'),
    'q2.py': ('逐列置换重要性 + 入选频率 + 浓度阈值比分级',
              'q2_top3.csv、q2_pi.csv、q2_run_log.json'),
    'q2_graph.py': ('共表达图社区诊断', 'q2_graph.json'),
    'q2_consensus.py': ('三模型族跨模型平均排名', 'q2_consensus.csv'),
    'q2_confident.py': ('置信化合物集', 'q2_confident.csv'),
    'q3.py': ('收缩高斯生成 + PLS 代理 + ε-约束 MILP',
              'q3_pareto.csv、q3_deltas.csv、q3_run_log.json'),
    'q3_transfer.py': ('Pils/Lager → Tripel 跨风格迁移', 'q3_transfer_*.csv/json'),
    'robustness_q3.py': ('六参数单因素扰动、27 次重解',
                         'q3_sensitivity*.csv/json'),
    'nsga2.py': ('手写 NSGA-II 对照', 'q3_compare.json'),
    'selftest.py': ('自检：数据读入 + 全部脚本可导入', '—'),
    '绘图/figures.py': ('21 张图（PNG + SVG）', 'figures/'),
}
for f in CODE + PLOT:
    d, o = DESC.get(f, ('—', '—'))
    listing.append(f'| `{f}` | {d} | `{o}` |')
io.open(os.path.join(SUP, '代码清单.md'), 'w', encoding='utf-8').write('\n'.join(listing))

# ---- 打包支撑材料
zsup = os.path.join(DIST, 'MathorCup2026A_支撑材料.zip')
if os.path.exists(zsup):
    os.remove(zsup)
with zipfile.ZipFile(zsup, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for base, _, fs in os.walk(SUP):
        for f in fs:
            p = os.path.join(base, f)
            z.write(p, os.path.join('MathorCup2026A_支撑材料',
                                    os.path.relpath(p, SUP)))
print(f'  → {os.path.basename(zsup)}  {os.path.getsize(zsup)/1e6:.1f} MB')

print('=' * 60)
print('② 重建交付总包')
if os.path.isdir(PKG):
    def _force(func, path, exc):
        os.chmod(path, 0o666)
        func(path)
    shutil.rmtree(PKG, onexc=_force) if sys.version_info >= (3, 12) \
        else shutil.rmtree(PKG, onerror=_force)
os.makedirs(PKG)

# 01 论文源码
copytree(os.path.join(ROOT, 'latex模板'), os.path.join(PKG, '01_论文源码'),
         skip=('main.aux', 'main.log', 'main.out', 'main.toc',
               '_backup_tex', 'sections.bak', '_archive'))
n_tex = sum(len(fs) for _, _, fs in os.walk(os.path.join(PKG, '01_论文源码')))
print(f'  01_论文源码  {n_tex} 个文件')

# 02 支撑材料（整包解压进去）
copytree(SUP, os.path.join(PKG, '02_支撑材料'))
print('  02_支撑材料  已复制')

# 03 修复说明
os.makedirs(os.path.join(PKG, '03_修复说明'), exist_ok=True)
for src in ('修复说明_问题一预处理.md', '修复说明_问题三目标口径.md',
            '修订计划_第三轮.md', '论文核对清单_审计19项.csv',
            '论文核对清单_逐维R2.csv', '论文核对清单_派生统计量.csv'):
    for base in ('docs', ''):
        p = os.path.join(ROOT, base, src)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(PKG, '03_修复说明', src))
            break
    else:
        print(f'  ! 缺 {src}')
print(f'  03_修复说明  {len(os.listdir(os.path.join(PKG, "03_修复说明")))} 个文件')

# 04 核查回应
d4 = os.path.join(PKG, '04_核查回应')
os.makedirs(d4, exist_ok=True)
for f in ('六条意见判定.md', '问题核对_35条.md',
          '问题一_内层交叉验证预处理核查.md',
          '问题二_FDR统计解释核查.md', '论文第二轮_问题诊断报告.md'):
    for base in (os.path.join(ROOT, 'docs'), ROOT):
        p = os.path.join(base, f)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(d4, f))
            break
n4 = len(os.listdir(d4))
print(f'  04_核查回应  {n4} 个文件')

# 05 工具
d5 = os.path.join(PKG, '05_工具')
os.makedirs(d5, exist_ok=True)
for f in ('audit_paper.py', 'build_paper.py', 'make_checklist.py',
          'diff_fix.py', 'verify_consistency.py', 'table5_values.py'):
    p = os.path.join(ROOT, 'code', f)
    if not os.path.exists(p):
        p = os.path.join(ROOT, 'code', 'tools', f)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(d5, f))
print(f'  05_工具  {len(os.listdir(d5))} 个文件')

# 00 先看这里
top = r'''# 2026 MathorCup 大数据 · 赛道 A · 交付包

**打包日期**：2026-10-30
**论文**：啤酒风味代谢数据的感官预测、关键化合物归因与受约束配方重构

## 目录

| 目录 | 内容 | 什么时候用 |
|---|---|---|
| `01_论文源码/` | LaTeX 全套（`main.tex`、`sections/`、`figures/`、`main.pdf`） | 改正文 |
| `02_支撑材料/` | 代码 + 结果 + 图 + 附件 + 论文 PDF | **提交的就是这个** |
| `03_修复说明/` | 问题一（内层预处理）与问题三（目标口径）两处修复的完整说明，含"论文里要改哪个数字" | 对账 |
| `04_核查回应/` | 六条核查意见判定 + 35 条诊断报告核对 | 和老师/队友对账 |
| `05_工具/` | 审计、编译、核对清单生成脚本 | 自己复算 |

## 状态

编译：53 页，0 error，0 overfull，正文 30 页（赛规上限）。
审计：`05_工具/audit_paper.py` **126 / 126 通过**。

## 三轮修复的净效果

| 项 | 修前 | 修后 |
|---|---:|---:|
| Q1 $R^2$ 中位 | 0.1471 | **0.1469** |
| Q1 QWK | 0.3433 | **0.3400** |
| Q3 Pareto 点 | 5 | **7** |
| Q3 最优 $f_1$ | 23.8519 | **20.2063** |
| Q3 降幅 | 51.3% | **58.7%** |
| Q3 支配 NSGA-II | 91.30% | **92.17%** |
| Q3 超体积 | 688.54 | **757.78** |

## 队友最需要看的两份

1. `03_修复说明/修复说明_问题三目标口径.md` —— 表 12 整表换、表 15 整表换、正文 5 个数字、6 张图重画
2. `03_修复说明/修复说明_问题一预处理.md` —— 表 5、表 6 与 6.x 的 19 处数字

## 环境

Python 3.13 + numpy / pandas / scipy / scikit-learn / matplotlib /
networkx / openpyxl / seaborn。Gurobi 可选（缺失自动回退 `scipy.optimize.milp`）。

编译：TeX Live 2026 的 xelatex，跑三遍。
'''
io.open(os.path.join(PKG, '00_先看这里.md'), 'w', encoding='utf-8').write(top)

# ---- 打包总包
zpkg = os.path.join(DIST, '交付包_20261030.zip')
if os.path.exists(zpkg):
    os.remove(zpkg)
with zipfile.ZipFile(zpkg, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for base, _, fs in os.walk(PKG):
        for f in fs:
            p = os.path.join(base, f)
            z.write(p, os.path.join('交付包_20261030',
                                    os.path.relpath(p, PKG)))
print(f'  → {os.path.basename(zpkg)}  {os.path.getsize(zpkg)/1e6:.1f} MB')

print('=' * 60)
print('③ 统计')
for name, path in (('支撑材料', SUP), ('交付总包', PKG)):
    n = sum(len(fs) for _, _, fs in os.walk(path))
    print(f'  {name}: {n} 文件')
