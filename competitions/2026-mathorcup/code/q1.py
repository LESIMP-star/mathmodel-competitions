# -*- coding: utf-8 -*-
"""q1.py — 问题一：50 维感官强度的代理预测（n=250, p=231）

本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：Hermes Agent（Nous Research），底层模型 deepseek-v4-flash，
# 开发机构：Nous Research（工具）/ 深度求索 DeepSeek（模型），使用日期：2026-10-26

输入
  附件/1.csv   250 × 231 化学（226 实测 + 5 派生），37 列已在 log10 域
  附件/4.csv   250 × 50 感官靶（仅中心化的连续强度，非 0-6 原始分）
  附件/7.csv   250 × 186 论坛评论 z 分数 → 独立外部效度检验集
  附件/8.xlsx  Sensory thresholds（origin_paper 分组）、Calibrated chemical dataset

口径（全部经 verify_facts.py 与本次实算复算）
  - 特征 = 226 实测列；剔除 5 个派生列 kcalperc / esters_sum / aroma_hops_sum /
    acids_sum / sulfur_sum（与母列强共线，且 esters_sum 等会吃掉母列重要性）
  - 37 个 log10 列保持 log10 尺度（1.csv 已是 log10，不再取 10^）
  - LOD 地板值 -1.817819 是"低于检出限"的占位，不是 NA → 保留原值，不替换
  - 真 NA（73 格 / 9 列）→ 按训练折中位数插补（不用全表中位数，避免泄漏）
  - 靶全部按**连续回归**处理；不拆 24 维二分类（实测推翻总纲 §2.1）
  - 地板质量 > 30% 的靶（9 个）叠加 hurdle 两部模型

模型与评估
  逐维 **嵌套 CV**：外层 5 折评估、内层 5 折选模型 → 真实泛化误差，无选择偏差
  候选：Ridge / ElasticNet / LightGBM / ExtraTrees
  指标：R²、MAE、Spearman + R² 的 bootstrap 95% 区间（1000 次）
  外部效度：4.csv↔7.csv 同名概念的 14 组对齐，检验预测与论坛评论是否同向

输出
  results/q1_metrics.csv        逐维 50 行
  results/q1_external.csv       外部效度 14 行
  results/q1_predictions.csv    250 × 50 的 out-of-fold 预测（供 Q3 代理复用）
  results/q1_run_log.json       运行参数与实际耗时

运行
  python q1.py            # 完整：洋外 5 × 内 5
  python q1.py --quick    # 快速：外层 3 × 内层 3（只用于冒烟，结果不进论文）
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

# Windows 控制台默认 GBK，R²/ρ/≤ 等字符会抛 UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, '附件')
RES = os.path.join(ROOT, 'results')
os.makedirs(RES, exist_ok=True)

SEED = 2026
DERIVED = ['kcalperc', 'esters_sum', 'aroma_hops_sum', 'acids_sum', 'sulfur_sum']
# 主口径用附件1 全部 231 个化学列。依据：附件2 提供的相关矩阵是 231×231 的
# 对称矩阵，且行列中明确含 Caloric value、Total ester compounds、Total hop
# aroma compounds、Total acids、Total sulfur compounds 这 5 个派生量——说明
# 出题方把 231 列当作完整的化合物集合。文献（Schreurs 2024）亦用 p=231。
# 剔除 5 列（226 维）的版本不再作为主口径，仅由 q1_ablation_231.py 做对照。
USE_ALL_COLS = True
LOD_FLOOR = -1.817819
FLOOR_WIN = 0.15          # 地板窗宽（与 plan 的地板质量定义一致）
HURDLE_THR = 0.30         # 地板质量 > 30% 才上 hurdle
N_BOOT = 1000

# 4.csv ↔ 7.csv 概念对齐（同名 + 手工语义对齐，见 plan §1.2）
EXTERNAL_PAIRS = {
    'alcohol': 'aroma_alcohol',
    'A_malt_cara': 'aroma_caramel',
    'A_malt_all': 'aroma_malt',
    'lactic': 'aroma_acidic',
    'acetic': 'aroma_acetic',
    'A_hops_citrus': 'aroma_citrus',
    'sweetness': 'aroma_candy',
    'bitternes': 'aroma_bitter',
    'clove': 'aroma_clove',
    'A_esters_isoaa': 'aroma_banana',
    'dms': 'aroma_corn',
    'diacetyl': 'aroma_diacetyl',
    'aftertaste': 'aroma_aftertaste',
    'A_esters_fruity': 'aroma_fruity',
}


# ============================================================ 数据加载
def load_data():
    c1 = pd.read_csv(os.path.join(DATA, '1.csv'))
    c4 = pd.read_csv(os.path.join(DATA, '4.csv'))
    c7 = pd.read_csv(os.path.join(DATA, '7.csv'))

    chem_all = list(c1.columns[3:])
    feats = chem_all if USE_ALL_COLS else [c for c in chem_all if c not in DERIVED]
    sens = list(c4.columns[3:])
    n_expect = 231 if USE_ALL_COLS else 226
    assert len(feats) == n_expect, f'特征数应为 {n_expect}，实际 {len(feats)}'
    assert len(sens) == 50, f'靶数应为 50，实际 {len(sens)}'

    # beer 对齐（beer_id 只有 96/250 唯一，禁止用于对齐）
    assert c1['beer'].is_unique and c4['beer'].is_unique and c7['beer'].is_unique
    X = c1.set_index('beer')[feats].apply(pd.to_numeric, errors='coerce')
    Y = c4.set_index('beer')[sens].apply(pd.to_numeric, errors='coerce')
    Z = c7.set_index('beer')

    idx = X.index.intersection(Y.index).intersection(Z.index)
    X, Y, Z = X.loc[idx], Y.loc[idx], Z.loc[idx]
    assert len(idx) == 250, f'三表交集应为 250，实际 {len(idx)}'
    return X, Y, Z, feats, sens


def floor_stats(Y):
    """逐靶地板质量：与列最小值相距 ≤0.15 的样本占比。"""
    out = {}
    for c in Y.columns:
        v = Y[c].to_numpy(float)
        out[c] = float((v - np.nanmin(v) <= FLOOR_WIN).mean())
    return out


# ============================================================ 模型
def make_models():
    from sklearn.linear_model import Ridge, ElasticNet
    from sklearn.ensemble import ExtraTreesRegressor
    from lightgbm import LGBMRegressor
    return {
        'ridge': Ridge(alpha=10.0, random_state=SEED),
        'enet': ElasticNet(alpha=0.05, l1_ratio=0.5, max_iter=5000, random_state=SEED),
        'lgbm': LGBMRegressor(n_estimators=150, num_leaves=7, min_child_samples=8,
                              learning_rate=0.06, subsample=0.8, colsample_bytree=0.6,
                              reg_lambda=1.0, random_state=SEED, n_jobs=4, verbose=-1),
        'et': ExtraTreesRegressor(n_estimators=200, max_features='sqrt',
                                  min_samples_leaf=3, random_state=SEED, n_jobs=4),
    }


def make_models_hurdle():
    """hurdle 两部模型：按模型名配对 (π 分类器, μ 回归器)。

    注意：name 必须作用在**回归头**上，否则四个候选给出完全相同的预测，
    内层选模型退化为"永远选第一个"，与"多模型对比择优"的说法不符。
    """
    from sklearn.linear_model import LogisticRegression, Ridge, ElasticNet
    from sklearn.ensemble import ExtraTreesRegressor
    from lightgbm import LGBMClassifier, LGBMRegressor
    logit = LogisticRegression(C=0.1, max_iter=3000, random_state=SEED)
    lgbc = LGBMClassifier(n_estimators=120, num_leaves=7, min_child_samples=8,
                          learning_rate=0.06, subsample=0.8, colsample_bytree=0.6,
                          reg_lambda=1.0, random_state=SEED, n_jobs=4, verbose=-1)
    return {
        'ridge': (logit, Ridge(alpha=10.0, random_state=SEED)),
        'enet': (logit, ElasticNet(alpha=0.05, l1_ratio=0.5, max_iter=5000, random_state=SEED)),
        'lgbm': (lgbc, LGBMRegressor(n_estimators=150, num_leaves=7, min_child_samples=8,
                                     learning_rate=0.06, subsample=0.8, colsample_bytree=0.6,
                                     reg_lambda=1.0, random_state=SEED, n_jobs=4, verbose=-1)),
        'et': (logit, ExtraTreesRegressor(n_estimators=200, max_features='sqrt',
                                          min_samples_leaf=3, random_state=SEED, n_jobs=4)),
    }


def _fit_predict_plain(name, model, Xtr, ytr, Xte):
    m = model.__class__(**model.get_params())
    m.fit(Xtr, ytr)
    # 预测裁剪回观测值域：连续靶有物理上下界，树模型外推会给出界外值
    return np.clip(m.predict(Xte), float(np.min(ytr)), float(np.max(ytr)))


def _fit_predict_hurdle(models, name, Xtr, ytr, Xte, thr_hi):
    """两部模型：π = P(y > 地板窗)，μ = E[y | y > 地板窗]；ŷ = (1-π)·ȳ_floor + π·μ̂。"""
    clf, reg = models[name]
    z = (ytr > thr_hi).astype(int)
    if z.sum() < 5 or (1 - z).sum() < 5:      # 某折退化 → 退回单部回归
        return _fit_predict_plain(name, reg, Xtr, ytr, Xte)
    c = clf.__class__(**clf.get_params()).fit(Xtr, z)
    pi = c.predict_proba(Xte)[:, 1]
    r = reg.__class__(**reg.get_params()).fit(Xtr[z == 1], ytr[z == 1])
    mu = r.predict(Xte)
    y_floor = float(np.mean(ytr[z == 0])) if (z == 0).any() else float(np.min(ytr))
    out = (1.0 - pi) * y_floor + pi * mu
    return np.clip(out, float(np.min(ytr)), float(np.max(ytr)))


def _score(y, p):
    from scipy.stats import spearmanr
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    ss_res = float(np.sum((y - p) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    mae = float(np.mean(np.abs(y - p)))
    rho = float(spearmanr(y, p).statistic) if len(np.unique(p)) > 1 else np.nan
    return r2, mae, rho


def _boot_ci(y, p, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(y)
    vals = np.empty(n_boot)
    for b in range(n_boot):
        i = rng.integers(0, n, n)
        vals[b] = _score(y[i], p[i])[0]
    vals = vals[np.isfinite(vals)]
    if len(vals) < 10:
        return np.nan, np.nan
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def _prep(tr_idx, te_idx, Xv, needs_imp):
    """按训练折统计量插补 + 标准化（无泄漏）。"""
    Xtr = Xv[tr_idx]
    Xte = Xv[te_idx]
    med = Xtr['__med']
    sd = Xtr['__sd']
    A = (Xtr['__X'] - med) / sd
    B = (Xte['__X'] - med) / sd
    return A, B


# ============================================================ 单靶嵌套 CV
def _fit_prep(Mtr):
    """由**训练块**估计预处理参数：中位数填补 + 标准化。

    注意 sd 必须在“用中位数填补之后”的矩阵上算——先 nan_to_num(0) 再算 sd
    会把缺失处当成真值 0，与随后实际使用的填补值不一致。
    """
    med = np.nanmedian(Mtr, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    filled = np.where(np.isfinite(Mtr), Mtr, med[None, :])
    sd = filled.std(axis=0)
    sd = np.where(sd > 1e-12, sd, 1.0)
    return med, sd


def _apply_prep(M, med, sd):
    """用给定的 (med, sd) 变换，不重新估计。"""
    M = np.where(np.isfinite(M), M, med[None, :])
    return (M - med[None, :]) / sd[None, :]


def nested_cv_one(y, Xraw, hurdle, outer=5, inner=5, seed=SEED):
    """嵌套交叉验证：外层评估、内层选型，预处理参数逐层独立估计。

    **预处理的位置是关键**：内层的缺失填补与标准化参数只能由该次内层训练折
    估计；若用整个外层训练集先算好再切内层，内层验证折的特征信息就参与了
    参数估计（内层泄漏），选型结果不再干净。外层测试折始终只用外层训练折的
    参数，这一点无论哪种写法都成立。
    """
    from sklearn.model_selection import KFold
    n = len(y)
    kf_out = KFold(n_splits=outer, shuffle=True, random_state=seed)
    oof = np.full(n, np.nan)
    chosen = []
    names = list(make_models().keys())
    for fold, (tr, te) in enumerate(kf_out.split(Xraw)):
        Xtr_raw, Xte_raw = Xraw[tr], Xraw[te]
        ytr, yte = y[tr], y[te]

        # ── 内层选模型：每次划分只用内层训练折估计预处理参数
        kf_in = KFold(n_splits=inner, shuffle=True, random_state=seed + fold)
        best_name, best_r2 = None, -np.inf
        for name in names:
            preds = np.full(len(tr), np.nan)
            for itr, ite in kf_in.split(Xtr_raw):
                med_i, sd_i = _fit_prep(Xtr_raw[itr])
                A_i = _apply_prep(Xtr_raw[itr], med_i, sd_i)
                B_i = _apply_prep(Xtr_raw[ite], med_i, sd_i)
                models = make_models_hurdle() if hurdle else make_models()
                if hurdle:
                    thr_hi = float(np.min(ytr[itr]) + FLOOR_WIN)
                    preds[ite] = _fit_predict_hurdle(models, name, A_i, ytr[itr], B_i, thr_hi)
                else:
                    preds[ite] = _fit_predict_plain(name, models[name], A_i, ytr[itr], B_i)
            r2 = _score(ytr, preds)[0]
            if np.isfinite(r2) and r2 > best_r2:
                best_r2, best_name = r2, name
        best_name = best_name or 'ridge'
        chosen.append(best_name)

        # ── 外层：选完模型后，在整个外层训练折上重估一次预处理再预测测试折
        med, sd = _fit_prep(Xtr_raw)
        A = _apply_prep(Xtr_raw, med, sd)
        B = _apply_prep(Xte_raw, med, sd)
        models = make_models_hurdle() if hurdle else make_models()
        if hurdle:
            thr_hi = float(np.min(ytr) + FLOOR_WIN)
            oof[te] = _fit_predict_hurdle(models, best_name, A, ytr, B, thr_hi)
        else:
            oof[te] = _fit_predict_plain(best_name, models[best_name], A, ytr, B)
    return oof, chosen


# ============================================================ 外部效度
def external_validity(Xraw, Y, Z, feats):
    rows = []
    from sklearn.linear_model import Ridge
    from scipy.stats import spearmanr
    med = np.nanmedian(Xraw, axis=0); med = np.where(np.isfinite(med), med, 0.0)
    sd = np.nanstd(np.nan_to_num(Xraw, nan=0.0), axis=0); sd = np.where(sd > 1e-12, sd, 1.0)
    A = (np.where(np.isfinite(Xraw), Xraw, med[None, :]) - med) / sd
    for s4, s7 in EXTERNAL_PAIRS.items():
        if s4 not in Y.columns or s7 not in Z.columns:
            rows.append(dict(sens_4csv=s4, sens_7csv=s7, status='MISSING'))
            continue
        y = Y[s4].to_numpy(float)
        z = pd.to_numeric(Z[s7], errors='coerce').to_numpy(float)
        ok = np.isfinite(y) & np.isfinite(z)
        if ok.sum() < 30:
            rows.append(dict(sens_4csv=s4, sens_7csv=s7, status='FEW', n=int(ok.sum())))
            continue
        m = Ridge(alpha=10.0).fit(A[ok], y[ok])
        pred = m.predict(A[ok])
        # 逐行的可迁移性指标：预测与论坛评论 z 分数的决定系数与标准化平均绝对误差。
        # 绘图脚本禁止重算数值（figure-contract），指标框要用这两个数就必须在这里落盘。
        r2_pred = float(1.0 - np.sum((z[ok] - pred) ** 2) /
                        np.sum((z[ok] - z[ok].mean()) ** 2))
        zp = (pred - pred.mean()) / (pred.std(ddof=0) or 1.0)
        zz = (z[ok] - z[ok].mean()) / (z[ok].std(ddof=0) or 1.0)
        rows.append(dict(
            sens_4csv=s4, sens_7csv=s7, status='OK', n=int(ok.sum()),
            rho_label7_vs_4=round(float(spearmanr(y[ok], z[ok]).statistic), 4),
            rho_pred_vs_7=round(float(spearmanr(pred, z[ok]).statistic), 4),
            rho_pred_vs_4=round(float(spearmanr(pred, y[ok]).statistic), 4),
            r2_pred_vs_7=round(r2_pred, 4),
            mae_z_pred_vs_7=round(float(np.mean(np.abs(zp - zz))), 4),
        ))
    return pd.DataFrame(rows)


# ============================================================ 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true', help='外层3×内层3，仅冒烟')
    args = ap.parse_args()
    outer = inner = 3 if args.quick else 5
    suffix = '_quick' if args.quick else ''

    t0 = time.perf_counter()
    print('=' * 78)
    print('Q1 · 50 维感官强度代理预测（嵌套 CV）')
    print('=' * 78)

    X, Y, Z, feats, sens = load_data()
    print(f'样本 {X.shape[0]} | 特征 {X.shape[1]} | 靶 {Y.shape[1]}')
    print(f'真 NA 格数 {int(X.isna().sum().sum())} | LOD 地板值出现 {int((X == LOD_FLOOR).sum().sum())}')
    print(f'嵌套 CV：外层 {outer} 折 / 内层 {inner} 折 | bootstrap {N_BOOT} 次')

    fs = floor_stats(Y)
    n_hurdle = sum(1 for v in fs.values() if v > HURDLE_THR)
    print(f'地板质量 > {HURDLE_THR:.0%} 的靶：{n_hurdle} 个 → 走 hurdle 两部模型')
    print()

    Xraw = X.to_numpy(float)
    preds = {}
    rows = []
    for k, c in enumerate(sens, 1):
        y = Y[c].to_numpy(float)
        ok = np.isfinite(y)
        pub = np.full(len(y), np.nan)
        hurdle = fs[c] > HURDLE_THR
        oof, chosen = nested_cv_one(y[ok], Xraw[ok], hurdle, outer, inner)
        pub[ok] = oof
        preds[c] = pub
        r2, mae, rho = _score(y[ok], oof)
        lo, hi = _boot_ci(y[ok], oof)
        from collections import Counter
        pick = Counter(chosen).most_common(1)[0][0]
        rows.append(dict(
            sens=c, n=int(ok.sum()), hurdle=hurdle,
            floor_mass=round(fs[c], 4), model_pick=pick,
            R2=round(r2, 4), R2_lo=round(lo, 4), R2_hi=round(hi, 4),
            MAE=round(mae, 4), spearman=round(rho, 4),
            y_sd=round(float(np.nanstd(y)), 4),
        ))
        flag = '★' if r2 > 0.15 else ('~' if r2 > 0.03 else ' ')
        print(f'  [{k:>2}/50] {c:18s} {"H" if hurdle else " "} {pick:6s} '
              f'R²={r2:+.3f} [{lo:+.3f},{hi:+.3f}] MAE={mae:.3f} ρ={rho:+.3f} {flag}')

    met = pd.DataFrame(rows).sort_values('R2', ascending=False)
    met.to_csv(os.path.join(RES, f'q1_metrics{suffix}.csv'), index=False, encoding='utf-8-sig')

    pred_df = pd.DataFrame(preds, index=X.index)
    pred_df.insert(0, 'beer', pred_df.index)
    pred_df.to_csv(os.path.join(RES, f'q1_predictions{suffix}.csv'), index=False, encoding='utf-8-sig')

    print()
    print('-' * 78)
    print('外部效度：4.csv 标签 vs 7.csv 论坛评论（同名概念中位 ρ={:.3f}）'.format(
        met.shape[0] and float(np.median([abs(v) for v in [0]]) or 0)))
    ext = external_validity(Xraw, Y, Z, feats)
    ext.to_csv(os.path.join(RES, f'q1_external{suffix}.csv'), index=False, encoding='utf-8-sig')
    ok_ext = ext[ext.status == 'OK']
    if len(ok_ext):
        print(ok_ext[['sens_4csv', 'sens_7csv', 'rho_label7_vs_4', 'rho_pred_vs_7']].to_string(index=False))
        print(f'\n预测↔7.csv 中位 ρ = {ok_ext.rho_pred_vs_7.median():.3f} '
              f'| 标签↔7.csv 中位 ρ = {ok_ext.rho_label7_vs_4.median():.3f}')

    dur = time.perf_counter() - t0
    summary = dict(
        n_samples=int(X.shape[0]), n_features=int(X.shape[1]), n_targets=int(Y.shape[1]),
        outer=outer, inner=inner, n_boot=N_BOOT, seed=SEED,
        hurdle_thr=HURDLE_THR, n_hurdle_targets=int(n_hurdle),
        median_R2=round(float(met.R2.median()), 4),
        mean_R2=round(float(met.R2.mean()), 4),
        n_R2_positive=int((met.R2 > 0).sum()),
        best_target=met.iloc[0]['sens'], best_R2=float(met.iloc[0].R2),
        worst_target=met.iloc[-1]['sens'], worst_R2=float(met.iloc[-1].R2),
        median_boot_width=round(float((met.R2_hi - met.R2_lo).median()), 4),
        duration_s=round(dur, 1), quick=bool(args.quick),
    )
    # 地板质量 ↔ R² 的关系：论文里要点名"−0.38，所以 hurdle 的依据是分布形状"，
    # 这个数必须在求解脚本落盘，绘图脚本的回归线只能照抄，不许自己再算。
    xf = met.floor_mass.to_numpy(float)
    yf = met.R2.to_numpy(float)
    slope, intercept = np.polyfit(xf, yf, 1)
    summary['floor_vs_R2'] = dict(
        spearman=round(float(met.floor_mass.corr(met.R2, method='spearman')), 4),
        pearson=round(float(met.floor_mass.corr(met.R2)), 4),
        slope=round(float(slope), 4), intercept=round(float(intercept), 4),
        hurdle_n=int(met.hurdle.sum()),
        hurdle_mean_R2=round(float(met.loc[met.hurdle, 'R2'].mean()), 4),
        plain_mean_R2=round(float(met.loc[~met.hurdle, 'R2'].mean()), 4),
    )
    # OLS 拟合线 + 95% 置信带：逐格点落盘，绘图脚本只连线填带（figure-contract：
    # 绘图脚本禁止重算论文数值）。用经典 OLS 标准误，n=50 下 t≈2.011。
    n_f = len(xf)
    resid = yf - (slope * xf + intercept)
    s_err = float(np.sqrt(np.sum(resid ** 2) / max(n_f - 2, 1)))
    xbar = float(xf.mean())
    sxx = float(np.sum((xf - xbar) ** 2))
    t_crit = 2.0106                     # scipy.stats.t.ppf(0.975, 48)
    xg = np.linspace(float(xf.min()), float(xf.max()), 120)
    width = t_crit * s_err * np.sqrt(1.0 / n_f + (xg - xbar) ** 2 / sxx)
    pd.DataFrame(dict(
        floor_mass=xg.round(6),
        fit=(slope * xg + intercept).round(6),
        band_lo=(slope * xg + intercept - width).round(6),
        band_hi=(slope * xg + intercept + width).round(6),
    )).to_csv(os.path.join(RES, f'q1_floor_fit{suffix}.csv'), index=False, encoding='utf-8-sig')

    if len(ok_ext):
        summary['ext_median_rho_pred_vs_7'] = round(float(ok_ext.rho_pred_vs_7.median()), 4)
        summary['ext_median_rho_label_vs_7'] = round(float(ok_ext.rho_label7_vs_4.median()), 4)
        summary['ext_median_r2_pred_vs_7'] = round(float(ok_ext.r2_pred_vs_7.median()), 4)
        summary['ext_median_mae_z_pred_vs_7'] = round(float(ok_ext.mae_z_pred_vs_7.median()), 4)

    # 森林图的"16 行显示版"：50 维塞进 5.4 英寸会挤成一团，所以图里只放
    # Top-10 + 其余 35 维的中位聚合行 + Bottom-5。"其余 35 维的中位数"是一个
    # 会印进图里的数，必须在求解脚本算好落盘（figure-contract），绘图脚本只读。
    top10 = met.head(10)
    bot5 = met.tail(5).iloc[::-1]
    rest = met.iloc[10:-5]
    forest_rows = [dict(label=r.sens, estimate=float(r.R2), ci_low=float(r.R2_lo),
                        ci_high=float(r.R2_hi), kind='top')
                   for _, r in top10.iterrows()]
    if len(rest):
        forest_rows.append(dict(
            label=f'其余 {len(rest)} 维（中位）',
            estimate=round(float(rest.R2.median()), 4),
            ci_low=round(float(rest.R2_lo.median()), 4),
            ci_high=round(float(rest.R2_hi.median()), 4),
            kind='rest'))
    forest_rows += [dict(label=r.sens, estimate=float(r.R2), ci_low=float(r.R2_lo),
                         ci_high=float(r.R2_hi), kind='bottom')
                    for _, r in bot5.iterrows()]
    pd.DataFrame(forest_rows).to_csv(
        os.path.join(RES, f'q1_forest_rows{suffix}.csv'), index=False, encoding='utf-8-sig')
    with open(os.path.join(RES, f'q1_run_log{suffix}.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print()
    print('=' * 78)
    print(f'中位 R² = {summary["median_R2"]:+.4f} | 平均 R² = {summary["mean_R2"]:+.4f} | '
          f'R²>0 的靶 {summary["n_R2_positive"]}/50')
    print(f'最强维 {summary["best_target"]} R²={summary["best_R2"]:+.4f} | '
          f'最弱维 {summary["worst_target"]} R²={summary["worst_R2"]:+.4f}')
    print(f'耗时 {dur:.1f}s → results/q1_*{suffix}.csv')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
