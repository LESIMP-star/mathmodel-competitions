# -*- coding: utf-8 -*-
"""把干净版本推到 mathmodel-competitions 仓库的 competitions/2026-mathorcup/。

只放：代码、结果、论文源、图、文档。
不放：赛题原始数据（附件/）、生成物（dist/）、归档区。
"""
import io
import os
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = r'E:\hermes\.hermes\cache\scratch\repo_push'
REPO = 'https://github.com/LESIMP-star/mathmodel-competitions.git'
DEST = os.path.join(WORK, 'competitions', '2026-mathorcup')

# ── 清空工作副本
if os.path.isdir(WORK):
    shutil.rmtree(WORK)
subprocess.run(['git', 'clone', REPO, WORK], check=True,
               capture_output=True)
print(f'✓ clone {REPO}')

os.makedirs(DEST, exist_ok=True)


def cp_tree(src, dst, skip=()):
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in os.listdir(src):
        if f in skip:
            continue
        s = os.path.join(src, f)
        d = os.path.join(dst, f)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copy2(s, d)
        n += 1
    return n


# ── 1. code/
n = cp_tree(os.path.join(ROOT, 'code'), os.path.join(DEST, 'code'))
print(f'✓ code/  {n} 项')

# ── 2. results/（排除大日志）
RES_DST = os.path.join(DEST, 'results')
os.makedirs(RES_DST, exist_ok=True)
SKIP_EXT = ('.log',)
n = 0
for f in os.listdir(os.path.join(ROOT, 'results')):
    if f.endswith(SKIP_EXT) or f == '__pycache__':
        continue
    shutil.copy2(os.path.join(ROOT, 'results', f), os.path.join(RES_DST, f))
    n += 1
print(f'✓ results/  {n} 个文件（跳过 .log）')

# ── 3. paper/
PAPER = os.path.join(DEST, 'paper')
os.makedirs(PAPER, exist_ok=True)
for f in ('main.tex', 'references.tex', 'README.md', 'build_paper.bat'):
    s = os.path.join(ROOT, 'latex模板', f)
    if os.path.exists(s):
        shutil.copy2(s, os.path.join(PAPER, f))
for d in ('sections', 'figures'):
    shutil.copytree(os.path.join(ROOT, 'latex模板', d),
                    os.path.join(PAPER, d), dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '_bak*'))
shutil.copy2(os.path.join(ROOT, 'latex模板', 'main.pdf'),
             os.path.join(PAPER, 'main.pdf'))
print(f'✓ paper/  tex {len(os.listdir(os.path.join(PAPER, "sections")))} 个 + '
      f'图 {len(os.listdir(os.path.join(PAPER, "figures")))} 个 + main.pdf')

# ── 4. docs/
DOCS = os.path.join(DEST, 'docs')
os.makedirs(DOCS, exist_ok=True)
n = 0
for f in ('问题核对_35条.md', '修订计划_第三轮.md', '整理说明.md',
          '2026A题坑点汇总.md', 'A题_素材总纲.md',
          'MathorCup_A_文献整理2026-10-24.md', '交接文档.md'):
    s = os.path.join(ROOT, f)
    if os.path.exists(s):
        shutil.copy2(s, os.path.join(DOCS, f))
        n += 1
# 赛题 PDF 也放 docs（.gitignore 允许 docs/**/*.pdf）
shutil.copy2(os.path.join(ROOT, '2026年MathorCup大数据挑战赛-赛道A初赛.pdf'),
             os.path.join(DOCS, '赛题原文.pdf'))
print(f'✓ docs/  {n + 1} 个文件')

