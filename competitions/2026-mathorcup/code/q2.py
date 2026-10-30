# -*- coding: utf-8 -*-
"""q2.py — 问题二：逐维 Top-3 关键化合物归因
（置换重要性 + bootstrap 稳定性 + 跨模型一致性 + FDR 反解阈值 + OAV 化学裁判）

本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：Hermes Agent（Nous Research），底层模型 deepseek-v4-flash，
# 开发机构：Nous Research（工具）/ 深度求索 DeepSeek（模型），使用日期：2026-10-26

================================================================ 为什么不用 8.xlsx 的 MDI / SHAP
那两个 sheet 是**单模型、无稳定性、全局一次性**的产物，且 MDI 在共线特征间分配任意
（同组高度相关的列会随机分摊重要性）。本题 p=231、n=250，单模型变量重要性的
bootstrap 方差极大，不可作为结论使用。

================================================================ 评估口径（本文件最关键的一处修正）
置换重要性必须在**模型没见过的行**上计算。在训练行上置换会被提升树自身的
过拟合严重扭曲（特征被记住一次就"很重要"）。
- 稳定性 π 用 **bootstrap OOB**：重采样留下的约 36.8% 未选中行直接作评估集，零额外成本；
- 跨模型一致性用**固定分层 70/30**：三个模型族必须在同一评估集上排名才可比，
  否则差异里混进了"评估集不同"这个混杂因素。

================================================================ 三层证据线
① 主归因：逐列置换重要性（R² 下降量）。组标签取自 8.xlsx `Sensory thresholds` 的
   `origin_paper`（Yeast 78 / Hops 77 / Others 25 / Spices 23 / Malt 21 / Wild flora 6 /
   Internal std 1，合计 231；5 个派生总量无标注，归入 Others）。
   为什么逐列而不整组同时置换：整组只给 7 个族级数值，要落到单个化合物的 Top-3 必须
   人为摊派比例，而摊派方式本身决定排名；本题要找的是"可单独调控的化合物"，
   逐列置换的语义（该列的可替代性）才对。代价是同族顶替会低估重要性（Strobl 等 2008），
   故用 200 次重采样的入选频率做稳健化。
② 稳定性：bootstrap N=200（题面建议下限 30），记录入选频率 π_j。
   **π 只度量同一模型族下的重采样稳定性，不度量换模型族是否还选它** ——
   这两个概念必须分开报，否则 π 会被误读为稳健性。
③ 阈值不拍脑袋：稳定性选择的有限样本界反解
        π_thr = (1 + q/p) / 2，取 q=1、p=231 → 0.5022
   **注意 q 的含义**：界 E[V] ≤ q_sel²/((2π−1)p) 里的 q_sel 是基础选择程序
   每次选出的变量数（本题 10），不是错误发现预算。本文取 q=1、即"期望误选 1 个"
   这一操作性标准，**不构成 0.05 水平的 FDR 控制**。若按 q_sel=10 原义代入，
   同一式给 0.7165，本文未用。论文只能称"入选频率阈值"，不能称"控制 FDR"。
④ 化学裁判：OAV = 浓度 / 阈值，**必须按量纲分开算**——
   37 个 log10 列 OAV = 10^x/θ；线性列 OAV = x/θ。
   若对 37 列直接 x/θ，OAV 会系统性偏小 1~2 个数量级（常见口径错误）。
   实测 231 个特征中仅 43 个有文献阈值 → 188 个无法算 OAV，这一覆盖率限制
   必须在论文里如实说明，不能只报能算的那些。

================================================================ 范畴分离
理化指标（protein / color.EBC / pH / iron / GFS / bitterness / ethanol / CO2 /
unfermentables / betaglucan / glycerol / SO2 / ammonia）是**机制代理**，不是香气化合物。
实测它们确实主导若干靶的置换重要性（bitternes→bitterness、metallic→iron、
X4vg→X4VG、sweetness→GFS，近乎同义反复），但写进"关键香气化合物 Top-3"是范畴错误。
故输出两张表：
  q2_top3.csv              50×3  **香气化合物** Top-3
  q2_top3_physicochem.csv  50×3  **理化代理** Top-3（供 Q3 约束与机制解释）

================================================================ 输出
  results/q2_top3.csv              50 × 3 香气化合物（π / 组 / OAV / 跨模型支持 / 证据等级）
  results/q2_top3_physicochem.csv  50 × 3 理化代理
  results/q2_feature_pi.csv        50 × 226 π 矩阵
  results/q2_feature_consrank.csv  50 × 226 跨模型平均秩
  results/q2_jaccard.csv           跨方法 Top-10 Jaccard（逐靶）
  results/q2_fdr.csv               q → π_thr 反解表
  results/q2_oav.csv               逐特征 OAV（按量纲分算）
  results/q2_run_log.json

================================================================ 运行
  python q2.py             # 完整 200 次 bootstrap
  python q2.py --quick     # 30 次（仅冒烟）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, '附件')
RES = os.path.join(ROOT, 'results')
os.makedirs(RES, exist_ok=True)

SEED = 2026
DERIVED = ['kcalperc', 'esters_sum', 'aroma_hops_sum', 'acids_sum', 'sulfur_sum']
N_BOOT = 200
TOP_K = 3
TOP_MEASURE = 10
Q_TARGET = 1.0
N_JOBS = 4
FAMILIES = ('lgbm', 'et', 'ridge')
CONS_EVAL_FRAC = 0.30

# 37 个 log10 列（1.csv 中已是 log10 值，与原值的关系为 10^x）。
# 名单由对 8.xlsx `Calibrated chemical dataset` 逐列对拍得出：
# 判定准则 |10^a − b|/|b| 的中位数显著小于 |a − b|/|b|（70/70 列可判定，0 列歧义）。
LOG10_COLS = {
    'acetaldehyde', 'CS2', 'DES', 'DMS', 'ethyl_2.methyl_butyrate', 'ethyl_acetate',
    'ethyl_decanoate', 'ethyl_hexanoate', 'ethyl_isovalerate', 'ethyl_octanoate',
    'ethyl_propionate', 'H2S', 'isoamyl_alcohol', 'isobutanol', 'isobutyl_acetate',
    'isopentyl_acetate', 'MeSH', 'octyl_acetate', 'phenethyl_acetate',
    'phenethyl_alcohol', 'X4VG', 'SO2.mg.L.', 'acetic_acid.g.L.', 'ammonia.mg.L.',
    'color.EBC.', 'betaglucan.mg.L.', 'lactic_acid.mg.L.', 'glycerol', 'iron', 'pH',
    'protein.g.L.', 'bitterness', 'GFS', 'ethanol..v.v.', 'CO2.PSI.', 'unfermentables',
    'kcalperc',
}

# 理化指标：机制代理，不进"关键香气化合物"
PHYSICOCHEM = {'protein.g.L.', 'color.EBC.', 'pH', 'iron', 'GFS', 'bitterness',
               'ethanol..v.v.', 'CO2.PSI.', 'kcalperc', 'unfermentables',
               'betaglucan.mg.L.', 'glycerol', 'SO2.mg.L.', 'ammonia.mg.L.'}

# 内标：实验室为定量而外加的参照物，不是啤酒自身成分。
# origin_paper='Internal standard solution' 只有 1 个特征（X3.methyl.2.butenal）。
# 实测它曾进入 A_malt_bread 的 Top-1——与理化指标同属范畴错误，一并排除出香气候选池。
NON_AROMA_GROUPS = {'Internal standard solution'}

OAV_TRUST = 1.0
OAV_NEAR = 0.5


def norm_key(s):
    s = str(s).lower()
    for ch in ('_', '-', ' '):
        s = s.replace(ch, '.')
    while '..' in s:
        s = s.replace('..', '.')
    return s.strip('.')


# ============================================================ 数据
def load_all():
    import openpyxl
    c1 = pd.read_csv(os.path.join(DATA, '1.csv'))
    c4 = pd.read_csv(os.path.join(DATA, '4.csv'))
    # 主口径 231 列（与附件2 的 231×231 相关矩阵一致），见 q1.py 顶部说明
    feats = [c for c in c1.columns[3:]]
    sens = [c for c in c4.columns[3:]]

    wb = openpyxl.load_workbook(os.path.join(DATA, '8.xlsx'), read_only=True, data_only=True)
    rows = list(wb['Sensory thresholds'].iter_rows(values_only=True))
    wb.close()
    th = pd.DataFrame(rows[1:], columns=list(rows[0]))
    th['key'] = th['field_name_R'].map(norm_key)
    th_up = th.drop_duplicates('key').set_index('key')

    grp, thr = {}, {}
    for f in feats:
        k = norm_key(f)
        if k in th_up.index:
            g = th_up.at[k, 'origin_paper']
            grp[f] = str(g) if pd.notna(g) else 'Others'
            t = pd.to_numeric(th_up.at[k, 'threshold_mean'], errors='coerce')
            if pd.notna(t) and float(t) > 0:
                thr[f] = float(t)
        else:
            grp[f] = 'Others'

    X = c1.set_index('beer')[feats].apply(pd.to_numeric, errors='coerce')
    Y = c4.set_index('beer')[sens].apply(pd.to_numeric, errors='coerce')
    idx = X.index.intersection(Y.index)
    return X.loc[idx], Y.loc[idx], feats, sens, grp, thr


# ============================================================ 模型族
def _make_model(kind, seed):
    from lightgbm import LGBMRegressor
    from sklearn.ensemble import ExtraTreesRegressor
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if kind == 'lgbm':
        return LGBMRegressor(n_estimators=120, num_leaves=7, min_child_samples=10,
                             learning_rate=0.08, subsample=0.85, colsample_bytree=0.5,
                             reg_lambda=1.0, random_state=seed, n_jobs=2, verbose=-1)
    if kind == 'et':
        return ExtraTreesRegressor(n_estimators=150, max_features='sqrt',
                                   min_samples_leaf=3, random_state=seed, n_jobs=2)
    if kind == 'ridge':
        # 必须标准化：226 列尺度跨越若干数量级，原尺度 Ridge 会被大量纲列完全主导
        return make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    raise ValueError(kind)


def _clip_pred(p, ytr):
    """裁剪回观测值域：连续靶有物理上下界，树模型外推会给出界外值。"""
    return np.clip(p, float(np.min(ytr)), float(np.max(ytr)))


def permutation_importance(Xtr, ytr, Xev, yev, kind='lgbm', seed=SEED,
                           n_repeats=1, top_k=TOP_MEASURE):
    """在**评估集**上做逐列置换，返回 (importance, top_idx)。

    importance_j = R²(基线) − R²(打乱第 j 列)。
    栈式预测：把 p 个置换副本纵向拼接后一次 predict，实测比逐列 predict 快 1.6x，
    两种写法数值完全一致（差 0.000e+00）。
    """
    n_ev, p = Xev.shape
    m = _make_model(kind, seed).fit(Xtr, ytr)
    ss_tot = float(np.sum((yev - yev.mean()) ** 2))
    if ss_tot <= 0 or n_ev < 5:
        return np.zeros(p), np.arange(min(top_k, p))

    base_r2 = 1.0 - float(np.sum((yev - _clip_pred(m.predict(Xev), ytr)) ** 2)) / ss_tot

    rng = np.random.default_rng(seed)
    imp = np.zeros(p)
    for _ in range(n_repeats):
        blocks = []
        for j in range(p):
            Xp = Xev.copy()
            Xp[:, j] = Xp[rng.permutation(n_ev), j]
            blocks.append(Xp)
        pred_all = m.predict(np.vstack(blocks))
        for j in range(p):
            seg = _clip_pred(pred_all[j * n_ev:(j + 1) * n_ev], ytr)
            imp[j] += base_r2 - (1.0 - float(np.sum((yev - seg) ** 2)) / ss_tot)
    imp /= n_repeats
    return imp, np.argsort(-imp)[:top_k]


def _boot_topk(args):
    """一次 bootstrap：重采样行 → 在 OOB 行上算置换重要性 → 返回 Top-k 索引。"""
    X, y, seed, kind, n_repeats = args
    rng = np.random.default_rng(seed)
    n = len(y)
    boot = rng.integers(0, n, n)
    oob = np.setdiff1d(np.arange(n), np.unique(boot))
    if len(oob) < 30:                       # 极小样本退化时退回全样本评估
        oob = np.arange(n)
    _, top = permutation_importance(X[boot], y[boot], X[oob], y[oob],
                                    kind, seed, n_repeats)
    return top


def _stratified_split(y, seed, frac=CONS_EVAL_FRAC):
    """按 y 的分位分层取评估集，保证评估集覆盖靶值域的上下端。"""
    rng = np.random.default_rng(seed)
    n = len(y)
    rank = pd.Series(y).rank(method='first').to_numpy()
    nb = max(5, int(round(1.0 / frac)))
    bucket = np.clip(((rank - 1) / n * nb).astype(int), 0, nb - 1)
    ev_parts = []
    for b in range(nb):
        mem = np.where(bucket == b)[0]
        if len(mem) == 0:
            continue
        take = max(1, int(round(len(mem) * frac)))
        ev_parts.append(rng.choice(mem, min(take, len(mem)), replace=False))
    ev = np.unique(np.concatenate(ev_parts))
    tr = np.setdiff1d(np.arange(n), ev)
    return tr, ev


# ============================================================ 入选择阈值
def fdr_threshold(p, q=Q_TARGET):
    """由稳定性选择的有限样本界反解入选频率阈值 π_thr = (1 + q/p)/2。

    Meinshausen & Bühlmann (2010) 的界为 E[V] ≤ q_sel² / ((2·π_thr − 1)·p)，
    其中 **q_sel 是基础选择程序每次选出的变量数**（本题 TOP_MEASURE = 10），
    p 是候选变量数，V 是误选变量数。按 E[V] ≤ q 反解得 π_thr = (1 + q/p)/2。

    【口径警告】本函数传入的 q 是"允许的期望误选个数"，不是基础程序的选出数。
    取 q=1、p=231 得 π_thr = 0.5022，含义是"把期望误选数当 1 个来定的操作性阈值"，
    **不构成 0.05 水平上的 FDR 控制**。若严格按界中 q_sel 的原义取 10，
    同一式给出 π_thr = 0.7165，本脚本未采用。
    论文里只能说这是"入选频率阈值"，不能说"控制了错误发现率"。
    函数名沿用旧名以免下游引用断掉，语义以上述说明为准。

    下限 0.5（π<0.5 连多数稳定都算不上）；上限 0.95（200 次 bootstrap 的
    蒙特卡洛标准差约 0.015，阈值再高就分不清 0.95 与 1.00）。
    """
    return float(min(max((1.0 + q / p) / 2.0, 0.5), 0.95))


# ============================================================ OAV
def compute_oav(X, feats, thr):
    """按量纲分算 OAV：log10 列 10^x/θ，线性列 x/θ。"""
    rows = []
    for f in feats:
        if f not in thr:
            continue
        v = X[f].to_numpy(float)
        v = v[np.isfinite(v)]
        if len(v) == 0:
            continue
        conc = np.power(10.0, v) if f in LOG10_COLS else v
        oav = conc / thr[f]
        rows.append(dict(
            feat=f, threshold=thr[f],
            scale='log10' if f in LOG10_COLS else 'linear',
            is_physicochem=bool(f in PHYSICOCHEM),
            conc_median=float(np.median(conc)),
            oav_median=float(np.median(oav)),
            oav_p95=float(np.percentile(oav, 95)),
            oav_max=float(np.max(oav)),
        ))
    return pd.DataFrame(rows)


# ============================================================ Top-K 表
def _grade(feat, grp, oav_map):
    if feat in PHYSICOCHEM:
        return 'X 理化指标（机制代理，非香气化合物）'
    if feat in DERIVED:
        return 'X 派生量（由多个实测列加和算出，非独立化合物）'
    if grp.get(feat) in NON_AROMA_GROUPS:
        return 'X 内标（实验室外加参照物，非啤酒成分）'
    o = oav_map.get(feat)
    if o is None:
        return 'N 无阈值（无法判 OAV）'
    if o['oav_median'] >= OAV_TRUST:
        return 'A 统计显著且 OAV>1'
    if o['oav_median'] >= OAV_NEAR:
        return 'B 统计显著、OAV 接近阈值'
    return 'C 统计显著但 OAV 远低（需化学论证）'


def _build_topk(sens, feats, pi_df, cons_df, ntop_df, grp, oav_map,
                pool_mask, pi_thr, k=TOP_K):
    """按 π 降序、跨模型平均秩升序打破并列，从指定候选池取 Top-k。"""
    rows = []
    for c in sens:
        pi = pi_df.loc[c, feats].to_numpy(float)
        cr = cons_df.loc[c, feats].to_numpy(float)
        nt = ntop_df.loc[c, feats].to_numpy(float)
        cand = np.where(pool_mask)[0]
        if len(cand) == 0:
            continue
        order = cand[np.lexsort((cr[cand], -pi[cand]))][:k]
        for rank, j in enumerate(order, 1):
            f = feats[j]
            o = oav_map.get(f)
            rows.append(dict(
                sens=c, rank=rank, feat=f, origin_group=grp[f],
                pi=round(float(pi[j]), 4),
                pi_thr=round(pi_thr, 4),
                passes_pi=bool(pi[j] >= pi_thr),
                n_models_top10=int(nt[j]),
                cross_model_rank=round(float(cr[j]), 1),
                is_physicochem=bool(f in PHYSICOCHEM),
                is_internal_std=bool(grp[f] in NON_AROMA_GROUPS),
                oav_median=None if o is None else round(o['oav_median'], 4),
                oav_p95=None if o is None else round(o['oav_p95'], 4),
                threshold=None if o is None else o['threshold'],
                scale=None if o is None else o['scale'],
                grade=_grade(f, grp, oav_map),
            ))
    return pd.DataFrame(rows)


# ============================================================ 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true')
    args = ap.parse_args()
    n_boot = 30 if args.quick else N_BOOT
    suffix = '_quick' if args.quick else ''

    t0 = time.perf_counter()
    print('=' * 84)
    print('Q2 · 置换重要性(bootstrap OOB) + N=%d + FDR 反解 + OAV 裁判' % n_boot)
    print('=' * 84)

    X, Y, feats, sens, grp, thr = load_all()
    Xv = X.to_numpy(float)
    med = np.nanmedian(Xv, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    Xv = np.where(np.isfinite(Xv), Xv, med[None, :])

    p = len(feats)
    groups = [grp[f] for f in feats]
    print(f'样本 {Xv.shape[0]} | 特征 {p} | 靶 {len(sens)} | bootstrap {n_boot}')
    print('origin_paper 分组（覆盖 %d/%d）：' % (p, p))
    for g in sorted(set(groups)):
        print(f'   {g:28s} {groups.count(g):>3}')
    n_log = sum(1 for f in thr if f in LOG10_COLS)
    print(f'有阈值可算 OAV {len(thr)} 个（log10 {n_log} / 线性 {len(thr) - n_log}）；'
          f'无阈值 {p - len(thr)} 个无法判 OAV')

    pi_thr = fdr_threshold(p, Q_TARGET)
    print(f'\nFDR 反解：q={Q_TARGET}, p={p} → π_thr = {pi_thr:.4f}（不是惯用的 0.5）')

    # 香气候选池 = 既非理化指标、非内标、也非 5 个派生量
    # （派生量是若干实测列的加和，作为"关键化合物"报告属范畴错误）
    non_aroma_mask = np.array(
        [(f in PHYSICOCHEM) or (grp[f] in NON_AROMA_GROUPS) or (f in DERIVED)
         for f in feats])
    aroma_idx = np.where(~non_aroma_mask)[0]
    print(f'候选池划分：香气化合物 {len(aroma_idx)} / 非香气 {int(non_aroma_mask.sum())}'
          f'（理化 {sum(1 for f in feats if f in PHYSICOCHEM)} + '
          f'派生 {sum(1 for f in feats if f in DERIVED)} + '
          f'内标 {sum(1 for f in feats if grp[f] in NON_AROMA_GROUPS)}）')

    # ---- 逐靶 bootstrap + 跨模型评估 ----
    from joblib import Parallel, delayed
    print(f'\n逐靶 bootstrap（N={n_boot}，joblib {N_JOBS} 进程）...')
    pi_mat = np.zeros((len(sens), p))
    cons_mat = np.full((len(sens), p), np.nan)
    ntop_mat = np.zeros((len(sens), p))
    jac_rows = []
    pi_trace_rows = []
    trace_all = {}

    for k, c in enumerate(sens, 1):
        y = Y[c].to_numpy(float)
        ok = np.isfinite(y)
        yk, Xk = y[ok], Xv[ok]

        tops = Parallel(n_jobs=N_JOBS, backend='loky')(
            delayed(_boot_topk)((Xk, yk, SEED + 1000 * k + b, 'lgbm', 1))
            for b in range(n_boot)
        )
        cnt = np.zeros(p)
        for t in tops:
            cnt[t] += 1
        pi_mat[k - 1] = cnt / n_boot

        # π 的 bootstrap 收敛轨迹：第 b 次重采样后 π_b = cnt_b / b。
        # 只记"香气特征池内的均值/标准误"，50 个靶各一条，用于收敛曲线图。
        # 逐靶全 226 维的轨迹没必要存（200×226×50 太大），均值已足够证明平台。
        cnt_cum = np.zeros(p)
        tr_mean = np.empty(n_boot)
        tr_se = np.empty(n_boot)
        for b, t in enumerate(tops, 1):
            cnt_cum[t] += 1
            pi_b = cnt_cum / b
            tr_mean[b - 1] = float(pi_b[aroma_idx].mean())
            tr_se[b - 1] = float(np.sqrt(pi_b[aroma_idx] * (1 - pi_b[aroma_idx]) / b).mean())
        pi_trace_rows.append(dict(sens=c, n_boot=1, pi_mean=round(tr_mean[0], 4),
                                  pi_se=round(tr_se[0], 4)))
        for b in (5, 10, 20, 30, 50, 75, 100, 150, 200):
            if b <= n_boot:
                pi_trace_rows.append(dict(sens=c, n_boot=b,
                                          pi_mean=round(tr_mean[b - 1], 4),
                                          pi_se=round(tr_se[b - 1], 4)))
        trace_all.setdefault('mean', []).append(tr_mean)
        trace_all.setdefault('se', []).append(tr_se)

        # 跨模型：固定分层 70/30，三个模型族在同一评估集上排名（可比）
        tr, ev = _stratified_split(yk, SEED + k)
        if len(ev) < 20 or len(tr) < 20:
            tr, ev = np.arange(len(yk)), np.arange(len(yk))
        sets, ranks = {}, []
        for kind in FAMILIES:
            imp, top = permutation_importance(Xk[tr], yk[tr], Xk[ev], yk[ev],
                                              kind, SEED + k, 1)
            sets[kind] = set(top.tolist())
            ranks.append(pd.Series(-imp).rank(method='average').to_numpy())
            ntop_mat[k - 1] += np.isin(np.arange(p), top).astype(float)
        cons_mat[k - 1] = np.mean(ranks, axis=0)

        jac = {}
        for a in range(len(FAMILIES)):
            for b in range(a + 1, len(FAMILIES)):
                ka, kb = FAMILIES[a], FAMILIES[b]
                jac[(ka, kb)] = len(sets[ka] & sets[kb]) / max(1, len(sets[ka] | sets[kb]))
        jac_rows.append(dict(sens=c,
                             j_lgbm_et=round(jac[('lgbm', 'et')], 4),
                             j_lgbm_ridge=round(jac[('lgbm', 'ridge')], 4),
                             j_et_ridge=round(jac[('et', 'ridge')], 4),
                             j_mean=round(float(np.mean(list(jac.values()))), 4)))

        order = aroma_idx[np.argsort(-pi_mat[k - 1][aroma_idx])]
        top1 = order[0]
        print(f'  [{k:>2}/50] {c:18s} top1={feats[top1]:24s} π={pi_mat[k-1][top1]:.2f} '
              f'| 跨模型 {int(ntop_mat[k-1][top1])}/3 '
              f'| π≥{pi_thr:.2f}: {int((pi_mat[k-1][aroma_idx] >= pi_thr).sum()):>2} '
              f'| J={np.mean(list(jac.values())):.2f}')

    pi_df = pd.DataFrame(pi_mat, index=sens, columns=feats)
    pi_df.insert(0, 'sens', pi_df.index)
    pi_df.to_csv(os.path.join(RES, f'q2_feature_pi{suffix}.csv'),
                 index=False, encoding='utf-8-sig')

    cons_df = pd.DataFrame(cons_mat, index=sens, columns=feats)
    cons_df.insert(0, 'sens', cons_df.index)
    cons_df.to_csv(os.path.join(RES, f'q2_feature_consrank{suffix}.csv'),
                   index=False, encoding='utf-8-sig')
    ntop_df = pd.DataFrame(ntop_mat, index=sens, columns=feats)
    ntop_df.insert(0, 'sens', ntop_df.index)

    jac = pd.DataFrame(jac_rows)
    jac.to_csv(os.path.join(RES, f'q2_jaccard{suffix}.csv'), index=False, encoding='utf-8-sig')

    # 四分位数在求解脚本落盘（绘图脚本禁止重算，figure-contract）：
    # 50 个靶的跨方法 Jaccard 分布汇总，供箱线图的标注文字直接读。
    # 单行表（不是逐靶表）——箱线图的箱体由 ax.boxplot 从原始值画，
    # 这里的 q1/median/q3 只用于图内注释，两处必须一致。
    jac_stats = pd.DataFrame([dict(
        n_targets=int(len(jac)),
        q1=round(float(jac.j_mean.quantile(0.25)), 4),
        median=round(float(jac.j_mean.median()), 4),
        q3=round(float(jac.j_mean.quantile(0.75)), 4),
        iqr=round(float(jac.j_mean.quantile(0.75) - jac.j_mean.quantile(0.25)), 4),
        mean=round(float(jac.j_mean.mean()), 4),
        min=round(float(jac.j_mean.min()), 4),
        max=round(float(jac.j_mean.max()), 4),
        n_zero=int((jac.j_mean <= 1e-9).sum()),
    )])
    jac_stats.to_csv(os.path.join(RES, f'q2_jaccard_stats{suffix}.csv'),
                     index=False, encoding='utf-8-sig')

    # π 收敛轨迹：逐靶抽样点 + 全体平均曲线（后者是收敛曲线图的主线）
    if pi_trace_rows:
        pd.DataFrame(pi_trace_rows).to_csv(
            os.path.join(RES, f'q2_pi_trace{suffix}.csv'), index=False,
            encoding='utf-8-sig', float_format='%.4f')
    if trace_all.get('mean'):
        M = np.vstack(trace_all['mean'])
        S = np.vstack(trace_all['se'])
        pd.DataFrame({
            'n_boot': np.arange(1, M.shape[1] + 1),
            'pi_mean_across_sens': M.mean(axis=0),
            'pi_se_across_sens': S.mean(axis=0),
            'pi_mean_p95': np.percentile(M, 95, axis=0),
            'pi_mean_p5': np.percentile(M, 5, axis=0),
        }).to_csv(os.path.join(RES, f'q2_pi_convergence{suffix}.csv'), index=False,
                  encoding='utf-8-sig', float_format='%.4f')

    # ---- OAV ----
    oav = compute_oav(X, feats, thr)
    oav.to_csv(os.path.join(RES, f'q2_oav{suffix}.csv'), index=False, encoding='utf-8-sig')
    oav_map = oav.set_index('feat').to_dict('index')

    # 棒棒糖图的显示版：35 个香气化合物全塞进 6.2 英寸会把标签压成 5pt，
    # 所以按 oav_p95 降序取 Top-20 + 其余聚合成一行。聚合行的分位数同样在
    # 求解脚本算好落盘（figure-contract：绘图脚本禁止重算论文数值）。
    oav_aroma = oav[~oav.is_physicochem].sort_values('oav_p95', ascending=False)
    top_n = oav_aroma.head(20).copy()
    top_n['kind'] = 'single'
    rest = oav_aroma.iloc[20:]
    if len(rest):
        agg = dict(
            feat=f'其余 {len(rest)} 个（中位）', threshold=float('nan'), scale='-',
            is_physicochem=False, conc_median=float('nan'),
            oav_median=round(float(rest.oav_median.median()), 6),
            oav_p95=round(float(rest.oav_p95.median()), 6),
            oav_max=round(float(rest.oav_max.median()), 6), kind='rest',
        )
        top_n = pd.concat([top_n, pd.DataFrame([agg])], ignore_index=True)
    # 三档配色由求解脚本判定（≥1 / 0.5–1 / <0.5），图里只按档位上色
    top_n['band'] = np.where(top_n.oav_median >= 1.0, 'ge1',
                             np.where(top_n.oav_median >= 0.5, 'mid', 'low'))
    top_n[['feat', 'oav_median', 'oav_p95', 'oav_max', 'band', 'kind']].to_csv(
        os.path.join(RES, f'q2_oav_display{suffix}.csv'), index=False, encoding='utf-8-sig')

    # ---- 两张 Top-3 表 ----
    top3 = _build_topk(sens, feats, pi_df, cons_df, ntop_df, grp, oav_map,
                       ~non_aroma_mask, pi_thr)
    top3.to_csv(os.path.join(RES, f'q2_top3{suffix}.csv'), index=False, encoding='utf-8-sig')
    top3_phys = _build_topk(sens, feats, pi_df, cons_df, ntop_df, grp, oav_map,
                            non_aroma_mask, pi_thr)
    top3_phys.to_csv(os.path.join(RES, f'q2_top3_physicochem{suffix}.csv'),
                     index=False, encoding='utf-8-sig')

    # ---- FDR 反解表 ----
    fdr = pd.DataFrame([
        dict(q=q, pi_thr=round(fdr_threshold(p, q), 4),
             n_feat_pass=int((pi_df[feats].max(axis=0).to_numpy()
                              >= fdr_threshold(p, q)).sum()))
        for q in (0.1, 0.5, 1.0, 2.0, 5.0)
    ])
    fdr.to_csv(os.path.join(RES, f'q2_fdr{suffix}.csv'), index=False, encoding='utf-8-sig')

    # ---- 收敛性：π 的 bootstrap 标准误（200 次时约 0.03 上限，说明 200 够用）----
    se = np.sqrt(pi_mat * (1 - pi_mat) / n_boot)
    conv = dict(n_boot=n_boot,
                pi_boot_se_mean=round(float(se.mean()), 4),
                pi_boot_se_p95=round(float(np.percentile(se, 95)), 4))

    # ---- 汇总 ----
    print('\n' + '-' * 84)
    print('香气化合物 Top-3 证据分级：')
    print(top3.grade.value_counts().to_string())
    print('\n理化代理 Top-3 证据分级：')
    print(top3_phys.grade.value_counts().to_string())
    print('\nOAV 最高的 8 个香气化合物（量纲已分算）：')
    aroma_oav = oav[~oav.is_physicochem].sort_values('oav_median', ascending=False)
    print(aroma_oav.head(8)[['feat', 'threshold', 'scale', 'oav_median', 'oav_p95']]
          .to_string(index=False))

    n_phys = int((top3.is_physicochem | top3.is_internal_std).sum())
    n_nothr = int((top3.grade.str.startswith('N')).sum())
    n_mm = int((top3.n_models_top10 >= 2).sum())
    print(f'\n香气 Top-3 中非香气成分 {n_phys} 条 / 150（理化/内标，必须为 0）')
    print(f'无阈值 {n_nothr} 条 / 150；跨模型支持 ≥2/3 的 {n_mm} 条 / 150')
    print(f'跨方法 Top-10 Jaccard：中位 {jac.j_mean.median():.3f}，'
          f'最差 {jac.j_mean.min():.3f}，lgbm-ridge 中位 {jac.j_lgbm_ridge.median():.3f}')
    print(f'π 的 bootstrap 标准误：均值 {conv["pi_boot_se_mean"]}，'
          f'p95 {conv["pi_boot_se_p95"]}')

    dur = time.perf_counter() - t0
    summary = dict(
        n_samples=int(Xv.shape[0]), n_features=p, n_targets=len(sens),
        n_boot=n_boot, top_k=TOP_K, top_measure=TOP_MEASURE, q_target=Q_TARGET,
        pi_thr=round(pi_thr, 4),
        n_feat_ever_over_thr=int((pi_df[feats].max(axis=0).to_numpy() >= pi_thr).sum()),
        aroma_grade_counts=top3.grade.value_counts().to_dict(),
        physicochem_grade_counts=top3_phys.grade.value_counts().to_dict(),
        n_non_aroma_in_aroma_top3=n_phys,
        n_no_threshold_in_aroma_top3=n_nothr,
        n_multimodel_support2_in_aroma_top3=n_mm,
        median_cross_method_jaccard=round(float(jac.j_mean.median()), 4),
        worst_cross_method_jaccard=round(float(jac.j_mean.min()), 4),
        median_lgbm_ridge_jaccard=round(float(jac.j_lgbm_ridge.median()), 4),
        n_oav_computable=int(len(oav)),
        n_oav_computable_aroma=int((~oav.is_physicochem).sum()),
        n_log10_thr=n_log, n_linear_thr=len(thr) - n_log,
        pi_convergence=conv,
        eval_protocol='pi: bootstrap OOB; cross-model: stratified 70/30 shared eval set',
        duration_s=round(dur, 1), quick=bool(args.quick),
    )
    with open(os.path.join(RES, f'q2_run_log{suffix}.json'), 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f'\n耗时 {dur / 60:.1f} min → results/q2_*{suffix}.csv')
    print('=' * 84)
    return 0


if __name__ == '__main__':
    sys.exit(main())
