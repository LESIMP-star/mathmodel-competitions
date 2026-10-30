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


def cp_tree(src, dst, skip=()):
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in os.listdir(src):
        if f in skip:
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

# ① code/
print(f'✓ code/  {cp_tree(os.path.join(ROOT, "code"), os.path.join(DEST, "code"), skip=("__pycache__",))} 项')

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
**状态**：53 页 / 正文 30 页（上限 30）/ 0 error 0 overfull / `audit_paper.py` 126-126
**队号**：待填（`paper/main.tex` 与 AI 声明里的 `MCB260XXXX`）

---

## 目录

```
competitions/2026-mathorcup/
├── code/        16 个求解脚本（q0 → q1 → q2 → q3）+ 10 个审计/构建工具
├── paper/       LaTeX 源 + 编译好的 main.pdf
│   ├── sections/  16 个章节 tex
│   └── figures/   42 个图文件（21 张 × PNG + SVG）
├── results/     80 个结果文件，论文每个数字的源头
└── docs/        修复说明、核对清单、队友任务、赛题要求核对表
```

---

## 六条数据口径（改代码 / 改论文前必看）

1. **化学维数是 231**，不是 226。附件2 是 231×231 相关矩阵，含 5 个派生总量。226 只作消融对照。
2. **样本量是 250**。题面「226 种啤酒」是笔误。
3. **附件4 不是 0–6 整数**，是按品评员 z-score 后再按啤酒平均的连续强度。
   所以负值 = 低于该品评员的平均，**不是"没有尝到"**；全文用"左尾"不用"未感知"。
4. **缺失有两种**：`-1.817819` 是检出限地板值（保留），`NaN` 是真缺失（按列中位数填补）。
5. **Q3 的 PLS 训练集必须裁到 `[p1,p99]`**，否则线性浓度列独占协方差，成分数塌到 2。
6. **Q3 的 `f3` 三处必须同用 `lam * wj`**：目标向量 `c`、`ε3` 约束、`metrics_of`。
   任一处漏 `wj` 就会让"求解的目标"≠"报告的 f3"。

---

## 当前数字（四个问题）

| 项 | 值 |
|---|---|
| Q1 嵌套 CV R² | 中位 0.1469，均值 0.2223 |
| Q1 分级 QWK | 0.3400（精确同档 0.3812） |
| Q2 Top-3 归因 | 150 项，非香气混入 0 |
| Q2 阈值入选 | π ≥ 0.5022 共 10 条 |
| Q3 Pareto 点 | 7 个（f1 20.2063 – 47.2083） |
| Q3 最优 f1 | 20.2063（基线 48.9620，降 58.7%） |
| Q3 支配 NSGA-II | 92.17%（106/115） |
| Q3 超体积 | 757.78 对 299.12 |
| Q3 跨风格迁移 | 47.1450 → 13.1366，降 72.14% |

---

## 协作

分支 `feat/<名字>-<内容>`，提 PR 合回 `main`。

**画图由队友负责**：改 `code/figures.py`，改完跑

```bash
python code/figures.py      # 21 图 / 42 文件 → paper/figures/
```

再看 `docs/队友任务_改画图逻辑.md`。

核数：

```bash
python code/tools/audit_paper.py        # 论文数字 vs results/，126 项
python code/audit_consistency.py        # 全链路口径一致性
cd paper && xelatex -interaction=nonstopmode main.tex   # ×3
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
