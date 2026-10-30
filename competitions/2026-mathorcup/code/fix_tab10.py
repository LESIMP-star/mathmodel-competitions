# -*- coding: utf-8 -*-
"""表 10 数字修正 + 辛酸乙酯/β-水芹烯 + consrank 表述。"""
import io
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

C7 = 'latex模板/sections/7_问题二.tex'
OK, FAIL = [], []


def rep(old, new, tag, count=1):
    s = io.open(C7, encoding='utf-8', newline='').read()
    n = s.count(old)
    if n != count:
        FAIL.append((tag, n, count))
        print(f'  ✗ {tag}（{n}/{count}）')
        return
    io.open(C7, 'w', encoding='utf-8', newline='').write(s.replace(old, new))
    OK.append(tag)
    print(f'  ✓ {tag}')


# ══════ 表 10 两行数字（以 q2_consensus.csv 为准：DMS 9/4、prenyl 7/4）
rep('\\texttt{DMS}（熟蔬菜） & 9 & 1 \\\\',
    '\\texttt{DMS}（熟蔬菜） & 9 & 4 \\\\', '表10 DMS 前3名 1→4')
rep('\\texttt{prenyl.isobutyrate}（麦芽香） & 7 & 2 \\\\',
    '\\texttt{prenyl.isobutyrate}（麦芽香） & 7 & 4 \\\\',
    '表10 prenyl 前3名 2→4')

# ══════ 正文：DMS 的论证 + 辛酸乙酯 → β-水芹烯
rep('DMS 是熟蔬菜味的缺陷物，但同时会干扰酒花香的判断，因此在前 5 名频繁出现而在前 3 名罕见——这一差异本身就说明它的作用是被“减去”而非“加上”；苯乙醇与辛酸乙酯分别是玫瑰花香与果香的主体，与酿造学一致。',
    'DMS 是熟蔬菜味的缺陷物，在前 5 名出现 9 次、前 3 名 4 次，说明它虽常被模型挑中，却较少进入最前列；异丁酸异戊酯每列最高频取值（$\\pi=1.000$，即 200 次重采样全部进入前 10）与苯乙醇分别对应麦芽香与玫瑰花香，$\\beta$-水芹烯带果香与胡椒气息，三者与酿造学一致。',
    '表10 正文论证')

# ══════ consrank：200 次重采样 → 三个模型族的平均排名
rep('逐项不稳定可以用比 Jaccard 更直接的方式量化。200 次重采样给出每个化合物在每个感官项上的平均排名 consrank，1 为最靠前，据此定义“稳定进前 $k$”的子集：',
    '逐项不稳定可以用比 Jaccard 更直接的方式量化。对每个感官项，把 LightGBM、ExtraTrees、岭回归三个模型族的置换重要性排名取平均，得到每个化合物的跨模型平均排名 consrank，1 为最靠前；据此定义“稳定进前 $k$”的子集：',
    'consrank 口径')

print(f'\n成功 {len(OK)}，失败 {len(FAIL)}')
for t, n, c in FAIL:
    print(f'  {t}（{n}/{c}）')
