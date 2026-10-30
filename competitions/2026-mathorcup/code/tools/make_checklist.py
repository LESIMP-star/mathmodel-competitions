# -*- coding: utf-8 -*-
"""把论文里引用的每个 Q1 派生统计量，按修复前后各算一遍，产出核对清单 CSV。"""
import io
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BEF, AFT = '_freeze/before_fix', 'results'

# 15 个嗅觉项 / 15 个味觉项 / 其余 20 项（论文 9.2 的分类口径）
SMELL = ['A_malt_all', 'A_malt_grain', 'A_malt_bread', 'A_malt_cara', 'A_malt_burn',
         'A_hops_all', 'A_hops_citrus', 'A_hops_tropical', 'A_hops_noble',
         'A_hops_woody', 'A_esters_all', 'A_esters_ethac', 'A_esters_isoaa',
         'A_esters_fruity', 'A_esters_flower']
TASTE = ['acidity', 'bitternes', 'sweetness', 'X4vg', 'diacetyl', 'dms',
         'metallic', 'stale_hops', 't2n', 'orange', 'coriander', 'clove',
         'lactic', 'acetic', 'barnyard']


def load(d):
    m = pd.read_csv(os.path.join(d, 'q1_metrics.csv')).set_index('sens')
    run = json.load(open(os.path.join(d, 'q1_run_log.json'), encoding='utf-8'))
    gr = json.load(open(os.path.join(d, 'q1_grade_summary.json'), encoding='utf-8'))
    return m, run, gr


mb, rb, gb = load(BEF)
ma, ra, ga = load(AFT)

rows = []


def add(item, before, after, note=''):
    rows.append(dict(项目=item, 修复前=before, 修复后=after,
                     Δ=(after - before) if isinstance(after, (int, float))
                     and isinstance(before, (int, float)) else '',
                     说明=note))


r2b, r2a = mb['R2'], ma['R2']
add('R² 中位', round(r2b.median(), 4), round(r2a.median(), 4), '9.2 / 摘要 / 结论')
add('R² 均值', round(r2b.mean(), 4), round(r2a.mean(), 4), '9.2 / 摘要')
add('R² 为正的项数', int((r2b > 0).sum()), int((r2a > 0).sum()), '9.2')
add('R²>0.5 的项数', int((r2b > 0.5).sum()), int((r2a > 0.5).sum()), '9.2')
add('R²<0.10 的项数', int((r2b < 0.10).sum()), int((r2a < 0.10).sum()), '9.2')
add('最强项 R²（acidity）', round(r2b.max(), 4), round(r2a.max(), 4), '6.5 / 摘要')
add('最弱项 R²（stale_hops）', round(r2b.min(), 4), round(r2a.min(), 4), '6.5')

for name, s in (('best_target', None),):
    pass
for t in ('acidity', 'alcohol', 'lactic', 'acetic', 'bitternes', 'body',
          'overall', 'F_esters_flower', 'stale_hops', 'orange', 'co2',
          'diacetyl', 'dms', 'X4vg', 't2n', 'metallic', 'sweetness',
          'aftertaste', 'barnyard', 'clove', 'coriander'):
    if t in r2b.index:
        add(f'{t} 的 R²', round(r2b[t], 4), round(r2a[t], 4), '表 6 / 正文')

# 三类均值
for nm, lst in (('15 个嗅觉项 R² 均值', SMELL), ('15 个味觉项 R² 均值', TASTE)):
    ls = [s for s in lst if s in r2b.index]
    add(nm, round(r2b[ls].mean(), 4), round(r2a[ls].mean(), 4), '9.2')
    add(nm.replace('均值', '中位'), round(r2b[ls].median(), 4),
        round(r2a[ls].median(), 4), '9.2')
othb = [s for s in r2b.index if s not in SMELL + TASTE]
add('其余 20 项 R² 均值', round(r2b[othb].mean(), 4),
    round(r2a[othb].mean(), 4), '9.2')

