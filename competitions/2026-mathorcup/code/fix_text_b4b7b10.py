# -*- coding: utf-8 -*-
"""B4 标签口径改为品评员 z-score；B7 OAV 改浓度/阈值比；B9 表14 加是否超阈值；B10 主方案理由。"""
import io
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

C5 = 'latex模板/sections/5_数据预处理.tex'
C6 = 'latex模板/sections/6_问题一.tex'
C7 = 'latex模板/sections/7_问题二.tex'
C8 = 'latex模板/sections/8_问题三.tex'
C3 = 'latex模板/sections/3_模型假设.tex'
C4 = 'latex模板/sections/4_符号说明.tex'
MAIN = 'latex模板/main.tex'
OK, FAIL = [], []


def rep(path, old, new, tag, count=1):
    s = io.open(path, encoding='utf-8', newline='').read()
    n = s.count(old)
    if n != count:
        FAIL.append((tag, n, count))
        print(f'  ✗ {tag}（{n}/{count}）')
        return
    io.open(path, 'w', encoding='utf-8', newline='').write(s.replace(old, new))
    OK.append(tag)
    print(f'  ✓ {tag}')


# ══════════════════ B4-1　5.x 的标签定义改为 z-score 口径
rep(C5,
    '第三类是感官侧的未感知下限。50 个感官项全部存在负值，范围在 $-2.151$ 至 $-0.239$ 之间，'
    '且各列最小值互不相同。本文定义地板质量为与该列最小值相距不超过 0.15 的样本占比',
    r'''第三类是感官侧的列内左尾。附件4 的标签不是原始 0--6 分值：文献\cite{schreurs2024}的方法写明，16 位品评员先按 7 点量表打分，再\textbf{按品评员做 z-score}（减均值、除标准差），最后按啤酒求平均；原文对此的表述是"Scores were scaled by standard deviation and mean-centered per taster. Values are represented as z-scores"。因此负值表示"低于该品评员的平均"，不是"没有尝到"；列最小值是 z 空间里的左尾，不是感官 0 分。

据此，本文把 $\phi_s$ 定义为\emph{左尾占比}，即与该列最小值相距不超过 0.15 的样本占比''',
    'B4-1 标签 z-score 口径')

rep(C5, '作为“未感知比例”的度量，供问题一判断是否需要两段式模型。',
    '作为各列分布左尾厚度的度量，供问题一判断是否需要单独处理高左尾项。',
    'B4-2 左尾占比用途')

# ══════════════════ B4-3 符号表
rep(C4, '地板效应占比，即未感知样本占比', '左尾占比，即与该列最小值相距 ≤0.15 的样本占比',
    'B4-3 符号表 φ_s')

# ══════════════════ B4-4 假设 2
rep(C3, '附件4 的 50 个感官项是同一 0--6 评分制经中心化与尺度变换后的连续强度，项间差异不含量纲差异。',
    '附件4 的 50 个感官项是 7 点量表按品评员 z-score 后再按啤酒平均的连续强度，项间差异不含量纲差异。',
    'B4-4 假设2')

# ══════════════════ B7　OAV → 浓度/阈值比，分香气/味觉
rep(C7,
    '化学合理性用\\emph{气味活性值}判断。对化合物 $j$ 与感官项 $i$，定义',
    r'''化学合理性用\emph{浓度/阈值比}判断。这里要区分两类感官项：嗅觉项比的是\textbf{香气阈值}（即严格意义的气味活性值 OAV），味觉与口感项比的是\textbf{味觉或物理阈值}（乳酸 416.7\,mg/L 为酸感阈值、乙酸 0.14\,g/L 为酸感阈值、苦度 5\,IBU 为苦味阈值），二者不可混称。对化合物 $j$ 与感官项 $i$，统一定义''',
    'B7-1 OAV 改名')

# ══════════════════ B10　主方案 kappa 最低的理由
rep(C6,
    '因此 $p$ 取自感官评价文献的经验分布，并用敏感性分析代替主观设定。',
    r'''因此 $p$ 取自感官评价文献的经验分布，并用敏感性分析代替主观设定。需要说明一处：表~\ref{tab:q1grade} 里零膨胀先验的 kappa（0.3400）并非四组中最高（均匀先验 0.3812、等频映射 0.3770、轻度零膨胀 0.3599）。本文仍以零膨胀为主方案，理由不是 kappa 最高，而是 7 点感官量表在实测中的边际分布本身就是厚零的——大量样品在多数维度上被评为最低档，零膨胀先验的形状与这一先验知识一致；其余三组作为敏感性对照，用于界定"换先验会改变多少"。换言之，主方案按\emph{先验合理性}选定，kappa 的四组差异（极差 0.041）用于说明该选择对结论的影响幅度，而不是用于反向挑选最高分。''',
    'B10 主方案理由')

print(f'\n成功 {len(OK)}，失败 {len(FAIL)}')
for t, n, c in FAIL:
    print(f'  {t}（{n}/{c}）')
