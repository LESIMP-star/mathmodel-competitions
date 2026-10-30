# -*- coding: utf-8 -*-
"""复核 5.2 节的分域数字：33 线性 / 37 log10 确认 / 161 待判 / 145 含负 / 15 全>1 / 1 全非负。"""
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

X = pd.read_csv('附件/1.csv').iloc[:, 3:]
print(f'化学列 {X.shape[1]}')

neg_all = int((X.min() < 0).sum())
print(f'含负值的列（全表）: {neg_all}')

# Calibrated 表对照：把 8.xlsx 的 Calibrated 读出来逐列比
import openpyxl
wb = openpyxl.load_workbook('附件/8.xlsx', read_only=True, data_only=True)
print('8.xlsx sheets:', wb.sheetnames)
cal = None
for nm in wb.sheetnames:
    if 'calib' in nm.lower():
        cal = nm
        break
print('Calibrated sheet:', cal)
if cal:
    ws = wb[cal]
    rows = ws.iter_rows(values_only=True)
    hdr = next(rows)
    print(f'  Calibrated {len(hdr)} 列，表头前 6: {[str(h)[:18] for h in hdr[:6]]}')
    body = list(rows)
    D = pd.DataFrame(body, columns=[str(h) for h in hdr])
    common = [c for c in X.columns if c in D.columns]
    print(f'  与 1.csv 同名共 {len(common)} 列')
    lin, logc = [], []
    for c in common:
        a = pd.to_numeric(X[c], errors='coerce')
        b = pd.to_numeric(D[c], errors='coerce')
        m = a.notna() & b.notna() & (a.abs() > 1e-12)
        if m.sum() < 20:
            continue
        # 线性：X ≈ D；对数：X ≈ log10(D)
        e_lin = np.nanmedian(np.abs(a[m] - b[m]) / np.maximum(np.abs(b[m]), 1e-9))
        with np.errstate(all='ignore'):
            e_log = np.nanmedian(np.abs(a[m] - np.log10(b[m].clip(lower=1e-30))))
        if e_lin < 1e-3:
            lin.append(c)
        elif e_log < 1e-2:
            logc.append(c)
    print(f'  判为线性 {len(lin)}，判为 log10 {len(logc)}，'
          f'未能判定 {len(common) - len(lin) - len(logc)}')

# 待判那批的人工判据
undetermined = [c for c in X.columns if c not in set(lin if cal else []) | set(logc if cal else [])]
n_neg = sum(1 for c in undetermined if X[c].min() < 0)
n_pos_all_gt1 = sum(1 for c in undetermined
                    if X[c].min() >= 0 and X[c].min() >= 0 and X[c].max() > 1)
print(f'\n待判 {len(undetermined)} 列中：含负值 {n_neg}')
