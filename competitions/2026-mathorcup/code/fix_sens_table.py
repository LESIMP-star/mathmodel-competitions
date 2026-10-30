# -*- coding: utf-8 -*-
"""按重跑后的灵敏度结果更新表 15 与三条结论。数据源 q3_sensitivity.csv。"""
import io
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

P = 'latex模板/sections/8_问题三.tex'
d = pd.read_csv('results/q3_sensitivity.csv')

# 每个参数的 f1 范围与摆幅
g = d.groupby('param').agg(lo=('f1', 'min'), hi=('f1', 'max'),
                           nmin=('n_changed', 'min'), nmax=('n_changed', 'max'),
                           span=('df1', 'max')).round(4)
print(g.to_string())
base = float(d[(d.param == 'gamma') & (d.value == 1.0)].f1.iloc[0])
print(f'\n基准 f1（gamma=1, lambda=0.1, kmax=25）= {base:.4f}')

ORDER = ['gamma', 'pls_k', 'eps3', 'lambda', 'eps2', 'k_max']
NAME = {'gamma': '改动列代价 $\\gamma$', 'pls_k': '代理成分数',
        'eps3': '工艺预算 $\\varepsilon_3$', 'lambda': '改动量代价 $\\lambda$',
        'eps2': '缺陷容忍 $\\varepsilon_2$', 'k_max': '干预预算 $k_{\\max}$'}
RANGE = {'gamma': '$[0.5,\\ 4.0]$', 'pls_k': '$[4,\\ 13]$',
         'eps3': '$[6.42,\\ 17.11]$', 'lambda': '$[0.05,\\ 0.40]$',
         'eps2': '$[0.0005,\\ 0.002]$', 'k_max': '$[15,\\ 35]$'}

rows = []
for p in ORDER:
    r = g.loc[p]
    if r['span'] < 1e-6:
        rows.append(f'{NAME[p]} & {RANGE[p]} & {base:.4f}（恒定） & 0.0000 & '
                    f'{int(r["nmin"])} $\\to$ {int(r["nmax"])} \\\\')
    else:
        rows.append(f'{NAME[p]} & {RANGE[p]} & $[{r["lo"]:.3f},\\ {r["hi"]:.3f}]$ & '
                    f'{r["span"]:.4f} & {int(r["nmax"])} $\\to$ {int(r["nmin"])} \\\\')
TAB = '\n'.join(rows)
print('\n新表格行：')
print(TAB)

s = io.open(P, encoding='utf-8', newline='').read()

# ── 1. 表 15 整块替换
OLD_TAB = r'''改动列代价 $\gamma$ & $[0.5,\ 4.0]$ & $[11.080,\ 24.424]$ & 13.3438 & 10 $\to$ 1 \\
代理成分数 & $[4,\ 13]$ & $[20.244,\ 29.475]$ & 9.2310 & 5 $\to$ 7 \\
工艺预算 $\varepsilon_3$ & $[4.47,\ 11.92]$ & $[11.156,\ 17.061]$ & 5.9057 & 3 $\to$ 9 \\
改动量代价 $\lambda$ & $[0.05,\ 0.40]$ & $[12.670,\ 17.217]$ & 4.5471 & 6 $\to$ 5 \\
缺陷容忍 $\varepsilon_2$ & $[0.0005,\ 0.002]$ & 13.785（恒定） & 0.0000 & 6 $\to$ 6 \\
干预预算 $k_{\max}$ & $[15,\ 35]$ & 13.785（恒定） & 0.0000 & 6 $\to$ 6 \\'''
assert s.count(OLD_TAB) == 1, f'表 15 锚点 {s.count(OLD_TAB)}'
s = s.replace(OLD_TAB, TAB)
print('  ✓ 表 15 六行已换新')

# ── 2. 基准值 13.7852 → 新基准
s = s.replace('基准设定 $\\gamma=1$、$\\lambda=0.1$、$k_{\\max}=25$，此处 $f_1=13.7852$。',
              f'基准设定 $\\gamma=1$、$\\lambda=0.1$、$k_{{\\max}}=25$，此处 $f_1={base:.4f}$。')
s = s.replace('\\caption{问题三灵敏度分析，基准 $f_1=13.7852$}',
              f'\\caption{{问题三灵敏度分析，基准 $f_1={base:.4f}$}}')
print(f'  ✓ 基准 f1 改为 {base:.4f}')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
