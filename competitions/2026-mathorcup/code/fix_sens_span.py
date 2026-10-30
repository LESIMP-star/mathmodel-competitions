# -*- coding: utf-8 -*-
"""表 15 与三条结论统一改用 q3_sensitivity_span.csv 的 span 口径（f1 极差）。"""
import io
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

P = 'latex模板/sections/8_问题三.tex'
sp = pd.read_csv('results/q3_sensitivity_span.csv').set_index('param')
d = pd.read_csv('results/q3_sensitivity.csv')
base = float(sp.loc['gamma', 'f1_lo']) if False else 20.206269

NAME = {'gamma': r'改动列代价 $\gamma$', 'pls_k': '代理成分数',
        'eps3': r'工艺预算 $\varepsilon_3$', 'lambda': r'改动量代价 $\lambda$',
        'eps2': r'缺陷容忍 $\varepsilon_2$', 'k_max': r'干预预算 $k_{\max}$'}
RANGE = {'gamma': r'$[0.5,\ 4.0]$', 'pls_k': r'$[4,\ 13]$',
         'eps3': r'$[6.42,\ 17.11]$', 'lambda': r'$[0.05,\ 0.40]$',
         'eps2': r'$[0.0005,\ 0.002]$', 'k_max': r'$[15,\ 35]$'}
ORDER = ['gamma', 'pls_k', 'eps3', 'lambda', 'eps2', 'k_max']

rows = {}
for p in ORDER:
    r = sp.loc[p]
    lo, hi, span = float(r.f1_min), float(r.f1_max), float(r.span)
    nc_lo = int(d[d.param == p].sort_values('value').n_changed.iloc[-1])
    nc_hi = int(d[d.param == p].sort_values('value').n_changed.iloc[0])
    if span < 1e-6:
        rows[p] = (f'{NAME[p]} & {RANGE[p]} & ${lo:.4f}$（恒定） & 0.0000 & '
                   f'{nc_hi} $\\to$ {nc_hi} \\\\')
    else:
        rows[p] = (f'{NAME[p]} & {RANGE[p]} & $[{lo:.3f},\\ {hi:.3f}]$ & '
                   f'{span:.4f} & {nc_hi} $\\to$ {nc_lo} \\\\')

s = io.open(P, encoding='utf-8', newline='').read()

# ---- 换六行 ----
lines = s.split('\n')
KEY = {'gamma': '改动列代价', 'pls_k': '代理成分数', 'eps3': '工艺预算',
       'lambda': '改动量代价', 'eps2': '缺陷容忍', 'k_max': '干预预算'}
n = 0
for i, ln in enumerate(lines):
    for p in ORDER:
        if ln.startswith(KEY[p]) and '&' in ln and ('$[' in ln and '\\\\' in ln):
            lines[i] = rows[p]
            n += 1
            break
print(f'表 15 替换 {n}/6 行')
s = '\n'.join(lines)

# ---- 三条结论 ----
OLD1 = s[s.find('三条结论。第一'):s.find('第二，代理成分数')]
NEW1 = (r'三条结论。第一，改动列代价 $\gamma$ 是主导项，极差 21.5730，约是第二项的 2.4 倍。'
        r'$\gamma$ 从 0.5 增到 4.0 时，可改的列数从 19 压到 2，$f_1$ 从 15.436 升到 37.009。'
        r'这说明“愿意改几个化合物”对结果的影响大于任何数值细节，本文因此把改动数作为显式约束，'
        r'并把 $\gamma$ 作为报告权衡曲线的主轴。' + '\n\n')
s = s.replace(OLD1, NEW1)

OLD2 = s[s.find('第二，代理成分数'):s.find('第三，工艺预算')]
NEW2 = (r'第二，工艺预算 $\varepsilon_3$ 与代理成分数稍次之，极差分别为 8.8648 与 5.0949。'
        r'$\varepsilon_3$ 从 6.42 放宽到 17.11 时，$f_1$ 从 25.287 降到 16.422、可改列数从 6 增到 16，'
        r'这正是“多改换低偏差”的权衡本身。代理成分数则不单调：4 个成分时 $f_1=24.891$（拟合不足），'
        r'6 个降到 20.268，8 个（本文取值）为 20.206，13 个反而回升到 21.856。' + '\n\n')
s = s.replace(OLD2, NEW2)

OLD3 = s[s.find('第三，工艺预算'):]
OLD3 = OLD3[:OLD3.find('\n')] if '\n' in OLD3 else OLD3
# 上一版把「第三，工艺预算」整段写成了含第四的内容，这里一并重写
i0 = s.find('第三，工艺预算')
if i0 >= 0:
    i1 = s.find('\n', i0)
    while i1 != -1 and s[i1:i1 + 1] == '\n' and s[i1 + 1:i1 + 2] == '\n':
        break
    # 取到下一个空行前的整段
    end = s.find('\n\n', i0)
    if end == -1:
        end = len(s)
    NEW3 = (r'第三，改动量代价 $\lambda$ 的影响最小但非零，极差 2.3745：$\lambda$ 从 0.05 到 0.40 时'
            r'$f_1$ 仅从 20.206 升到 22.581，说明 $f_3$ 的权重只需保证“改动要有代价”，'
            r'具体数值不敏感。第四，缺陷容忍 $\varepsilon_2$ 与干预预算 $k_{\max}$ 的极差均为 0，'
            r'都是不活跃约束。$\varepsilon_2$ 不活跃是因为双乙酰已被硬约束压到阈值以下，此时 $f_2=0$，'
            r'放宽上限自然无影响——这也是单位修正后的结果，修正前 $f_2$ 被伪约束固定，'
            r'扰动 $\varepsilon_2$ 会看似敏感。$k_{\max}$ 不活跃是因为基准解只需改 10 个化合物，'
            r'上限从 15 放宽到 35 都不变。两点都须写明，否则容易把 $k_{\max}=25$ 误当作结论的驱动因素。')
    s = s[:i0] + NEW3 + s[end:]

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n新表：')
for p in ORDER:
    print('  ' + rows[p])
