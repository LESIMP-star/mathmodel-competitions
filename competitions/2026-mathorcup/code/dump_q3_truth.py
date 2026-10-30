# -*- coding: utf-8 -*-
"""打印 q3 相关全部真值，供同步 audit_paper.py。"""
import json
import os
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

R = 'results'
par = pd.read_csv(os.path.join(R, 'q3_pareto.csv'))
log = json.load(open(os.path.join(R, 'q3_run_log.json'), encoding='utf-8'))
sm = json.load(open(os.path.join(R, 'q3_sensitivity_summary.json'), encoding='utf-8'))
sp = pd.read_csv(os.path.join(R, 'q3_sensitivity_span.csv')).set_index('param')
tr = json.load(open(os.path.join(R, 'q3_transfer_run_log.json'), encoding='utf-8'))

c = log.get('compare', {})
print('=== q3_pareto ===')
print(f'  点数            {len(par)}')
print(f'  status OPTIMAL  {int((par.status == "OPTIMAL").sum())}')
print(f'  mip_gap==0      {int((par.mip_gap == 0).sum())}   最大 gap {par.mip_gap.max():.3e}')
print(f'  hard_feasible   {int(par.hard_feasible.astype(str).str.lower().eq("true").sum())}')
print(f'  f1 min          {par.f1.min():.6f}')
print(f'  f1 max          {par.f1.max():.6f}')
print(f'  f2 max          {par.f2.max():.9f}')
print(f'  基线 f1         {log["baseline_x0"]["f1"]:.6f}')
print(f'  降幅            {100 * (1 - par.f1.min() / log["baseline_x0"]["f1"]):.2f}%')
print(f'  决策维/变量/约束 {par.nbin.iloc[0]}/{par.nvars.iloc[0]}/{par.nconstr.iloc[0]}')

print('\n=== compare ===')
for k, v in c.items():
    print(f'  {k:28s} {v}')

print('\n=== sensitivity ===')
print(f'  n_runs          {sm["n_runs"]}')
print(f'  base_f1         {sm["base_f1"]:.6f}')
for p in ('gamma', 'pls_k', 'eps3', 'lambda', 'eps2', 'k_max'):
    print(f'  {p:8s} span    {sp.loc[p, "span"]:.6f}')

print('\n=== transfer ===')
for k in list(tr)[:8]:
    print(f'  {k:22s} {tr[k]}')
