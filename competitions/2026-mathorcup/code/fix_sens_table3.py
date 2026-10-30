# -*- coding: utf-8 -*-
"""按行替换表 15 六行（避免正则转义问题）。"""
import io
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

P = 'latex模板/sections/8_问题三.tex'
d = pd.read_csv('results/q3_sensitivity.csv')
g = d.groupby('param').agg(lo=('f1', 'min'), hi=('f1', 'max'),
                           nmin=('n_changed', 'min'), nmax=('n_changed', 'max'),
                           span=('df1', 'max')).round(4)
base = float(d[(d.param == 'gamma') & (d.value == 1.0)].f1.iloc[0])

ORDER = ['gamma', 'pls_k', 'eps3', 'lambda', 'eps2', 'k_max']
KEY = {'gamma': '改动列代价', 'pls_k': '代理成分数', 'eps3': '工艺预算',
       'lambda': '改动量代价', 'eps2': '缺陷容忍', 'k_max': '干预预算'}
NAME = {'gamma': r'改动列代价 $\gamma$', 'pls_k': '代理成分数',
        'eps3': r'工艺预算 $\varepsilon_3$', 'lambda': r'改动量代价 $\lambda$',
        'eps2': r'缺陷容忍 $\varepsilon_2$', 'k_max': r'干预预算 $k_{\max}$'}
RANGE = {'gamma': r'$[0.5,\ 4.0]$', 'pls_k': r'$[4,\ 13]$',
         'eps3': r'$[6.42,\ 17.11]$', 'lambda': r'$[0.05,\ 0.40]$',
         'eps2': r'$[0.0005,\ 0.002]$', 'k_max': r'$[15,\ 35]$'}

new = {}
for p in ORDER:
    r = g.loc[p]
    if r['span'] < 1e-6:
        body = (f'{NAME[p]} & {RANGE[p]} & ${base:.4f}$（恒定） & 0.0000 & '
                f'{int(r["nmin"])} $\\to$ {int(r["nmax"])} \\\\')
    else:
        body = (f'{NAME[p]} & {RANGE[p]} & $[{r["lo"]:.3f},\\ {r["hi"]:.3f}]$ & '
                f'{r["span"]:.4f} & {int(r["nmax"])} $\\to$ {int(r["nmin"])} \\\\')
    new[p] = body

lines = io.open(P, encoding='utf-8', newline='').read().split('\n')
n_ok = 0
for i, ln in enumerate(lines):
    for p in ORDER:
        if ln.startswith(KEY[p]) and '&' in ln and ('$[0' in ln or '恒定' in ln):
            lines[i] = new[p]
            n_ok += 1
            break
print(f'✓ 替换 {n_ok}/6 行')

s = '\n'.join(lines)

# 基准值：按行找
for i, ln in enumerate(lines):
    if '基准设定' in ln and 'f_1=' in ln:
        lines[i] = (r'前沿位置依赖六个设定：干预预算 $k_{\max}$、改动列代价 $\gamma$、'
                    r'改动量代价 $\lambda$、缺陷容忍 $\varepsilon_2$、工艺预算 '
                    r'$\varepsilon_3$ 与代理成分数。本文对每个参数做单因素扰动，每次扰动都'
                    r'重新求解一次混合整数规划，共 27 次重解，以最优 $f_1$ 的变化为响应。'
                    rf'基准设定 $\gamma=1$、$\lambda=0.1$、$k_{{\max}}=25$，此处 $f_1={base:.4f}$。'
                    r'结果见表~\ref{tab:q3sens} 与图~\ref{fig:q3tornado}。')
        print('✓ 基准段已换')
    if ln.startswith(r'\caption{问题三灵敏度分析'):
        lines[i] = rf'\caption{{问题三灵敏度分析，基准 $f_1={base:.4f}$}}'
        print('✓ 表注已换')

io.open(P, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
print(f'\n基准 f1 = {base:.4f}')
for p in ORDER:
    print('  ' + new[p])
