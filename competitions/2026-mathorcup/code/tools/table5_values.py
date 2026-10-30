# -*- coding: utf-8 -*-
"""从 q1_grade_metrics.csv 抽出表 5 需要的四组中位数（修复后）"""
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def table(path, tag):
    d = pd.read_csv(path)
    out = []
    for prior, lab in (('zeroinfl', '零膨胀分布（本文）'), ('uniform', '均匀分布'),
                       ('mildzero', '轻度零膨胀'), ('equifreq', '等频映射')):
        q = d[f'qwk_{prior}'].median()
        a = d[f'acc_{prior}'].median()
        p = d[f'acc_pm1_{prior}'].median()
        m = d[f'mae_{prior}'].median()
        z = (d[f'frac_round_at_zero'].median() if prior == 'equifreq' else None)
        out.append((lab, q, a, p, m))
    q = d['qwk_round'].median()
    a = d['acc_round'].median()
    z = d['frac_round_at_zero'].median()
    out.append(('平移后直接取整（反例）', q, a, None, None))
    print(f'--- {tag} ---')
    print(f'{"方案":22s} {"kappa":>8s} {"同档率":>8s} {"±1档":>8s} {"MAE":>8s} {"压0":>8s}')
    for lab, q, a, p, m in out:
        print(f'{lab:22s} {q:8.4f} {a:8.3f} '
              f'{(f"{p:8.3f}" if p is not None else "       -")} '
              f'{(f"{m:8.3f}" if m is not None else "       -")}')
    print(f'{"":22s} {"":8s} {"":8s} {"":8s} {"":8s} 压0={z:.3f}')
    ks = [o[1] for o in out[:4]]
    print(f'四组 kappa 极差 = {max(ks) - min(ks):.4f}')
    return out


table('_freeze/before_fix/q1_grade_metrics.csv', '修复前')
print()
table('results/q1_grade_metrics.csv', '修复后')