# 等级映射
K = [('median_qwk', '加权 kappa 中位', '表 5 / 摘要'),
     ('n_qwk_gt_0p3', 'kappa>0.3 的项数', '6.8'),
     ('n_qwk_gt_0p5', 'kappa>0.5 的项数', '6.8'),
     ('median_qwk_uniform', 'uniform kappa 中位', '表 5'),
     ('median_qwk_mildzero', 'mildzero kappa 中位', '表 5'),
     ('median_qwk_equifreq', 'equifreq kappa 中位', '表 5'),
     ('median_qwk_round', '直接取整 kappa', '表 5 反例'),
     ('median_acc', '同档率', '表 5'),
     ('median_acc_pm1', '±1 档命中率', '表 5'),
     ('median_mae_grade', '等级 MAE', '表 5'),
     ('median_acc_round', '取整的准确率', '表 5 反例'),
     ('median_frac_round_at_zero', '取整压到 0 档占比', '表 5 / 摘要'),
     ('median_acc_uniform', 'uniform 同档率', '表 5'),
     ('median_acc_mildzero', 'mildzero 同档率', '表 5'),
     ('median_acc_equifreq', 'equifreq 同档率', '表 5'),
     ('median_mae_grade_uniform', 'uniform 等级 MAE', '表 5'),
     ('median_mae_grade_mildzero', 'mildzero 等级 MAE', '表 5'),
     ('median_mae_grade_equifreq', 'equifreq 等级 MAE', '表 5'),
     ('worst_qwk', '最差维度 kappa', '6.8'),
     ('mean_qwk', 'kappa 均值', '6.8'),
     ('best_qwk', '最好维度 kappa', '6.8'),
     ]
for k, nm, where in K:
    if k in gb and k in ga:
        vb, va = gb[k], ga[k]
        if isinstance(vb, (int, float)):
            vb = round(vb, 4) if isinstance(vb, float) else vb
            va = round(va, 4) if isinstance(va, float) else va
        add(nm, vb, va, where)

# 四组 kappa 极差
if all(k in ga for k in ('median_qwk', 'median_qwk_uniform',
                         'median_qwk_mildzero', 'median_qwk_equifreq')):
    kb = [gb['median_qwk'], gb['median_qwk_uniform'],
          gb['median_qwk_mildzero'], gb['median_qwk_equifreq']]
    ka = [ga['median_qwk'], ga['median_qwk_uniform'],
          ga['median_qwk_mildzero'], ga['median_qwk_equifreq']]
    add('四组 kappa 极差', round(max(kb) - min(kb), 4),
        round(max(ka) - min(ka), 4), '6.8 / 表 5')

# 两两 Spearman：q1_grades.py 只落盘主先验（zeroinfl）的分级矩阵，
# 四组先验之间的 Spearman 需要额外持久化才能复算，此处不做，README 里标注为待复算。
s_b = s_a = ('需另行复算', '需另行复算')

# 外部效度
for k, nm in (('ext_median_rho_pred_vs_7', '预测 vs 附件7 的 ρ'),
              ('ext_median_rho_label_vs_7', '标签 vs 附件7 的 ρ'),
              ('ext_median_r2_pred_vs_7', '预测 vs 附件7 的 R²')):
    if k in rb and k in ra:
        add(nm, round(rb[k], 4), round(ra[k], 4), '6.7')

df = pd.DataFrame(rows)
df = df[df['项目'] != '分级结果两两 Spearman 区间']
df['变动'] = df.apply(
    lambda r: '改了' if (isinstance(r['Δ'], float) and abs(r['Δ']) > 1e-4) else '不变',
    axis=1)

pd.set_option('display.width', 220)
pd.set_option('display.max_rows', 100)
print('=' * 96)
print(f'{len(df)} 个派生统计量，其中 {sum(df["变动"] == "改了")} 个数值变了')
print('=' * 96)
print(df.to_string(index=False))

df.to_csv('_freeze/论文核对清单.csv', index=False, encoding='utf-8-sig')
print('\n→ _freeze/论文核对清单.csv')
