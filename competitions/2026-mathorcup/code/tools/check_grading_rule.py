# -*- coding: utf-8 -*-
"""按论文 6.8 节自己写的规则（切点只由真值定，预测沿用同一组切点）重算分级指标，
与现实现（真值、预测各自排序到同一先验）对比。"""
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PRIORS = {
    'zeroinfl': [0.50, 0.18, 0.12, 0.09, 0.06, 0.035, 0.015],
    'uniform': [1 / 7] * 7,
    'mildzero': [0.35, 0.20, 0.16, 0.13, 0.09, 0.05, 0.02],
    'equifreq': [1 / 7] * 7,
}


def qwk(a, b, k=7):
    a = np.asarray(a, int)
    b = np.asarray(b, int)
    O = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            O[i, j] = np.sum((a == i) & (b == j))
    w = (np.subtract.outer(np.arange(k), np.arange(k)) ** 2) / (k - 1) ** 2
    n = O.sum()
    if n == 0:
        return np.nan
    E = np.outer(O.sum(1), O.sum(0)) / n
    denom = (w * E).sum()
    return np.nan if denom == 0 else 1 - (w * O).sum() / denom


def rank_map(z, prior):
    """现实现：按自身秩映射到先验（真值与预测各自重排序）"""
    z = np.asarray(z, float)
    r = pd.Series(z).rank(method='average').values / len(z)
    cdf = np.cumsum(prior)
    return np.clip(np.searchsorted(cdf, r, side='left'), 0, 6)


def cut_from_truth(yt, prior):
    """论文所述规则：切点 = 真值的累积分位点"""
    cdf = np.cumsum(prior)[:-1]
    return np.quantile(yt, cdf)


def apply_cuts(z, cuts):
    z = np.asarray(z, float)
    return np.clip((z[:, None] > cuts[None, :]).sum(axis=1), 0, 6)


m = pd.read_csv('results/q1_predictions.csv')
lab = pd.read_csv('附件/4.csv') if __import__('os').path.exists('附件/4.csv') else None
if lab is None:
    import glob
    lab = pd.read_csv(glob.glob('附件*/**/4.csv', recursive=True)[0])
m = m.merge(lab[['beer'] + [c for c in lab.columns if c != 'beer']],
            on='beer', suffixes=('_p', '_t'))
print(f'q1_predictions.csv {m.shape}')
cols_t = [c for c in m.columns if c.endswith('_t')]
sens = [c[:-2] for c in cols_t]
print(f'{len(sens)} 个感官项')

for pname in ('zeroinfl', 'uniform'):
    prior = PRIORS[pname]
    q_self, q_cut, acc_self, acc_cut = [], [], [], []
    tv_self = []
    for s in sens:
        yt = m[f'{s}_t'].to_numpy(float)
        yp = m[f'{s}_p'].to_numpy(float)
        ok = np.isfinite(yt) & np.isfinite(yp)
        if ok.sum() < 30:
            continue
        yt, yp = yt[ok], yp[ok]

        # 现实现
        gt_a, gp_a = rank_map(yt, prior), rank_map(yp, prior)
        q_self.append(qwk(gt_a, gp_a))
        acc_self.append(np.mean(gt_a == gp_a))
        tv_self.append(0.5 * np.abs(np.bincount(gt_a, minlength=7) / len(gt_a)
                                    - np.bincount(gp_a, minlength=7) / len(gp_a)).sum())

        # 论文所述规则
        cuts = cut_from_truth(yt, prior)
        gt_b = apply_cuts(yt, cuts)
        gp_b = apply_cuts(yp, cuts)
        q_cut.append(qwk(gt_b, gp_b))
        acc_cut.append(np.mean(gt_b == gp_b))

    q_self, q_cut = np.array(q_self), np.array(q_cut)
    print(f'\n── {pname} ──')
    print(f'  现实现（各自排序）：QWK 中位 {np.median(q_self):.4f}，'
          f'>0.3 的项 {int((q_self > 0.3).sum())}/{len(q_self)}，'
          f'同档率 {np.median(acc_self):.3f}，TV {np.median(tv_self):.4f}')
    print(f'  论文规则（真值定切点）：QWK 中位 {np.median(q_cut):.4f}，'
          f'>0.3 的项 {int((q_cut > 0.3).sum())}/{len(q_cut)}，'
          f'同档率 {np.median(acc_cut):.3f}')
    print(f'  QWK 变化：{np.median(q_cut) - np.median(q_self):+.4f}')
