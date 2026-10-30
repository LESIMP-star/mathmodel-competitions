# -*- coding: utf-8 -*-
"""消融：把 5 个派生列加回特征集，看 226 vs 231 维差多少

Nature 原文用 p=231（含 caloric value、total acids、total ester、hop aroma、
sulfur 五个由多个实测值算出的量），其 Fig.4A 中 caloric value 排在 SHAP
第 6 位。本文用 226 维（剔除这 5 列）避免与母列强共线。本脚本量化这个取舍：
同一套嵌套 CV、同一随机种子，只换特征集。
"""
import os
import sys
import time

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import q1  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, '附件')
RES = os.path.join(ROOT, 'results')

c1 = pd.read_csv(os.path.join(DATA, '1.csv'))
c4 = pd.read_csv(os.path.join(DATA, '4.csv'))

feats231 = list(c1.columns[3:])
feats226 = [c for c in feats231 if c not in q1.DERIVED]
sens = list(c4.columns[3:])
print(f'231 维: {len(feats231)}   226 维: {len(feats226)}   靶: {len(sens)}')

X231 = c1.set_index('beer')[feats231].apply(pd.to_numeric, errors='coerce')
X226 = X231[feats226]
Y = c4.set_index('beer')[sens].apply(pd.to_numeric, errors='coerce')
idx = X226.index.intersection(Y.index)
X231, X226, Y = X231.loc[idx], X226.loc[idx], Y.loc[idx]
print('样本', len(idx))

fl = q1.floor_stats(Y)

rows = []
t0 = time.time()
for k, s in enumerate(sens, 1):
    y = Y[s].values.astype(float)
    hurdle = bool(fl[s] > q1.HURDLE_THR)
    oof226, ch226 = q1.nested_cv_one(y, X226.values, hurdle)
    oof231, ch231 = q1.nested_cv_one(y, X231.values, hurdle)
    s226 = q1._score(y, oof226)
    s231 = q1._score(y, oof231)
    rows.append(dict(sens=s, hurdle=hurdle,
                     R2_226=round(s226[0], 4), R2_231=round(s231[0], 4),
                     d=round(s231[0] - s226[0], 4),
                     m226='/'.join(sorted(set(ch226))),
                     m231='/'.join(sorted(set(ch231)))))
    print(f'[{k:2d}/{len(sens)}] {s:18s} 226 {s226[0]:+.4f}  231 {s231[0]:+.4f}  '
          f'Δ {s231[0] - s226[0]:+.4f}   ({time.time() - t0:.0f}s)')

df = pd.DataFrame(rows)
df.to_csv(os.path.join(RES, 'q1_ablation_231.csv'), index=False, encoding='utf-8-sig')
print('\n' + '=' * 60)
print(f'226 维  R2 中位 {df.R2_226.median():.4f}  均值 {df.R2_226.mean():.4f}')
print(f'231 维  R2 中位 {df.R2_231.median():.4f}  均值 {df.R2_231.mean():.4f}')
print(f'平均差 {df.d.mean():+.4f}，中位差 {df.d.median():+.4f}')
print(f'231 更好的维度 {int((df.d > 0).sum())}/{len(df)}  '
      f'(|Δ|>0.02 的有 {int((df.d.abs() > 0.02).sum())} 个)')
print(f'耗时 {time.time() - t0:.0f}s')
