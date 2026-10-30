# -*- coding: utf-8 -*-
"""核 5.x 的两处数：地板值列数（34 vs 40）、log10 列数（182 vs 37）。"""
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

X = pd.read_csv('附件/1.csv').iloc[:, 3:]
LOD = -1.817819
n = len(X)

# ① 精确等于地板值的占比 ≥30%
exact = []
modeish = []
for c in X.columns:
    v = X[c].dropna()
    if len(v) == 0:
        continue
    share_min = float((np.isclose(v, v.min())).mean())
    top = v.value_counts(normalize=True)
    share_mode = float(top.iloc[0])
    if share_min >= 0.30:
        exact.append(c)
    if share_mode >= 0.30:
        modeish.append(c)

print(f'① 精确等于列最小值且占比≥30%：{len(exact)} 列')
print(f'   任意众数占比≥30%          ：{len(modeish)} 列')

# ② 只统计"最小值就是地板值"的那批
floor_min = [c for c in X.columns
             if len(X[c].dropna()) and np.isclose(X[c].min(), LOD)]
print(f'\n② 列最小值 == 地板值 {LOD} 的列：{len(floor_min)}')
ge30 = [c for c in floor_min
        if float(np.isclose(X[c].dropna(), LOD).mean()) >= 0.30]
print(f'   其中地板值占比≥30%       ：{len(ge30)}')

# ③ 负值列数（对数域下界证据）
neg = int((X.min() < 0).sum())
print(f'\n③ 含负值的列：{neg} / {X.shape[1]}')
