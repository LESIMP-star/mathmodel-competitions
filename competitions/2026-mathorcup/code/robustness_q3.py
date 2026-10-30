# -*- coding: utf-8 -*-
"""robustness_q3.py — Q3 灵敏度分析（单因素扰动，每次真解 MILP）

设计约束
  1. 每个扰动都**重新求解** MILP，不套任何解析近似公式。
     队友 figs.py:467-508 的 tornado 图用 f1_of(p) 一个手写公式代替求解，
     那条路径在本项目禁用（等价于造数）。
  2. 只读 q3.py 的建模函数（build_arrays / solve_milp / metrics_of），
     不复制约束定义，避免两处口径漂移。
  3. 基准 = q3_pareto.csv 的 P1（f1 最小点），其 (ε2, ε3) 作为基准约束。
  4. 输出 results/q3_sensitivity.csv，供 figures.py 的 fig_q3_tornado 只读作图。

用法：python code/robustness_q3.py
本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：Hermes Agent（Nous Research），底层模型 deepseek-v4-flash，
# 开发机构：Nous Research（工具）/ 深度求索 DeepSeek（模型），使用日期：2026-10-26
"""
from __future__ import annotations

import os
import sys
import json
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import q3  # noqa: E402  建模函数的唯一来源


STYLE = 'Tripel'
OUT = q3.RES


def build_base(args):
    """复刻 q3.main 的前半段：数据 → 决策列 → 生成器 → 代理 → 约束 → 矩阵。"""
    X, Y, style, feats, sens, grp, thr = q3.load()
    rng = np.random.default_rng(q3.SEED)
    ns = len(sens)

    mask = (style == STYLE).to_numpy()
    sel, selinfo = q3.select_decision_features(feats, grp)
    n = len(sel)

    Xv = X[sel].to_numpy(float)
    medx = np.nanmedian(Xv, axis=0)
    Xv = np.where(np.isfinite(Xv), Xv, medx[None, :])
    Yv = Y.to_numpy(float)
    medy = np.nanmedian(Yv, axis=0)
    Yv = np.where(np.isfinite(Yv), Yv, medy[None, :])

    x0 = np.median(Xv[mask], axis=0)
    lb = np.percentile(Xv, 1, axis=0)
    ub = np.percentile(Xv, 99, axis=0)
    x0 = np.clip(x0, lb, ub)

    mu_s, cov_s, shrink_s, gen = q3.fit_generator(Xv[mask], rng, args['n_gen'])
    gen = np.clip(gen, lb, ub)

    # ⚠ 必须与 q3.py 主流程一致：PLS 代理的训练集要裁到 MILP 可行域 [lb, ub]。
    # 不裁的后果：线性浓度列（X2.methyltetrahydrofuran.3.one，std 795）独占协方差，
    # 成分数塌缩、CV R² 转负，代理与主结果不是同一个；实测未裁时 f1=11.0431，
    # 裁剪后与主流程同口径。
    Xv = np.clip(Xv, lb, ub)
    C, B, k_best, cv_r2, cv_mse = q3.fit_pls_surrogate(Xv, Yv)
    sd = Yv.std(axis=0)
    sd = np.where(sd > 1e-9, sd, 1.0)
    w = 1.0 / sd
    Targ = np.median(Yv[mask], axis=0)

    kh_idx = [sel.index(k) for k in q3.K_HARD if k in sel]
    ks_idx = [sel.index(k) for k in q3.K_SOFT if k in sel]
    # 阈值必须换算到各列在附件1 中的实际量纲域（同 q3.py 的修正）：
    # DMS/X4VG 在 log10 域，双乙酰在线性 mg/L 域。一律取 log10 会让线性域列的
    # 软约束退化成常数，ε2 网格随之失效。
    is_log10 = q3._load_is_log10()

    def thr_dom(f):
        t = float(thr[f])
        return float(np.log10(t)) if is_log10.get(f, True) else t

    hard_cap = [min(thr_dom(sel[j]), x0[j]) for j in kh_idx]
    soft_thr = [thr_dom(sel[j]) for j in ks_idx]

    return dict(X=X, Y=Y, sel=sel, sens=sens, grp=grp, thr=thr, n=n, ns=ns,
                Xv=Xv, Yv=Yv, x0=x0, lb=lb, ub=ub, mask=mask,
                C=C, B=B, k_best=k_best, cv_r2=cv_r2, sd=sd, w=w, Targ=Targ,
                kh_idx=kh_idx, ks_idx=ks_idx, hard_cap=hard_cap, soft_thr=soft_thr,
                rng=rng, shrink=shrink_s, n_style=int(mask.sum()))


