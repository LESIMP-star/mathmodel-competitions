# -*- coding: utf-8 -*-
"""Q2 优化路径 B：跨感官项的共识归因

逐项 Top-3 不稳定（Jaccard 0.0974、consrank 中位 11.8、40/50 项无稳定化合物），
说明"每项独立选前 3"这个读法在本数据上不可稳定回答。改问一个更稳的问题：
哪些化合物在多个感官项上同时排进前 5？这是题目允许的另一种读法，
且因为要求跨项一致，随机噪声难以同时抬高同一化合物在多个项上的排名。
"""
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

cr = pd.read_csv('results/q2_feature_consrank.csv', index_col=0)
t3 = pd.read_csv('results/q2_top3.csv')
pi = pd.read_csv('results/q2_feature_pi.csv', index_col=0)
AROMA = set(t3.feat.astype(str))

# 每项内对香气化合物按 consrank 排名（1 = 最稳定靠前）
rank_in = pd.DataFrame(index=cr.index, columns=sorted(AROMA), dtype=float)
for sens in cr.index:
    cand = [(f, float(cr.loc[sens, f])) for f in AROMA
            if f in cr.columns and np.isfinite(cr.loc[sens, f])]
    cand.sort(key=lambda x: x[1])
    for i, (f, _) in enumerate(cand, 1):
        rank_in.loc[sens, f] = i

for K in (3, 5, 10):
    hits = (rank_in <= K).sum(axis=0).sort_values(ascending=False)
    print(f'=== 进入前 {K} 名的项数分布 ===')
    print(f'  至少 1 项: {(hits >= 1).sum()} 个化合物')
    print(f'  至少 3 项: {(hits >= 3).sum()}')
    print(f'  至少 5 项: {(hits >= 5).sum()}')
    print(f'  至少 10 项: {(hits >= 10).sum()}')
    print('  Top 8：')
    for f, n in hits.head(8).items():
        # π 均值与所属族
        pv = float(np.nanmean(pi[f].values)) if f in pi.columns else np.nan
        print(f'    {f:34s} {n:3d} 项   mean π={pv:.3f}')
    print()

hits5 = (rank_in <= 5).sum(axis=0).sort_values(ascending=False)
out = pd.DataFrame(dict(feat=hits5.index, n_top5=hits5.values))
out['n_top3'] = out.feat.map(lambda f: int((rank_in[f] <= 3).sum()))
out['mean_pi'] = out.feat.map(
    lambda f: round(float(np.nanmean(pi[f].values)), 4) if f in pi.columns else np.nan)
out.to_csv('results/q2_consensus.csv', index=False, encoding='utf-8-sig')
print('写出 results/q2_consensus.csv')
