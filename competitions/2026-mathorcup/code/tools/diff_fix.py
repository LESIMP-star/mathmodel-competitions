# -*- coding: utf-8 -*-
"""对比修复前后的结果，产出「论文需要改哪些数字」的核对清单。"""
import io
import json
import os
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BEF = '_freeze/before_fix'
AFT = 'results'
OUT = '_freeze'

rows = []


def jdiff(name, keys=None):
    pb, pa = os.path.join(BEF, name), os.path.join(AFT, name)
    if not (os.path.exists(pb) and os.path.exists(pa)):
        return
    b = json.load(open(pb, encoding='utf-8'))
    a = json.load(open(pa, encoding='utf-8'))
    for k in (keys or b):
        if k not in a or not isinstance(b[k], (int, float)):
            continue
        rows.append(dict(file=name, key=k, before=b[k], after=a[k],
                         delta=(a[k] - b[k]) if isinstance(a[k], (int, float)) else None))


jdiff('q1_run_log.json')
jdiff('q1_grade_summary.json')

# 逐维 R²
pb, pa = os.path.join(BEF, 'q1_metrics.csv'), os.path.join(AFT, 'q1_metrics.csv')
if os.path.exists(pb) and os.path.exists(pa):
    b = pd.read_csv(pb).set_index('sens')
    a = pd.read_csv(pa).set_index('sens')
    for s in a.index:
        if s in b.index and 'R2' in a.columns:
            rows.append(dict(file='q1_metrics.csv', key=f'R2[{s}]',
                             before=b.at[s, 'R2'], after=a.at[s, 'R2'],
                             delta=a.at[s, 'R2'] - b.at[s, 'R2']))

df = pd.DataFrame(rows)
if len(df) == 0:
    print('无对比数据')
    sys.exit(0)

df['abs_delta'] = df['delta'].abs()
df = df.sort_values('abs_delta', ascending=False)

pd.set_option('display.width', 200)
print('=' * 78)
print(f'共 {len(df)} 项，|Δ| > 1e-4 的有 {(df["abs_delta"] > 1e-4).sum()} 项')
print('=' * 78)
print(df.head(30)[['file', 'key', 'before', 'after', 'delta']].to_string(index=False))

df.to_csv(os.path.join(OUT, 'diff_before_after.csv'), index=False,
          encoding='utf-8-sig')
print(f'\n完整对比 → {OUT}/diff_before_after.csv')

# 论文里出现的 Q1 数字
PAPER = ['0.1471', '0.2219', '0.7149', '0.7108', '0.6324', '0.6113',
         '0.5862', '0.5490', '0.0293', '0.3433', '0.376', '0.666', '1.200']
txt = ''
for f in os.listdir('latex模板/sections'):
    if f.endswith('.tex'):
        txt += io.open(f'latex模板/sections/{f}', encoding='utf-8',
                       newline='').read()
txt += io.open('latex模板/main.tex', encoding='utf-8', newline='').read()

print('\n论文中出现的 Q1 关键值 → 新值：')
for p in PAPER:
    hit = df[df['before'].astype(str).str.startswith(p)]
    cnt = txt.count(p)
    if len(hit):
        r = hit.iloc[0]
        print(f'  {p:8s} 论文出现 {cnt:2d} 次 → 新值 {r["after"]:.6g}')
    else:
        print(f'  {p:8s} 论文出现 {cnt:2d} 次 → 未变动')