def solve_at(base, kmax, gamma, lam, e_f2, e_f3, C=None, B=None):
    """在给定参数下解一次 min f1，返回 (f1, f2, f3, status, n_changed)。"""
    B_use = base['B'] if B is None else B
    C_use = base['C'] if C is None else C
    arr = q3.build_arrays(base['n'], base['ns'], base['kh_idx'], base['ks_idx'],
                          base['x0'], base['lb'], base['ub'], base['Targ'],
                          B_use, C_use, base['w'], gamma, lam,
                          base['hard_cap'], base['soft_thr'], kmax,
                          e_f2=e_f2, e_f3=e_f3)
    r = q3.solve_milp(arr, obj_override=q3._obj_vec(arr, 'f1', base['w'], gamma, lam),
                      solver='gurobi')
    if r['x'] is None:
        return dict(f1=np.nan, f2=np.nan, f3=np.nan,
                    status=r['status_name'], n_changed=0, feasible=False)
    met = q3.metrics_of(r['x'], arr, B_use, base['x0'], base['Targ'],
                        base['w'], gamma, lam, base['kh_idx'], base['ks_idx'],
                        base['hard_cap'])
    # 改动化合物个数 = 改动指示 y 的活跃数（不是软约束 slack 的 z）
    return dict(f1=met['f1'], f2=met['f2'], f3=met['f3'],
                status=r['status_name'], n_changed=int((met['y'] > 0.5).sum()),
                feasible=True)


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    t0 = time.perf_counter()
    print('=' * 88)
    print('Q3 灵敏度分析：单因素扰动，每次真解 MILP（不套解析公式）')
    print('=' * 88)

    base = build_base(dict(n_gen=200))
    print(f'样本 {len(base["X"])} | 决策列 {base["n"]} | 感官 {base["ns"]} '
          f'| {STYLE} n={base["n_style"]} | 收缩 δ={base["shrink"]:.4f} '
          f'| PLS 成分 {base["k_best"]}')

    # ---- 基准：P1 的 (ε2, ε3) ----
    # 单位修正后 P1 的 f2 可以达到 0（双乙酰不再被伪约束卡在 0.524），
    # 因此 ε2 不能用 f2+1e-9 这种绝对容差，否则 1e-9 的相对收紧会让模型不可行。
    par = pd.read_csv(os.path.join(OUT, 'q3_pareto.csv'))
    p1 = par.loc[par.f1.idxmin()]
    EPS_TOL = 1e-3
    e_f2_base = float(p1.f2) + EPS_TOL
    e_f3_base = float(p1.f3) + EPS_TOL
    ref = solve_at(base, q3.K_MAX, q3.GAMMA, q3.LAMBDA, e_f2_base, e_f3_base)
    f1_ref = ref['f1']
    print(f'基准（k_max={q3.K_MAX}, γ={q3.GAMMA}, λ={q3.LAMBDA}, '
          f'ε2={e_f2_base:.4f}, ε3={e_f3_base:.4f}）→ f1={f1_ref:.4f}, '
          f'改动 {ref["n_changed"]} 个  [{ref["status"]}]')

    rows = []

    def record(param, label, value, tag, res):
        rows.append(dict(param=param, label=label, value=value, tag=tag,
                         f1=res['f1'], df1=res['f1'] - f1_ref,
                         f2=res['f2'], f3=res['f3'],
                         n_changed=res['n_changed'], status=res['status']))
        flag = '' if res['feasible'] else '  ✗ 不可行'
        print(f'  {label:22s} {tag:8s} = {value:8.3f} → f1={res["f1"]:8.4f} '
              f'(Δ={res["f1"] - f1_ref:+8.4f}, 改动 {res["n_changed"]:2d}){flag}')

    # ---- ① 干预预算 k_max ----
    print('\n① 干预预算 k_max（改动上限）')
    for km in (15, 20, 25, 30, 35):
        record('k_max', '干预预算 k_max', km, 'k_max',
               solve_at(base, km, q3.GAMMA, q3.LAMBDA, e_f2_base, e_f3_base))

    # ---- ② f3 的列代价 γ ----
    print('\n② 改动列代价 γ（f3 中每个被改列的固定代价）')
    for g in (0.5, 1.0, 2.0, 4.0):
        record('gamma', '改动列代价 γ', g, 'gamma',
               solve_at(base, q3.K_MAX, g, q3.LAMBDA, e_f2_base, e_f3_base))

    # ---- ③ f3 的量代价 λ ----
    print('\n③ 改动量代价 λ（f3 中每单位 |Δx| 的代价）')
    for lm in (0.05, 0.1, 0.2, 0.4):
        record('lambda', '改动量代价 λ', lm, 'lambda',
               solve_at(base, q3.K_MAX, q3.GAMMA, lm, e_f2_base, e_f3_base))

    # ---- ④ 缺陷容忍 ε2 ----
    print('\n④ 缺陷风险上限 ε2（双乙酰软约束的容忍度）')
    for mult in (0.5, 1.0, 1.5, 2.0):
        e2 = e_f2_base * mult
        record('eps2', '缺陷风险上限 ε2', e2, 'eps2',
               solve_at(base, q3.K_MAX, q3.GAMMA, q3.LAMBDA, e2, e_f3_base))

    # ---- ⑤ 改动预算 ε3 ----
    print('\n⑤ 改动代价上限 ε3（工艺预算）')
    for mult in (0.6, 0.8, 1.0, 1.3, 1.6):
        e3 = e_f3_base * mult
        record('eps3', '改动代价上限 ε3', e3, 'eps3',
               solve_at(base, q3.K_MAX, q3.GAMMA, q3.LAMBDA, e_f2_base, e3))

    # ---- ⑥ PLS 代理成分数 ----
    print('\n⑥ PLS 代理成分数（重建代理后重解，检验代理设定对结论的影响）')
    for k in (4, 6, 8, 10, 13):
        Ck, Bk, _, cvk, _ = q3.fit_pls_surrogate(base['Xv'], base['Yv'],
                                                 grid=(k,))
        res = solve_at(base, q3.K_MAX, q3.GAMMA, q3.LAMBDA, e_f2_base, e_f3_base,
                       C=Ck, B=Bk)
        res_k = dict(res)
        record('pls_k', 'PLS 成分数', k, 'pls_k', res_k)
        rows[-1]['pls_cv_r2_median'] = float(np.median(cvk))

    df = pd.DataFrame(rows)

    # ---- 汇总：每个参数在扰动范围内的 f1 摆幅 → tornado 排序依据 ----
    pivot = (df.groupby(['param', 'label'])
               .agg(f1_min=('f1', 'min'), f1_max=('f1', 'max'),
                    f1_lo=('f1', lambda s: s.iloc[0]),
                    f1_hi=('f1', lambda s: s.iloc[-1]))
               .reset_index())
    pivot['span'] = pivot.f1_max - pivot.f1_min
    pivot = pivot.sort_values('span', ascending=False)

    df.to_csv(os.path.join(OUT, 'q3_sensitivity.csv'), index=False, encoding='utf-8-sig')
    pivot.to_csv(os.path.join(OUT, 'q3_sensitivity_span.csv'), index=False,
                 encoding='utf-8-sig')

    print('\n' + '-' * 88)
    print('按 f1 摆幅排序（龙卷风图的长度依据）')
    for _, r in pivot.iterrows():
        print(f'  {r.label:22s} 摆幅 {r.span:8.4f}  '
              f'[{r.f1_min:.4f}, {r.f1_max:.4f}]')

    summary = dict(
        style=STYLE,
        n_style=base['n_style'],
        n_decision=base['n'],
        pls_components=int(base['k_best']),
        shrinkage_delta=round(float(base['shrink']), 4),
        base_params=dict(k_max=q3.K_MAX, gamma=q3.GAMMA, lam=q3.LAMBDA,
                         eps2=e_f2_base, eps3=e_f3_base),
        base_f1=round(float(f1_ref), 6),
        n_runs=int(len(df)),
        dominant_param=pivot.iloc[0].label,
        dominant_span=round(float(pivot.iloc[0].span), 6),
        duration_s=round(time.perf_counter() - t0, 1),
        note='每次扰动均重新求解 MILP，无解析近似',
    )
    with open(os.path.join(OUT, 'q3_sensitivity_summary.json'), 'w',
              encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f'\n共 {len(df)} 次重解，主导演化参数：{summary["dominant_param"]}'
          f'（摆幅 {summary["dominant_span"]:.4f}）')
    print(f'写出 q3_sensitivity.csv / q3_sensitivity_span.csv / '
          f'q3_sensitivity_summary.json → {OUT}')
    print(f'耗时 {summary["duration_s"]} s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
