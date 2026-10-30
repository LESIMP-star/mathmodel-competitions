# -*- coding: utf-8 -*-
"""推送到 mathmodel-competitions 仓库（走 ghproxy，直连不通）。

只放代码 / 结果 / 论文源 / 图 / 文档；不放附件与 dist/。
"""
import io
import os
import shutil
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.getcwd()
WORK = r'E:\hermes\.hermes\cache\scratch\repo_push'
DEST = os.path.join(WORK, 'competitions', '2026-mathorcup')

# github.com 直连被加速器自签证书拦掉（schannel handshake 失败），
# 但加 http.sslVerify=false 后直连可通；ghproxy 那条会弹凭据管理器窗口，
# 在无终端的后台进程里必然失败（could not read Username），故不再用。
PUSH_URL = 'https://github.com/LESIMP-star/mathmodel-competitions.git'
REPOS = [PUSH_URL]


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', **kw)
    return r


def clone():
    if os.path.isdir(WORK):
        def _f(func, path, exc):
            os.chmod(path, 0o666)
            func(path)
        shutil.rmtree(WORK, onexc=_f)
    for url in REPOS:
        r = run(['git', '-c', 'http.sslVerify=false', 'clone',
                 '--depth', '1', url, WORK])
        if r.returncode == 0:
            print(f'✓ clone  {url.split("//")[1][:46]}')
            return url
        print(f'  × clone 失败: '
              f'{(r.stderr or "").strip().splitlines()[-1][:90] if r.stderr else ""}')
    raise SystemExit('clone 失败')


USED = clone()


def cp_tree(src, dst, skip=(), drop=()):
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in os.listdir(src):
        if f in skip or any(f.startswith(p) or f.endswith(p) for p in drop):
            continue
        s, d = os.path.join(src, f), os.path.join(dst, f)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(s, d)
        n += 1
    return n


if os.path.isdir(DEST):
    shutil.rmtree(DEST)
os.makedirs(DEST)

# ① code/（跳过运行日志与缓存）
print(f'✓ code/  {cp_tree(os.path.join(ROOT, "code"), os.path.join(DEST, "code"), skip=("__pycache__",), drop=("log_", ".log", ".pyc"))} 项')

# ② results/
RES = os.path.join(DEST, 'results')
os.makedirs(RES, exist_ok=True)
n = 0
for f in os.listdir(os.path.join(ROOT, 'results')):
    p = os.path.join(ROOT, 'results', f)
    if not os.path.isfile(p) or f.endswith('.log'):
        continue
    shutil.copy2(p, os.path.join(RES, f))
    n += 1
print(f'✓ results/  {n} 个文件')

# ③ paper/
PAPER = os.path.join(DEST, 'paper')
os.makedirs(PAPER, exist_ok=True)
for f in ('main.tex', 'references.tex', 'README.md', 'build_paper.bat'):
    s = os.path.join(ROOT, 'latex模板', f)
    if os.path.exists(s):
        shutil.copy2(s, os.path.join(PAPER, f))
for d in ('sections', 'figures'):
    shutil.copytree(os.path.join(ROOT, 'latex模板', d),
                    os.path.join(PAPER, d), dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '_bak*', '_archive'))
shutil.copy2(os.path.join(ROOT, 'latex模板', 'main.pdf'),
             os.path.join(PAPER, 'main.pdf'))
print(f'✓ paper/  sections {len(os.listdir(os.path.join(PAPER, "sections")))} 个 + '
      f'figures {len(os.listdir(os.path.join(PAPER, "figures")))} 个 + main.pdf')

# ④ docs/
DOCS = os.path.join(DEST, 'docs')
os.makedirs(DOCS, exist_ok=True)
n = 0
for f in ('六条意见判定.md', '修复说明_问题三目标口径.md',
          '修复说明_问题一预处理.md', '修订计划_第三轮.md',
          '队友任务_改画图逻辑.md', '赛题要求核对表.md',
          '问题核对_35条.md', '整理说明.md', '2026A题坑点汇总.md',
          '论文核对清单_审计19项.csv', '论文核对清单_逐维R2.csv'):
    for base in ('docs', ''):
        p = os.path.join(ROOT, base, f)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(DOCS, f))
            n += 1
            break
    else:
        print(f'  ! 缺 {f}')
print(f'✓ docs/  {n} 个文件')

# ⑤ README
readme = '''# 2026 MathorCup 大数据竞赛 · 赛道 A

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
| 4 | **A1 附录的分级大表是 25 列 × 2 张** | 试过合成一张 50 列，`\tiny` + `\tabcolsep 0.8pt` 仍超宽 325pt |

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
'''
io.open(os.path.join(DEST, 'README.md'), 'w', encoding='utf-8',
        newline='').write(readme)
print('✓ README.md')

# ⑥ 提交并推送
os.chdir(WORK)
run(['git', 'config', 'user.name', 'LESIMP-star'])
run(['git', 'config', 'user.email', '2220695796@qq.com'])
st = run(['git', 'reset'])
run(['git', 'add', '-A'])
st = run(['git', 'status', '--short'])
lines = [l for l in (st.stdout or '').splitlines() if l.strip()]
nadd = len(lines)
print(f'\n待提交 {nadd} 项')
for l in lines[:12]:
    print(f'  {l}')
if nadd > 12:
    print(f'  … 另有 {nadd - 12} 项')

if nadd == 0:
    print('无改动，直接检查推送状态')
else:
    msg = ('mathorcup: 同步 Q3 目标口径修复与全链路数字\n\n'
           '- q3.py: f3 的线性目标补 wj 归一（与 ε3 约束、metrics_of 同口径）\n'
           '- q3.py: 增广项 c_aug 同步乘 wj\n'
           '- robustness_q3.py: PLS 训练集裁剪到 [p1,p99]，与主流程一致\n'
           '- 结果：Pareto 5→7 点，最优 f1 23.8519→20.2063，降幅 51.3%→58.7%\n'
           '- 图：21 张全部按新结果重绘\n'
           '- 文档：修复说明（问题一/问题三）、六条意见判定、队友画图任务、'
           '赛题要求核对表')
    r = run(['git', 'commit', '-m', msg])
    print((r.stdout or '').strip()[:500] or (r.stderr or '')[:500])

pushed = False
for attempt in range(1, 4):
    r = run(['git', '-c', 'http.sslVerify=false', 'push',
             PUSH_URL, 'HEAD:main'])
    if r.returncode == 0:
        print(f'✓ push 成功（第 {attempt} 次尝试）')
        print((r.stderr or '').strip()[-300:])
        pushed = True
        break
    print(f'  × 第 {attempt} 次失败: {(r.stderr or "").strip()[-160:]}')
    time.sleep(3)

if not pushed:
    print('!! push 全部失败')

os.chdir(ROOT)
sys.exit(0 if pushed else 1)
