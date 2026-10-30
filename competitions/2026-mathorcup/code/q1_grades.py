# -*- coding: utf-8 -*-
"""q1_grades.py — 把问题一的连续预测转成赛题要求的 0–6 分级评分

为什么需要这个脚本
  题面原文要求给出 Aroma 与 Flavour 两套共 50 个感官维度的 0–6 分制分级评分。
  q1.py 只落盘连续折外预测，没有输出 0–6 等级。而附件4 只给中心化连续值、
  实测不可精确反解，所以只能做近似等级映射并如实声明局限。

代码来源：**直接复用队友 q1_model.py 的三个函数**（第 43-71 行），原样照搬：
  · PRIORS        三套 0–6 目标等级分布（uniform / zeroinfl / mildzero）
  · quantile_to_grade(z, prior)  保序分位映射，按目标分布切档
  · qwk(y_true, y_pred, k=7)     二次加权 kappa
只改一处：把"读队友自己的预测文件"换成读本工作区 results/q1_predictions.csv。

为什么用先验映射而不是等频映射（这是与被替换版本的关键差别）
  等频映射强制每维等级的 7 个档各占 1/7，等于断言"面板在每个维度上都用满了
  量程且分布均匀"。但这个断言在数据里没有依据：实测附件4 每列最高频取值只占
  1.8%（中位）、等于列最小值的样本仅 0.88%，说明标签已被中心化并加噪，既看不
  出整数分的重复台阶，也看不出零膨胀。既然两个方向都无法从数据验证，就应当
  取有文献支撑的那个：感官评价中大量化合物低于阈值记 0 分，零膨胀是啤酒风味
  面板的已知特征。故本文以 zeroinfl 先验为主口径，uniform 与 mildzero 作敏感性，
  等频映射只作为对照，用来说明"换映射后 QWK 变化多少"。

评估口径（必须如实声明）
  没有 0–6 真值，故 QWK / 准确率都是**同一映射内的往返一致性**，衡量预测分与
  标签分落在同一档的比例，不是对面板真值的绝对精度。

输入（只读）
  results/q1_predictions.csv   250 × 50 折外预测
  附件/4.csv                   250 × 50 感官标签
输出
  results/q1_grades.csv        250 × 50 的预测等级（0–6 整数，主口径 zeroinfl）
  results/q1_grade_metrics.csv 50 维 × 三种先验的等级层指标
  results/q1_grade_summary.json 汇总
  results/q1_grade_hist.csv    等级分布对照

用法：python code/q1_grades.py
本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：Hermes Agent（Nous Research），底层模型 deepseek-v4-flash，
# 开发机构：Nous Research（工具）/ 深度求索 DeepSeek（模型），使用日期：2026-10-26
"""
from __future__ import annotations

import os
import sys
import json

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'results')
DATA = os.path.join(ROOT, '附件')
N_GRADE = 7          # 0..6
MAIN_PRIOR = 'zeroinfl'


# ═════════════════════════════════════════════════════════════
# 以下三个函数照抄队友 q1_model.py:43-71，逐行未改
# ═════════════════════════════════════════════════════════════
PRIORS = {
    'uniform':    np.array([1/7]*7),
    'zeroinfl':   np.array([0.50, 0.18, 0.12, 0.09, 0.06, 0.035, 0.015]),
    'mildzero':   np.array([0.35, 0.20, 0.16, 0.13, 0.09, 0.05, 0.02]),
}


def quantile_to_grade(z, prior):
    """保序分位映射：把列内经验分位按目标分布切成 0-6"""
    z = np.asarray(z, float)
    ok = np.isfinite(z)
    out = np.full(len(z), np.nan)
    if ok.sum() == 0:
        return out
    r = pd.Series(z[ok]).rank(method='average').values / ok.sum()   # (0,1]
    cdf = np.cumsum(prior)
    g = np.searchsorted(cdf, r, side='left')
    out[ok] = np.clip(g, 0, 6)
    return out


def qwk(y_true, y_pred, k=7):
    """二次加权 kappa"""
    y_true = np.asarray(y_true, int)
    y_pred = np.asarray(y_pred, int)
    O = np.zeros((k, k))
    for a, b in zip(y_true, y_pred):
        if 0 <= a < k and 0 <= b < k:
            O[a, b] += 1
    if O.sum() == 0:
        return np.nan
    w = (np.arange(k)[:, None] - np.arange(k)[None, :]) ** 2 / (k - 1) ** 2
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    return 1 - (w * O).sum() / max((w * E).sum(), 1e-12)