# ── 5. 比赛 README
README = '''# 2026 MathorCup 大数据竞赛 · 赛道 A

**题目**：啤酒风味代谢数据的感官预测、关键化合物归因与受约束配方重构
**状态**：论文正文 30 页（上限 30），0 error 0 overfull，`audit_paper.py` 126/126 通过
**队号**：待填（`paper/main.tex` 与 AI 说明里的 `MCB260XXXX`）

---

## 目录

```
competitions/2026-mathorcup/
├── code/            16 个核心求解脚本（q0 → q1 → q2 → q3 → figures）
│   └── tools/       10 个审计/构建脚本（改论文和核数用）
├── paper/           LaTeX 源 + 编译好的 main.pdf
│   ├── main.tex     主文件（\\frontpage 封面逐坐标校准过，别动）
│   ├── sections/    15 个章节 tex
│   └── figures/     43 个图文件（21 张 × PNG + SVG）
├── results/         80 个结果文件，**论文每个数字的源头**
└── docs/            问题核对、修订记录、坑点汇总、赛题原文
```

---

## 先读这个：`docs/问题核对_35条.md`

第二轮诊断报告提了 35 条问题。逐条核对的结果：

- **17 条真问题且仍未修**（其中 4 条最严重，见下）
- **9 条真问题但已修**（报告审的是 10-29 旧版）
- **9 条误报或夸重**

### 四条必须先处理的

| # | 问题 | 位置 |
|---|---|---|
| 1 | 0–6 分级：真值与预测各自重排，`median_tv_dist` 恒为 0。按论文所写规则重算是 QWK 0.2978 / 25 项，不是 0.3400 / 34 项 | `code/q1_grades.py:170-171` |
| 2 | 式(15) 写 $f_3=\\sum|x-x_0|$，代码是 $\\gamma\\sum y+\\lambda\\sum w|\\Delta|$，表 12 的 f3 主要是改动个数 | `code/q3.py:490` |
| 3 | ε3 约束用未加权 λ、指标用 $\\lambda w_j$，`e_f3` 与 `f3` 不相等，前沿不可复现 | `code/q3.py:383-387` |
| 4 | 默认目标含 f1+f3，与正文「三目标不可加权求和」矛盾 | `code/q3.py:392-397` |

---

## 环境与重跑

```bash
pip install numpy pandas scipy scikit-learn matplotlib networkx openpyxl seaborn
```

Gurobi 可选，`q3.py` 的 `have_gurobi()` 会回退到 `scipy.optimize.milp`。

依赖顺序（`附件/` 需自备，不入库）：

```bash
python code/q0_relations.py     # 数据体检
python code/q1.py               # ≈390 秒
python code/q1_grades.py        # 0-6 分级
python code/q1_diagnostics.py
python code/q2.py               # ≈360 秒
python code/q2_graph.py
python code/q3.py               # MILP，≈10 秒
python code/q3_transfer.py
python code/robustness_q3.py
python code/figures.py          # 重画 21 张图
```

审计与编译：

```bash
python code/tools/audit_paper.py    # 论文数字 vs results/，126 项
cd paper && xelatex -interaction=nonstopmode main.tex   # ×3
```

---

## 六条口径（改代码前必看）

1. **化学维数是 231**，不是 226。附件2 是 231×231 相关矩阵，含 5 个派生总量。226 只作消融对照。
2. **样本量是 250**。题面「226 种啤酒」是笔误。
3. **附件4 不是 0–6 整数**，是按品评员 z-score 后再平均的连续强度（原论文 Methods 原文）。
4. **缺失有两种**：`-1.817819` 是检出限地板值（保留），`NaN` 是真缺失（按列中位数填补）。
5. **Q3 的 PLS 训练集必须裁到 `[p1,p99]`**，否则线性浓度列独占协方差，成分数塌到 2。
6. **`code/_notitle.py` 不能删**，`figures.py` 靠它屏蔽图内总标题。

---

## 协作

分支 `feat/<名字>-<内容>`，提 PR 合回 `main`。提交信息写清改了什么，例如：

```
q1: 分级改为真值定切点，QWK 0.3400 -> 0.2978，>0.3 项 34 -> 25
q3: f3 公式改为 gamma*sum(z)+lambda*sum(w*|delta|)，重跑 300 网格
paper: 表 10 DMS 前 3 名项数 1 -> 4
```
'''
io.open(os.path.join(DEST, 'README.md'), 'w', encoding='utf-8',
        newline='').write(README)
print('✓ 比赛 README.md')

# ── 6. 提交
os.chdir(WORK)
subprocess.run(['git', 'config', 'user.name', 'LESIMP-star'], check=True)
subprocess.run(['git', 'config', 'user.email', '2220695796@qq.com'], check=True)

print('\n--- git status ---')
print(subprocess.run(['git', 'status', '--short'], capture_output=True,
                     text=True, encoding='utf-8').stdout[:3000])
