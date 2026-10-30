# -*- coding: utf-8 -*-
"""q3_transfer.py — 跨风格迁移 + 覆盖赛题点名的 5 类缺陷物

为什么需要这个脚本
  赛题对问题三的原文要求有两项 q3.py 没有做：
    ① 「做跨风格迁移（如把 Pils/Lager 的化合物谱"迁移"为 Tripel 风格）」
       —— q3.py 只以目标风格自身中位数作起点，没有"源→目标"的迁移；
    ② 「缺陷化合物以所列 DMS/Diacetyl/4VG/trans-2-nonenal/Stale hops 等超阈值项为准」
       —— q3.py 只硬约束 DMS 与 4VG、软约束双乙酰，t2n 与 stale hops 完全没管。
  本脚本把这两项补齐，且缺陷物的量纲域逐列判定（t2n 与双乙酰在附件1 中是线性域）。

五类缺陷物的约束方式
  DMS           硬约束   x ≤ min(log10 θ, x0)，θ=17.25 µg/L（附件8）
  Diacetyl      硬+软    x ≤ min(θ, x0) 且超阈部分计入 f2，θ=0.299 mg/L（附件8）
  4VG           硬约束   x ≤ min(log10 θ, x0)，θ=0.206 mg/L（附件8）
  trans-2-nonenal 硬约束 x ≤ min(θ_lit, x0)，θ_lit=0.11 µg/L（附件8 该行阈值为 NA，取文献值）
  Stale hops    感官约束 代理预测值 ≤ 迁移前预测值（它不是化合物，是感官描述项）

  说明：θ_lit 取文献报道的 0.11 µg/L（折 1.1e-4 mg/L）。附件8 只给了 t2n 的列名与
  单位，阈值单元格为 NA，此处必须外部引用，不能假装表里有数。

输入（只读）
  results/q0_floor_share.csv   每列是否 log10（量纲域的唯一事实源）
  附件/1.csv、附件/4.csv、附件/8.xlsx
输出
  results/q3_transfer_pareto.csv    迁移前沿
  results/q3_transfer_defects.csv   五类缺陷物迁移前后对照
  results/q3_transfer_profile.csv   源/目标/迁移后 三线感官画像
  results/q3_transfer_run_log.json  参数与验收

用法：python code/q3_transfer.py
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
import scipy.sparse as sp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import q3  # noqa: E402

RES = q3.RES
SRC_STYLE = 'Pils/Lager'
DST_STYLE = 'Tripel'

# t2n 阈值：附件8 该行为 NA，取文献常见的啤酒中反式-2-壬烯醛气味阈值 0.11 µg/L
# = 1.1e-4 mg/L。此值必须写进论文并引用，不得声称来自附件8。
T2N_THR_MG_L = 1.1e-4
DEFECT_COMPOUNDS = ['DMS', 'X2.3.butanedione', 'X4VG', 'X.E..2.nonenal']
DEFECT_SENSORY = 'stale_hops'


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    t0 = time.perf_counter()

    print('=' * 86)
    print(f'Q3 跨风格迁移：{SRC_STYLE} → {DST_STYLE}，覆盖 5 类缺陷物')
    print('=' * 86)

    X, Y, style, feats, sens, grp, thr = q3.load()
    is_log10 = q3._load_is_log10()

    src_mask = (style == SRC_STYLE).to_numpy()
    dst_mask = (style == DST_STYLE).to_numpy()
    print(f'源风格 {SRC_STYLE} n={int(src_mask.sum())} | '
          f'目标风格 {DST_STYLE} n={int(dst_mask.sum())}')

    # ---- 决策列：Q2 归因并集 ∪ 全部缺陷物 ----
    sel, selinfo = q3.select_decision_features(feats, grp)
    for c in DEFECT_COMPOUNDS:
        if c in feats and c not in sel:
            sel.append(c)
    n = len(sel)
    print(f'决策列 {n}（含 Q2 归因并集，并强制并入 4 个缺陷化合物）')

    Xv = X[sel].to_numpy(float)
    medx = np.nanmedian(Xv, axis=0)
    Xv = np.where(np.isfinite(Xv), Xv, medx[None, :])
    Yv = Y.to_numpy(float)
    medy = np.nanmedian(Yv, axis=0)
    Yv = np.where(np.isfinite(Yv), Yv, medy[None, :])

    # ---- 起点 = 源风格的化学谱中位数（这是"被迁移的指纹"）----
    x0 = np.median(Xv[src_mask], axis=0)
    lb = np.percentile(Xv, 1, axis=0)
    ub = np.percentile(Xv, 99, axis=0)
    x0 = np.clip(x0, lb, ub)
    # 与 q3.py 同一条口径：把代理训练集裁到 MILP 可行域，避免域外的极端值
    # 独占 PLS 的协方差（详见 q3.py 中该处的注释）。
    Xv = np.clip(Xv, lb, ub)
    Targ = np.median(Yv[dst_mask], axis=0)
    print(f'起点取 {SRC_STYLE} 化学谱中位数；目标感官取 {DST_STYLE} 中位数')

    # ---- 代理 ----
    C, B, k_best, cv_r2, cv_mse = q3.fit_pls_surrogate(Xv, Yv)
    sd = Yv.std(axis=0)
    sd = np.where(sd > 1e-9, sd, 1.0)
    w = 1.0 / sd
    print(f'PLS 代理：{k_best} 成分，逐维 CV R² 中位 {np.median(cv_r2):.4f}')

    # ---- 五类缺陷物的约束 ----
    # 赛题要求两件事：「缺陷化合物以所列 ... 超阈值项为准」+「保持缺陷化合物不恶化」。
    # 「不恶化」是无条件可执行的（x ≤ x0）；「不超阈值」要看该列量纲域里的阈值是否
    # 可达。逐列判定，并把结论如实记录，不含糊。
    def thr_dom(f):
        t = float(thr[f])
        return float(np.log10(t)) if is_log10.get(f, True) else t

    lb_arr = np.asarray(lb, dtype=float)
    hard, soft, notes = [], [], []
    for c in DEFECT_COMPOUNDS:
        if c not in sel:
            notes.append(f'{c} 不在决策列，跳过')
            continue
        j = sel.index(c)
        x0_j = float(x0[j])
        # 阈值（量纲域）：t2n 附件8 该行为 NA，只能引文献
        if c == 'X.E..2.nonenal':
            th = T2N_THR_MG_L
            th_src = '文献 0.11 µg/L（附件8 该行为 NA）'
        elif c in thr:
            th = thr_dom(c)
            th_src = '附件8 threshold_mean'
        else:
            th = np.nan
            th_src = '无阈值'
        # 目标上限：不恶化是底线；阈值可达时再收紧到阈值
        cap = x0_j
        if np.isfinite(th):
            if lb_arr[j] <= th + 1e-12:
                cap = min(th, x0_j)
            else:
                notes.append(
                    f'{c}：文献/表中阈值 {th:.4g} 低于该列下界 {lb_arr[j]:.4g}，'
                    f'数据集内无样本可满足 → 只约束"不恶化"')
        hard.append((j, cap, c, th, th_src))
        if c == 'X2.3.butanedione':
            soft.append((j, th if np.isfinite(th) else x0_j, c))

    kh_idx = [h[0] for h in hard]
    hard_cap = [h[1] for h in hard]
    ks_idx = [s[0] for s in soft]
    soft_thr = [s[1] for s in soft]
    print('\n缺陷物约束（cap=min(阈值, 迁移前值)，底线是"不恶化"）：')
    for j, cap, c, th, src in hard:
        dom = ('log10 域' if is_log10.get(c, True) else '线性域/mg·L⁻¹') \
            if c in is_log10 else '线性域'
        print(f'  硬 {c:20s} [{dom:16s}] θ={th if np.isfinite(th) else float("nan"):10.4g}'
              f'  迁移前={x0[j]:10.4g}  cap={cap:10.4g}')
    for n_ in notes:
        print(f'  注 {n_}')
    for j, t, c in soft:
        print(f'  软 {c:20s} 超阈部分计入 f2，θ={t:.4g}')

    # ---- 感官约束：stale hops 不恶化（必须走 build_arrays 的 sens_ub 参数）----
    base = C + B @ x0
    si = sens.index(DEFECT_SENSORY) if DEFECT_SENSORY in sens else None
    sens_ub = [(si, float(base[si]))] if si is not None else None
    if si is not None:
        print(f'  感官 {DEFECT_SENSORY:20s} 迁移前代理预测={base[si]:.4f}，'
              f'要求迁移后 ≤ 该值')

    arr = q3.build_arrays(n, len(sens), kh_idx, ks_idx, x0, lb, ub, Targ,
                          B, C, w, q3.GAMMA, q3.LAMBDA, hard_cap, soft_thr,
                          q3.K_MAX, sens_ub=sens_ub)
    arr.update(_lb=lb, _ub=ub, _C=C)
    print(f'  模型规模：{arr["nv"]} 变量 / {arr["A_ub"].shape[0]} 约束'
          f'（含 {len(sens_ub) if sens_ub else 0} 条感官非恶化约束）')

    # ---- 解：AUGMECON2 ε-约束 ----
    pts, pay = q3.augmecon2(arr, B, x0, Targ, w, q3.GAMMA, q3.LAMBDA,
                            kh_idx, ks_idx, hard_cap, soft_thr, q3.K_MAX,
                            12, 8, 'gurobi', print, sens_ub=sens_ub)
    if not pts:
        print('!! 无可行解')
        return 1

    Obj = np.array([[q['f1'], q['f2'], q['f3']] for q in pts])
    pm = q3.pareto_mask(Obj)
    nd = [q for q, keep in zip(pts, pm) if keep]
    nd.sort(key=lambda q: (q['f1'], q['f3']))
    uniq = len({(round(q['f1'], 6), round(q['f3'], 6)) for q in nd})
    print(f'\nε 格点可行 {len(pts)} → 非支配 {len(nd)}（唯一前沿点 {uniq}）')

    # 缺陷物 z 在该情形下结构恒为 0（双乙酰迁移后远低于阈值），f2 无量纲可交易，
    # 故 ε-约束只剩 f1–f3 一条轴，96 次求解塌缩到 3 个唯一解。ε 扫描不保证
    # 触到 f1 的极值点（网格端点与 payoff 上界重合时会被数值误差挤掉），
    # 因此报告点改用**带全部约束的单目标 f1 最优解**，前沿只作为权衡形状。
    arr.update(_lb=lb, _ub=ub, _C=C)
    obj1 = q3._obj_vec(arr, 'f1', w, q3.GAMMA, q3.LAMBDA)
    sol1 = q3.solve_milp(arr, obj_override=obj1, solver='gurobi')
    if sol1.get('x') is None:
        print(f'!! f1 单目标求解失败：{sol1.get("status_name")}')
        return 1
    m1 = q3.metrics_of(sol1['x'], arr, B, x0, Targ, w, q3.GAMMA, q3.LAMBDA,
                       kh_idx, ks_idx, hard_cap)
    best = m1
    t_best = m1['t']
    f1_at_x0 = float(np.sum(w * np.abs(C + B @ x0 - Targ)))
    print(f'f1 单目标最优：{m1["f1"]:.4f}（ε 前沿最小 {nd[0]["f1"]:.4f}）'
          f'，改动 {int((m1["y"] > 0.5).sum())} 个化合物')
    print(f'同一代理下 f1(x0)={f1_at_x0:.4f} → 最优 {m1["f1"]:.4f}'
          f'（降 {100 * (1 - m1["f1"] / f1_at_x0):.2f}%）')

    par = pd.DataFrame([dict(point=f'P{i+1}', f1=round(q['f1'], 6),
                             f2=round(q['f2'], 6), f3=round(q['f3'], 6),
                             n_changed=int((q['y'] > 0.5).sum()),
                             changed=';'.join([sel[j] for j in range(n)
                                               if q['y'][j] > 0.5]))
                       for i, q in enumerate(nd)])
    par.to_csv(os.path.join(RES, 'q3_transfer_pareto.csv'), index=False,
               encoding='utf-8-sig')

    # ---- 缺陷物迁移前后对照（在 f1 最优的点上）----
    rows = []
    for c in DEFECT_COMPOUNDS:
        if c not in sel:
            continue
        j = sel.index(c)
        before, after = float(x0[j]), float(t_best[j])
        if c == 'X.E..2.nonenal':
            th_dom, unit, src_thr = T2N_THR_MG_L, 'mg/L（文献 0.11 µg/L）', 'literature'
        elif c in thr:
            th_dom = thr_dom(c)
            unit = 'log10 域' if is_log10.get(c, True) else 'mg/L'
            src_thr = 'att8'
        else:
            th_dom, unit, src_thr = np.nan, '-', 'none'
        rows.append(dict(
            defect=c, domain=unit, source_thr=src_thr,
            thr_in_domain=round(float(th_dom), 8) if np.isfinite(th_dom) else None,
            before=round(before, 8), after=round(after, 8),
            delta=round(after - before, 8),
            worsened=bool(after > before + 1e-9),
            over_thr_after=bool(np.isfinite(th_dom) and after > th_dom + 1e-9),
        ))
    if si is not None:
        pred_after = float(arr['base'][si] + B[si] @ (t_best - x0))
        rows.append(dict(
            defect=DEFECT_SENSORY, domain='代理预测（感官）', source_thr='n/a',
            thr_in_domain=round(float(base[si]), 6),
            before=round(float(base[si]), 6), after=round(pred_after, 6),
            delta=round(pred_after - float(base[si]), 6),
            worsened=bool(pred_after > float(base[si]) + 1e-9),
            over_thr_after=False,
        ))
    dfd = pd.DataFrame(rows)
    dfd.to_csv(os.path.join(RES, 'q3_transfer_defects.csv'), index=False,
               encoding='utf-8-sig')

    # ══════════════════════════════════════════════════════════
    # 消融：去掉缺陷物约束后重解一次，量化「不恶化」到底约束住了什么
    #
    # 必要性：五类缺陷物的 cap 全部等于 x0（阈值不可达或高于 x0），因此
    # 约束形如 x_j ≤ x0_j。此时 Δ=0 是**约束被满足的证书**，不是发现；
    # 若只报 Δ=0，等于把硬约束重述一遍当作结论。真正有信息量的是两件事：
    #   ① 不加约束时这些缺陷物会不会变差、变差多少；
    #   ② 为了压住它们，f1 付出了多少。
    # 故在此求解同类模型但不含缺陷约束的那一版，逐项对照。
    # ══════════════════════════════════════════════════════════
    arr_free = q3.build_arrays(n, len(sens), [], [], x0, lb, ub, Targ,
                               B, C, w, q3.GAMMA, q3.LAMBDA, [], [],
                               q3.K_MAX, sens_ub=None)
    obj_free = q3._obj_vec(arr_free, 'f1', w, q3.GAMMA, q3.LAMBDA)
    sol_free = q3.solve_milp(arr_free, obj_override=obj_free, solver='gurobi')
    t_free = None
    if sol_free.get('x') is not None:
        mf = q3.metrics_of(sol_free['x'], arr_free, B, x0, Targ, w,
                           q3.GAMMA, q3.LAMBDA, [], [], [])
        t_free = mf['t']
        print(f'\n消融（去掉缺陷约束）：状态 {sol_free["status_name"]}，'
              f'f1={mf["f1"]:.4f}（受约束版 {best["f1"]:.4f}）')
    else:
        print(f'\n消融失败：{sol_free.get("status_name")}')

    abl = []
    if t_free is not None:
        for c in DEFECT_COMPOUNDS:
            if c not in sel:
                continue
            j = sel.index(c)
            a_free = float(t_free[j])
            abl.append(dict(defect=c, before=round(float(x0[j]), 8),
                            after_no_cap=round(a_free, 8),
                            delta_no_cap=round(a_free - float(x0[j]), 8),
                            after_capped=round(float(t_best[j]), 8),
                            would_worsen=bool(a_free > float(x0[j]) + 1e-9)))
        if si is not None:
            p_free = float(base[si] + B[si] @ (t_free - x0))
            abl.append(dict(defect=DEFECT_SENSORY, before=round(float(base[si]), 6),
                            after_no_cap=round(p_free, 6),
                            delta_no_cap=round(p_free - float(base[si]), 6),
                            after_capped=round(float(pred_after), 6),
                            would_worsen=bool(p_free > float(base[si]) + 1e-9)))
    dfa = pd.DataFrame(abl)
    if len(dfa):
        dfa.to_csv(os.path.join(RES, 'q3_transfer_ablation.csv'), index=False,
                   encoding='utf-8-sig')
        n_ww = int(dfa.would_worsen.sum())
        cost_f1 = float(best['f1']) - float(mf['f1'])
        print(f'  不加缺陷约束时 {n_ww}/{len(dfa)} 类缺陷物会变差；'
              f'为压住它们 f1 增加 {cost_f1:+.4f}'
              f'（{100 * cost_f1 / max(float(mf["f1"]), 1e-9):+.2f}%）')
        print(dfa.to_string(index=False))
    else:
        n_ww, cost_f1, mf = 0, float('nan'), dict(f1=float('nan'))

    # ---- 三线感官画像 ----
    prof = []
    for s_i, s_name in enumerate(sens):
        prof.append(dict(dim=s_name,
                         src=round(float(np.median(Yv[src_mask][:, s_i])), 4),
                         dst=round(float(Targ[s_i]), 4),
                         migrated=round(float(arr['base'][s_i] +
                                              B[s_i] @ (t_best - x0)), 4)))
    pd.DataFrame(prof).to_csv(os.path.join(RES, 'q3_transfer_profile.csv'),
                              index=False, encoding='utf-8-sig')

    d_src = float(np.sum(w * np.abs(np.median(Yv[src_mask], axis=0) - Targ)))
    log = dict(
        src_style=SRC_STYLE, dst_style=DST_STYLE,
        n_src=int(src_mask.sum()), n_dst=int(dst_mask.sum()),
        n_decision=n, pls_components=int(k_best),
        # 口径：before 与 after 必须由**同一个代理**给出，否则不可比。
        # f1_source_measured 是源风格实测中位与目标的距离，只作参考，
        # 不参与降幅计算——实测值与代理预测值之间隔着 PLS 的拟合误差。
        f1_source_measured=round(d_src, 6),
        f1_at_x0=round(f1_at_x0, 6),
        f1_migrated=round(float(m1['f1']), 6),
        f1_reduction_pct=round(100 * (1 - float(m1['f1']) / f1_at_x0), 2),
        n_changed=int((m1['y'] > 0.5).sum()),
        n_pareto=len(nd), n_front_unique=int(uniq),
        f1_front_min=round(float(nd[0]['f1']), 6),
        all_defects_non_worsening=bool(not dfd.worsened.any()),
        # 消融：Δ=0 是硬约束的证书记录，真正的信息在下面两个字段
        n_defects_would_worsen_without_cap=int(n_ww),
        n_defects_total=int(len(dfa)),
        f1_without_defect_cap=round(float(mf['f1']), 6),
        f1_cost_of_defect_cap=round(float(cost_f1), 6),
        t2n_threshold_note='附件8 该行为 NA，取文献值 0.11 µg/L = 1.1e-4 mg/L',
        duration_s=round(time.perf_counter() - t0, 1),
    )
    with open(os.path.join(RES, 'q3_transfer_run_log.json'), 'w',
              encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print('\n' + '-' * 86)
    print('五类缺陷物迁移前后（f1 最小的迁移点）：')
    print(dfd.to_string(index=False))
    print(f'\n感官偏差 f1：同一代理下 x0 为 {f1_at_x0:.4f} → 迁移后 {m1["f1"]:.4f}'
          f'（降 {log["f1_reduction_pct"]:.2f}%），改动 {log["n_changed"]} 个化合物')
    print(f'  参考：源风格实测中位与目标的距离 {d_src:.4f}（实测口径，不与代理口径混用）')
    print(f'全部缺陷物不恶化：{log["all_defects_non_worsening"]}')
    print(f'写出 q3_transfer_pareto.csv / q3_transfer_defects.csv / '
          f'q3_transfer_profile.csv / q3_transfer_run_log.json')
    print(f'耗时 {log["duration_s"]} s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
