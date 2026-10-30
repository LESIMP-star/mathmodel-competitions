# -*- coding: utf-8 -*-
"""第二版：按最新的 q3_sensitivity.csv 换表 15 六行（锚点已改为当前实际内容）。"""
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
        rows.append(f'{NAME[p]} & {RANGE[p]} & ${base:.4f}$（恒定） & 0.0000 & '
                    f'{int(r["nmin"])} $\\to$ {int(r["nmax"])} \\\\')
    else:
        rows.append(f'{NAME[p]} & {RANGE[p]} & $[{r["lo"]:.3f},\\ {r["hi"]:.3f}]$ & '
                    f'{r["span"]:.4f} & {int(r["nmax"])} $\\to$ {int(r["nmin"])} \\\\')

s = io.open(P, encoding='utf-8', newline='').read()

# 用正则替换六行表格体
import re
pat = re.compile(
    r'改动列代价 \$\\gamma\$ & \[0\.5,\\ 4\.0\][^\n]*\n'
    r'代理成分数[^\n]*\n'
    r'工艺预算 \$\\varepsilon_3\$[^\n]*\n'
    r'改动量代价 \$\\lambda\$[^\n]*\n'
    r'缺陷容忍 \$\\varepsilon_2\$[^\n]*\n'
    r'干预预算 \$k_\{\\max\}\$[^\n]*\n')
m = pat.search(s)
if not m:
    print('✗ 表格体未匹配')
    sys.exit(1)
s = s[:m.start()] + '\n'.join(rows) + '\n' + s[m.end():]
print('✓ 表 15 六行已换新')

# 基准值
s = re.sub(r'基准设定 \$\\gamma=1\$、\$\\lambda=0\.1\$、\$k_\{\\max\}=25\$，此处 \$f_1=[\d.]+\$。',
           f'基准设定 $\\\\gamma=1$、$\\\\lambda=0.1$、$k_{{\\\\max}}=25$，此处 $f_1={base:.4f}$。', s)
s = re.sub(r'\\caption\{问题三灵敏度分析，基准 \$f_1=[\d.]+\$\}',
           f'\\\\caption{{问题三灵敏度分析，基准 $f_1={base:.4f}$}}', s)
print(f'✓ 基准 f1 = {base:.4f}')

io.open(P, 'w', encoding='utf-8', newline='').write(s)

# 打印供核对
print('\n新表：')
for r in rows:
    print('  ' + r)
