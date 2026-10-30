# -*- coding: utf-8 -*-
"""算 Q2 的高置信子集：按 200 次自助的平均排名（consrank）筛稳定靠前的香气化合物"""
import json
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

cr = pd.read_csv('results/q2_feature_consrank.csv', index_col=0)
pi = pd.read_csv('results/q2_feature_pi.csv', index_col=0)
t3 = pd.read_csv('results/q2_top3.csv')
print('consrank 形状', cr.shape, '  pi 形状', pi.shape)

# 香气候选池 = top3 里出现过的 feat（已排除理化/派生/内标）
AROMA = set(t3.feat.astype(str))
print('香气候选池', len(AROMA))

rows = []
for sens in cr.index:
    r = cr.loc[sens]
    cand = [(f, float(v)) for f, v in r.items() if f in AROMA and np.isfinite(v)]
    cand.sort(key=lambda x: x[1])
    top = cand[:3]
    # 高置信：平均排名 <= 5
    conf = [(f, v) for f, v in cand if v <= 5.0]
    rows.append(dict(sens=sens, **{f'top{i+1}': top[i][0] for i in range(3)},
                     **{f'cr{i+1}': round(top[i][1], 1) for i in range(3)},
                     n_conf=len(conf),
                     conf=';'.join(f'{f}({v:.1f})' for f, v in conf)))

df = pd.DataFrame(rows)
print('\n每项 consrank<=5 的化合物个数分布：')
print(df.n_conf.value_counts().sort_index().to_string())
print(f'\n合计高置信记录 {int(df.n_conf.sum())} 条（对比 Top-3 的 150 条）')
print(f'至少 1 条高置信的感官项 {int((df.n_conf > 0).sum())}/50')
print(f'至少 3 条高置信的感官项 {int((df.n_conf >= 3).sum())}/50')
print(f'consrank 中位（Top-1）{df.cr1.median():.1f}')

print('\n=== 前 12 个感官项的高置信子集 ===')
print(df.head(12)[['sens', 'top1', 'cr1', 'cr2', 'cr3', 'conf']].to_string(index=False))

df.to_csv('results/q2_confident.csv', index=False, encoding='utf-8-sig')
print('\n写出 results/q2_confident.csv')
