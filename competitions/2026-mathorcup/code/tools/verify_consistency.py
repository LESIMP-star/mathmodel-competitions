# -*- coding: utf-8 -*-
"""复核：results/ 与 _freeze/after_fix/ 与 修复包/results/ 三者是否一致"""
import hashlib
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

A = 'results'
B = '_freeze/after_fix'
C = 'dist/修复包_问题一预处理_20261030/results'
Z = 'dist/修复包_问题一预处理_20261030.zip'


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''):
            h.update(c)
    return h.hexdigest()


FILES = ['q1_metrics.csv', 'q1_predictions.csv', 'q1_run_log.json',
         'q1_grade_summary.json', 'q1_grade_metrics.csv', 'q1_grades.csv',
         'q1_residual_stats.csv', 'q1_floor_fit.csv', 'q1_external.csv']

print(f'{"文件":28s} {"results":10s} {"冻结":10s} {"包内":10s} 一致')
ok = True
for f in FILES:
    pa, pb, pc = (os.path.join(d, f) for d in (A, B, C))
    if not all(os.path.exists(x) for x in (pa, pb, pc)):
        print(f'{f:28s} 缺文件')
        ok = False
        continue
    ha, hb, hc = md5(pa), md5(pb), md5(pc)
    same = ha == hb == hc
    ok &= same
    print(f'{f:28s} {ha[:8]:10s} {hb[:8]:10s} {hc[:8]:10s} {"✓" if same else "✗"}')

print()
print('三者完全一致' if ok else '存在不一致，需重新冻结/打包')

# zip 内文件数
import zipfile
with zipfile.ZipFile(Z) as z:
    names = z.namelist()
    bad = z.testzip()
print(f'zip: {len(names)} 项，损坏 {bad or "无"}')

# 日志尾部
print()
for lg, tag in (('code/log_q1_fixed.txt', 'q1'),
                ('code/log_q1grades_fixed.txt', 'grades'),
                ('code/log_q1diag_fixed.txt', 'diag')):
    if os.path.exists(lg):
        lines = [x for x in open(lg, encoding='utf-8', errors='replace').read().split('\n') if x.strip()]
        print(f'[{tag}] {lines[-2][:90] if len(lines) > 1 else ""}')
        print(f'       {lines[-1][:90] if lines else ""}')
