# -*- coding: utf-8 -*-
"""按「对数域 / 线性域」的判定规则直接从 8.xlsx Calibrated 表复算，解决 33 vs 34 之争。

规则（与 5.x 节一致）：对每个化学列，
  · 若 |10^x − b| / |b| 的中位数 < 1e-3  → 判为 log10 域
  · 若 |x − b| / |b| 的中位数 < 1e-3    → 判为原始线性域
  · 两者都不满足 / 表中无该列            → 无对照
"""
import glob
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

c1 = pd.read_csv(glob.glob('附件*/**/1.csv', recursive=True)[0])
feats = list(c1.columns[3:])

cal = pd.read_excel(glob.glob('附件*/**/8.xlsx', recursive=True)[0],
                    sheet_name='Calibrated chemical dataset')
print(f'Calibrated 表 {cal.shape}')
print('前 5 列:', list(cal.columns[:5]))


def norm(s):
    return str(s).lower().replace(' ', '').replace('.', '').replace('_', '').replace('-', '')


# 找 beer 列
key = cal.columns[0]
print('首列名:', key)

n_log = n_lin = n_none = 0
detail = []
for f in feats:
    if f not in cal.columns:
        n_none += 1
        continue
    x = pd.to_numeric(c1[f], errors='coerce').to_numpy(float)
    b = pd.to_numeric(cal[f], errors='coerce').to_numpy(float)
    ok = np.isfinite(x) & np.isfinite(b) & (np.abs(b) > 0)
    if ok.sum() < 30:
        n_none += 1
        continue
    x, b = x[ok], b[ok]
    e_log = np.median(np.abs(np.power(10.0, x) - b) / np.abs(b))
    e_lin = np.median(np.abs(x - b) / np.abs(b))
    if e_log < 1e-3 and e_log < e_lin:
        n_log += 1
        detail.append((f, 'log10', e_log, e_lin))
    elif e_lin < 1e-3:
        n_lin += 1
        detail.append((f, 'linear', e_log, e_lin))
    else:
        n_none += 1
        detail.append((f, 'none', e_log, e_lin))

print(f'\n对数域 {n_log} | 线性域 {n_lin} | 无对照 {n_none} | 合计 {n_log + n_lin + n_none}')
print('（论文两版分别写 37/33 与 37/34；q0_summary 记录 n_log10_cols=37）')
df = pd.DataFrame(detail, columns=['feat', 'domain', 'err_log', 'err_lin'])
df.to_csv('results/_dim_split_recomputed.csv', index=False, encoding='utf-8-sig')
print('\n→ results/_dim_split_recomputed.csv')
