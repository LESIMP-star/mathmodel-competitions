# -*- coding: utf-8 -*-
"""逐条复核 5.2 节（量纲与共线结构）里的四个数：
   33 列线性 / 37 列 log10 / 161 列待判 / 145 含负 / 15 全>1 / 1 全非负最小<1
判定方法：与附件8 Calibrated chemical dataset 逐列比，不用阈值猜。
"""
import sys

import numpy as np
import openpyxl
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

X = pd.read_csv('附件/1.csv').iloc[:, 3:]
wb = openpyxl.load_workbook('附件/8.xlsx', read_only=True, data_only=True)
ws = wb['Calibrated chemical dataset']
rows = ws.iter_rows(values_only=True)
hdr = [str(h) if h is not None else '' for h in next(rows)]
D = pd.DataFrame(list(rows), columns=hdr)

common = [c for c in X.columns if c in D.columns]
print(f'1.csv 化学列 {X.shape[1]}；与 Calibrated 同名 {len(common)}')

lin, logc, undec = [], [], []
for c in common:
    a = pd.to_numeric(X[c], errors='coerce')
    b = pd.to_numeric(D[c], errors='coerce')
    m = a.notna() & b.notna() & (b.abs() > 1e-12)
    if m.sum() < 20:
        undec.append((c, 'n<20'))
        continue
    av, bv = a[m].to_numpy(), b[m].to_numpy()
    rel_lin = np.nanmedian(np.abs(av - bv) / np.maximum(np.abs(bv), 1e-12))
    with np.errstate(all='ignore'):
        rel_log = np.nanmedian(np.abs(av - np.log10(np.abs(bv))))
    if rel_lin < 1e-3:
        lin.append(c)
    elif rel_log < 1e-3:
        logc.append(c)
    else:
        undec.append((c, f'lin={rel_lin:.2e} log={rel_log:.2e}'))

print(f'  线性   {len(lin)}')
print(f'  log10  {len(logc)}')
print(f'  未判   {len(undec)}')
for c, why in undec[:6]:
    print(f'    · {c[:40]:42s} {why}')

# 剩下没对照的列，按取值范围判
rest = [c for c in X.columns if c not in set(common)]
print(f'\nCalibrated 无对照的列：{len(rest)}')
n_neg = [c for c in rest if X[c].min() < 0]
print(f'  含负值（只能来自对数域）：{len(n_neg)}')
pos = [c for c in rest if X[c].min() >= 0]
print(f'  全非负：{len(pos)}')
gt1 = [c for c in pos if X[c].min() > 1]
lt1 = [c for c in pos if X[c].min() <= 1]
print(f'    其中最小值 > 1（原始浓度全大于1，应判线性）：{len(gt1)}')
print(f'    其中最小值 ≤ 1（无法判，需人工）：{len(lt1)}')
for c in lt1:
    print(f'      {c[:44]:46s} min={X[c].min():.6f} max={X[c].max():.4f}')

n_log_total = len(logc) + len(n_neg)
n_lin_total = len(lin) + len(gt1) + len(lt1)
print(f'\n合计：log10 {n_log_total} + 线性 {n_lin_total} = {n_log_total + n_lin_total}')
print(f'论文 5.2 节写的：33 线性 / 37 log10 确认 / 161 待判 / 145 含负 / 15 全>1 / 1 全非负最小<1')
print(f'论文合计：182 log10 / 49 线性')