# ═════════════════════════════════════════════════════════════
# 以下为本文新增：等频映射（仅作对照）与直接取整（反例）
# ═════════════════════════════════════════════════════════════
def equifreq_to_grade(z):
    """对照口径：按列内经验分位等频切 7 档，隐含"每档各占 1/7"的假设。"""
    z = np.asarray(z, float)
    ok = np.isfinite(z)
    out = np.full(len(z), np.nan)
    if ok.sum() == 0:
        return out
    edges = np.unique(np.quantile(z[ok], np.linspace(0, 1, N_GRADE + 1)[1:-1]))
    out[ok] = np.searchsorted(edges, z[ok], side='right')
    return np.clip(out, 0, N_GRADE - 1)


def round_grade(z):
    """反例：平移到非负后四舍五入再截断到 0..6。"""
    z = np.asarray(z, float)
    ok = np.isfinite(z)
    out = np.full(len(z), np.nan)
    if ok.sum() == 0:
        return out
    s = z[ok] - np.nanmin(z[ok])
    out[ok] = np.clip(np.rint(s), 0, N_GRADE - 1)
    return out


def metrics(gt, gp):
    """一次算齐 QWK / 准确率 / ±1 准确率 / 等级 MAE / 分布 TV 距离。"""
    ok = np.isfinite(gt) & np.isfinite(gp)
    gt = gt[ok].astype(int)
    gp = gp[ok].astype(int)
    h_t = np.bincount(gt, minlength=N_GRADE) / max(len(gt), 1)
    h_p = np.bincount(gp, minlength=N_GRADE) / max(len(gp), 1)
    return dict(
        qwk=round(float(qwk(gt, gp)), 4),
        acc=round(float((gt == gp).mean()), 4),
        acc_pm1=round(float((np.abs(gt - gp) <= 1).mean()), 4),
        mae_grade=round(float(np.mean(np.abs(gt - gp))), 4),
        tv_dist=round(0.5 * float(np.abs(h_t - h_p).sum()), 4),
    )


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    pred = pd.read_csv(os.path.join(RES, 'q1_predictions.csv'))
    lab = pd.read_csv(os.path.join(DATA, '4.csv'))
    pred['beer'] = pred['beer'].astype(str).str.strip()
    lab['beer'] = lab['beer'].astype(str).str.strip()
    assert lab['beer'].is_unique

    sens = [c for c in lab.columns[3:] if c in pred.columns]
    assert len(sens) == 50, f'感官列应为 50，实际 {len(sens)}'

    m = lab[['beer'] + sens].merge(pred[['beer'] + sens], on='beer',
                                   suffixes=('_t', '_p'), how='inner')
    assert len(m) == 250

    g_main = {'beer': m['beer']}
    rows, hist_rows = [], []

    for s in sens:
        yt = m[f'{s}_t'].to_numpy(float)
        yp = m[f'{s}_p'].to_numpy(float)

        rec = dict(sens=s, n=int((np.isfinite(yt) & np.isfinite(yp)).sum()))

        # ── 三种先验 + 等频对照，全部用同一套指标 ──
        for pname, prior in PRIORS.items():
            gt = quantile_to_grade(yt, prior)
            gp = quantile_to_grade(yp, prior)
            mt = metrics(gt, gp)
            rec.update({f'qwk_{pname}': mt['qwk'], f'acc_{pname}': mt['acc'],
                        f'acc_pm1_{pname}': mt['acc_pm1'],
                        f'mae_{pname}': mt['mae_grade'],
                        f'tv_{pname}': mt['tv_dist']})
            if pname == MAIN_PRIOR:
                g_main[s] = gp
                gt_main, gp_main = gt, gp
            if pname == 'uniform':
                hist_rows.extend(
                    dict(sens=s, prior=pname, grade=g,
                         frac_label=round(float((gt == g).mean()), 4),
                         frac_pred=round(float((gp == g).mean()), 4))
                    for g in range(N_GRADE))

        # ── 对照：等频映射 ──
        ge_t = equifreq_to_grade(yt)
        ge_p = equifreq_to_grade(yp)
        mt = metrics(ge_t, ge_p)
        rec.update({f'qwk_equifreq': mt['qwk'], f'acc_equifreq': mt['acc'],
                    f'acc_pm1_equifreq': mt['acc_pm1'],
                    f'mae_equifreq': mt['mae_grade'],
                    f'tv_equifreq': mt['tv_dist']})

        # ── 反例：直接取整 ──
        gr = round_grade(yp)
        mt = metrics(gt_main, gr)
        rec.update({f'qwk_round': mt['qwk'], f'acc_round': mt['acc'],
                    f'frac_round_at_zero': round(float(np.nanmean(gr == 0)), 4)})

        rows.append(rec)

    met = pd.DataFrame(rows)
    met.to_csv(os.path.join(RES, 'q1_grade_metrics.csv'), index=False,
               encoding='utf-8-sig')
    pd.DataFrame(g_main).to_csv(os.path.join(RES, 'q1_grades.csv'),
                                index=False, encoding='utf-8-sig')
    pd.DataFrame(hist_rows).to_csv(os.path.join(RES, 'q1_grade_hist.csv'),
                                   index=False, encoding='utf-8-sig')

    mt = MAIN_PRIOR
    summary = dict(
        n_samples=250, n_dims=len(met), n_grades=N_GRADE,
        main_prior=MAIN_PRIOR,
        code_source='队友 q1_model.py:43-71（PRIORS / quantile_to_grade / qwk，原样照搬）',
        priors={k: [float(x) for x in v] for k, v in PRIORS.items()},
        # 主口径
        median_qwk=round(float(met[f'qwk_{mt}'].median()), 4),
        mean_qwk=round(float(met[f'qwk_{mt}'].mean()), 4),
        median_acc=round(float(met[f'acc_{mt}'].median()), 4),
        median_acc_pm1=round(float(met[f'acc_pm1_{mt}'].median()), 4),
        median_mae_grade=round(float(met[f'mae_{mt}'].median()), 4),
        median_tv_dist=round(float(met[f'tv_{mt}'].median()), 4),
        n_qwk_gt_0p3=int((met[f'qwk_{mt}'] > 0.3).sum()),
        best_dim=met.loc[met[f'qwk_{mt}'].idxmax(), 'sens'],
        best_qwk=float(met[f'qwk_{mt}'].max()),
        worst_dim=met.loc[met[f'qwk_{mt}'].idxmin(), 'sens'],
        worst_qwk=float(met[f'qwk_{mt}'].min()),
        # 敏感性：三套先验
        median_qwk_uniform=round(float(met.qwk_uniform.median()), 4),
        median_qwk_mildzero=round(float(met.qwk_mildzero.median()), 4),
        # 对照：等频映射
        median_qwk_equifreq=round(float(met.qwk_equifreq.median()), 4),
        median_acc_equifreq=round(float(met.acc_equifreq.median()), 4),
        # 反例：直接取整
        median_qwk_round=round(float(met.qwk_round.median()), 4),
        median_acc_round=round(float(met.acc_round.median()), 4),
        median_frac_round_at_zero=round(float(met.frac_round_at_zero.median()), 4),
        limitation=('附件4 无 0–6 真值，QWK/准确率均为同一映射内的往返一致性，'
                    '衡量预测分与标签分的同档比例，不是对面板真值的绝对精度；'
                    '实测每列最高频取值仅占 1.8%、等于列最小值仅 0.88%，'
                    '说明标签已中心化并加噪，零膨胀结构无法从数据直接验证，'
                    '故先验取自感官评价文献而非拟合；换先验后 QWK 的变动'
                    f'（uniform {float(met.qwk_uniform.median()):.4f} vs '
                    f'zeroinfl {float(met.qwk_zeroinfl.median()):.4f}）即映射假设'
                    '的影响幅度。'),
    )
    with open(os.path.join(RES, 'q1_grade_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f'Q1 等级映射（主口径 {mt} 先验 → 0..6）')
    print(f'  中位 QWK {summary["median_qwk"]:.4f}，均值 {summary["mean_qwk"]:.4f}，'
          f'QWK>0.3 的维度 {summary["n_qwk_gt_0p3"]}/50')
    print(f'  中位准确率 {summary["median_acc"]:.4f}，'
          f'±1 档 {summary["median_acc_pm1"]:.4f}，'
          f'等级 MAE {summary["median_mae_grade"]:.4f}')
    print(f'  最优维 {summary["best_dim"]}（{summary["best_qwk"]:.4f}），'
          f'最差维 {summary["worst_dim"]}（{summary["worst_qwk"]:.4f}）')
    print(f'  ── 先验敏感性：uniform {summary["median_qwk_uniform"]:.4f} / '
          f'mildzero {summary["median_qwk_mildzero"]:.4f} / '
          f'zeroinfl {summary["median_qwk"]:.4f}')
    print(f'  ── 等频映射对照 QWK {summary["median_qwk_equifreq"]:.4f}，'
          f'准确率 {summary["median_acc_equifreq"]:.4f}')
    print(f'  ── 直接取整反例 QWK {summary["median_qwk_round"]:.4f}，'
          f'压到 0 分占比 {summary["median_frac_round_at_zero"]:.1%}')
    print('  写出 q1_grades.csv / q1_grade_metrics.csv / q1_grade_hist.csv / '
          'q1_grade_summary.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
