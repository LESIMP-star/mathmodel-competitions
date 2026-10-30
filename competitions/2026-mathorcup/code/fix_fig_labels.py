# -*- coding: utf-8 -*-
"""修 figures.py 里残留的旧口径：226→231、0.1471→0.1469、分组置换→逐列置换、
5 点 Pareto→7 点、91.30%→92.17%，删掉「+ FDR」。"""
import io
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

P = 'code/figures.py'
s = io.open(P, encoding='utf-8', newline='').read()
OK, FAIL = [], []


def rep(old, new, tag):
    global s
    n = s.count(old)
    if n != 1:
        FAIL.append((tag, n))
        print(f'  ✗ {tag}（{n}）')
        return
    s = s.replace(old, new)
    OK.append(tag)
    print(f'  ✓ {tag}')


rep('  Q2  fig_q2_pi_heatmap       化合物 × 感官的分组置换重要性 —— 主证据',
    '  Q2  fig_q2_pi_heatmap       化合物 × 感官的逐列置换重要性 —— 主证据',
    '文件头注释')

rep('    """化合物 × 感官的分组置换重要性（主证据）。',
    '    """化合物 × 感官的逐列置换重要性（主证据）。',
    '函数 docstring')

rep('    V = pi[feats].to_numpy(dtype=float)                 # (50 感官, 226 化合物)',
    '    V = pi[feats].to_numpy(dtype=float)                 # (50 感官, 231 化合物)',
    '注释 226→231')

rep("                       cbar_label='分组置换重要性 $\\\\pi$', vmin=0.0,",
    "                       cbar_label='逐列置换重要性 $\\\\pi$', vmin=0.0,",
    'colorbar 标签')

rep("    box(XC[2], YR[0], '统一数据底座 D0\\\\n250×226 / 250×50', C_PALE, C_BLUE2)",
    "    box(XC[2], YR[0], '统一数据底座 D0\\\\n250×231 / 250×50', C_PALE, C_BLUE2)",
    '流程图 226→231')

rep("    box(XC[2], YR[1], '$R^2$ 中位 0.1471\\\\nhurdle 9 维 · 自助区间', '#DDEFF2', C_TEAL)",
    "    box(XC[2], YR[1], '$R^2$ 中位 0.1469\\\\nhurdle 9 维 · 自助区间', '#DDEFF2', C_TEAL)",
    '流程图 R²')

rep("    box(XC[1], YR[2], '分组置换 $\\\\\\\\pi$ + FDR\\\\n阈值 0.5022', '#E4E8F5', C_PURPLE)",
    "    box(XC[1], YR[2], '逐列置换 $\\\\\\\\pi$\\\\n阈值 0.5022 · 10 条入选', '#E4E8F5', C_PURPLE)",
    '流程图 分组置换+FDR')

rep("    box(XC[2], YR[3], '5 点 Pareto\\\\n支配 NSGA-II 91.30%', '#E3F0EC', C_TEAL)",
    "    box(XC[2], YR[3], '7 点 Pareto\\\\n支配 NSGA-II 92.17%', '#E3F0EC', C_TEAL)",
    '流程图 Pareto')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print(f'\n成功 {len(OK)}，失败 {len(FAIL)}')
for t, n in FAIL:
    print(f'  {t}（{n}）')
