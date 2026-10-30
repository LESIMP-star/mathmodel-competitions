# -*- coding: utf-8 -*-
"""支撑材料自检：数据能否读入、全部脚本能否导入、关键结果文件是否齐全。

用法：
    python code/selftest.py          # 在支撑材料根目录下运行
退出码 0 = 全部通过。
"""
import importlib
import os
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
os.chdir(PROJ)
sys.path.insert(0, ROOT)

OK, BAD = [], []


def ck(name, cond, detail=''):
    (OK if cond else BAD).append(name)
    print(f'  {"OK " if cond else "FAIL"}  {name}{("  " + detail) if detail else ""}')


print('【1】数据读入')
X = pd.read_csv('附件/1.csv')
Y = pd.read_csv('附件/4.csv')
R = pd.read_csv('附件/2.csv', index_col=0)
# 前 3 列是样本标识（beer / beer_id / tasting_category_fine），不计入特征
ck('附件1 化学谱 250×234（含 3 列标识 → 231 特征）',
   X.shape == (250, 234) and X.shape[1] - 3 == 231, str(X.shape))
ck('附件4 感官 250×53（含 3 列标识 → 50 感官项）',
   Y.shape == (250, 53) and Y.shape[1] - 3 == 50, str(Y.shape))
ck('附件2 相关矩阵 231×231', R.shape == (231, 231), str(R.shape))

print('\n【2】脚本可导入')
for mod in ('q0_relations', 'q1', 'q1_helpers', 'q1_grades', 'q2',
            'q3', 'q3_transfer', 'robustness_q3', 'nsga2'):
    try:
        importlib.import_module(mod)
        ck(mod, True)
    except Exception as e:                     # noqa: BLE001
        ck(mod, False, f'{type(e).__name__}: {e}')

print('\n【3】关键结果文件')
NEED = ['q1_metrics.csv', 'q1_run_log.json', 'q1_grade_summary.json',
        'q2_top3.csv', 'q2_run_log.json',
        'q3_pareto.csv', 'q3_run_log.json',
        'q3_sensitivity_span.csv', 'q3_transfer_run_log.json']
for f in NEED:
    ck(f, os.path.exists(os.path.join('results', f)))

print('\n【4】数字自洽')
try:
    par = pd.read_csv('results/q3_pareto.csv')
    ck('Q3 前沿 7 点', len(par) == 7, f'{len(par)} 点')
    ck('Q3 f2 全为 0', float(par.f2.max()) < 1e-9)
    if 'e_f3' in par.columns:
        ck('e_f3 - f3 >= 0', bool((par.e_f3 - par.f3 >= -1e-6).all()))
    sp = pd.read_csv('results/q3_sensitivity_span.csv')
    base = pd.read_csv('results/q3_sensitivity.csv')
    b = float(base[(base.param == 'gamma') & (base.value == 1.0)].f1.iloc[0])
    ck('灵敏度基准 = P1 的 f1', abs(b - float(par.f1.min())) < 1e-4,
       f'{b:.4f} vs {float(par.f1.min()):.4f}')
except Exception as e:                          # noqa: BLE001
    ck('Q3 自洽检查', False, str(e))

print('\n' + '=' * 50)
print(f'通过 {len(OK)} / 失败 {len(BAD)}')
if BAD:
    for b in BAD:
        print(f'  ✗ {b}')
sys.exit(0 if not BAD else 1)
