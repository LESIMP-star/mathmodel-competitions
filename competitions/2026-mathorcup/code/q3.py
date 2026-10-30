# -*- coding: utf-8 -*-
"""q3.py — 问题三：风格条件生成 → PLS 线性代理 → AUGMECON2 ε-约束 + 真 MILP（Gurobi）→ NSGA-II 互证

本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：Hermes Agent（Nous Research），底层模型 deepseek-v4-flash，
# 开发机构：Nous Research（工具）/ 深度求索 DeepSeek（模型），使用日期：2026-10-26

================================================================ 问题的真实结构
题面写的是"风格条件生成 + 迁移不改缺陷"。它不是纯生成题，而是
  生成候选谱 → 代理预测感官 → 约束优化（含"改不改这一列"的离散决策）
生成部分只负责给出一个可信的起点，真正决定结果的是约束优化。
所以本文件重心在 MILP；生成用可解释、可复现的收缩高斯，不用 cVAE
（250 样本、最小风格类仅 3 个样本，深度生成模型在这个样本量上无法验证是否只是复制训练样本）。

================================================================ 三处必须先讲清的结构性修正（都是实测推翻了初版设计）

【修正一】代理不能用 212 个原始列直接回归
  初版把 226 个列（剔除理化/内标后 212 个）全塞进 Ridge，在 Tripel 的 28 个样本上
  拟合 212 个系数 → 训练域内 R² = 1.0000。这不是"代理很准"，是**过拟合到插值**：
  n_s = 28 < p = 212，回归系数根本不可辨识。
  修正：① 决策列先按 Q2 的归因结果收缩（只保留对某个感官维进过 Top-3 的化合物
  ＋硬/软约束化合物），这是 Q2 → Q3 的真实依赖；② 代理改用 **PLS**（偏最小二乘），
  成分数由 5 折交叉验证选，天然处理 p>n 与共线；③ 代理在**全部 250 个样本**上拟合
  ——风格子集只用于设定目标谱 Targ 与可行域，不用于估计映射本身。
  报告的是**交叉验证 R²**，不是训练域内 R²。

【修正二】决策变量数必须少于感官约束数，否则 f1 恒为 0
  50 个感官方程、212 个自由变量 → 线性系统欠定，可以精确打到目标谱，f1 = 0。
  初版 payoff 表里 min f1 = 0.0000，且几乎不花任何改动代价 —— 说明 f1 被架空了，
  所谓 Pareto 前沿退化成一个点。
  修正：加**基数约束 Σ y_j ≤ K_MAX**（工艺上不可能同时改两百个化合物，
  "最多改 K 个"是本题最自然的干预预算），并取 K_MAX < n_s，
  使 50 个方程无法被少数变量精确满足，f1 因此成为真实的权衡目标。
  K_MAX 也是可以扫描的工艺参数。

【修正三】软约束松弛量 z 必须有上界
  初版 z ∈ [0, ∞)。当 z 不在目标里时，单纯形会把 z 顶到某个任意大的基解位置，
  payoff 表实测 f2 上界跑到 1e8 —— 那不是"软约束违反 1 亿"，是变量无界导致的数值垃圾。
  修正：z ≤ z_max，z_max 由变量取值范围推出。

================================================================ 三段流水线

① 风格参考（生成）
   按 tasting_category_fine 取该风格样本，在决策子集上估计均值与协方差，
   用 **Ledoit-Wolf 收缩**（收缩强度由数据自适应，Ledoit & Wolf 2004）：
   n_s 越小 Σ 越不可靠，收缩越强，小风格类自然被拉向总体协方差。
   参考点 x0 = 风格逐列中位数；可行域 = 全体样本 [q01, q99]。

② PLS 线性代理（为了能进 MILP）
   MILP 只能吃线性结构。PLS 给出 ŷ = c + B t（t 为绝对 log10 值），
   成分数 k 由 5 折 CV 选。代理误差上界必须实测并如实报告：
   在可行域内蒙特卡洛抽样，比较 PLS 与 LightGBM 的绝对偏差。
   这个上界若大于 f1 在 Pareto 点之间的差异，就说明"前沿上的精细差别不可信" ——
   这是一条必须写进论文的负结果。

③ 约束优化（核心升级：连续松弛 → 真 MILP）
   决策变量（n 决策列、n_s 感官维、n_k 软约束物）：
     dp[j], dn[j] ≥ 0     调整量，t_j = x0_j + dp_j − dn_j（|Δ| 线性化）
     y[j] ∈ {0,1}          该列是否被改动
     up[s], um[s] ≥ 0      感官偏差松弛
     z[k] ≥ 0              软约束违反量（有上界）
   目标（全文口径统一，不混用）：
     f1 = Σ_s w_s (up_s + um_s)                    感官偏差，**L1**，w_s = 1/sd_s
     f2 = Σ_{k∈K_soft} z_k                         软约束违反量
     f3 = Σ_j γ_j y_j + λ Σ_j (dp_j + dn_j)        **含 y 项**
   硬约束：DMS、X4VG 两条，cap = min(log10 θ, 当前值)（"不得超标且不得恶化"）
   基数约束：Σ y_j ≤ K_MAX
   big-M：dp_j ≤ M_j y_j，dn_j ≤ M_j y_j

   双乙酰为何进软约束：题面要求"生成时不能恶化"，而"恶化"的参照可以是绝对阈值
   （θ=0.299）也可以是原样本自身值。8.xlsx 实测 DMS=17.25/中位 19.0、
   双乙酰=0.299/中位 0.09、4VG=0.206/中位 0.20 —— 取均值还是中位会翻转结论。
   做成软约束并用 f2 显式记账，比强行选一个口径塞进硬约束诚实。

④ AUGMECON2 式 ε-约束
   payoff table 定 (f2, f3) 范围，网格上最小化 f1 + eps·(f2/n2 + 0.1·f3/n3)。
   增广项用于剔除弱 Pareto 点（Mavrotas & Florios 2013）。

⑤ 精确 vs 启发式（验收第 5 条）
   手写 NSGA-II（`nsga2.py`，SBX η=15 + 多项式变异 η=20，染色体 = n 维连续调整量，
   二进制 y 由 |Δ|>0 后验导出），**初始种群用 delta=0 播种**（x0 本身可行，
   否则 212 维随机初始化几乎必然违反 DMS 上限，实测初版 20×10 代一个可行解都没出现）。
   报支配覆盖 / 归一化最短距离 / 蒙特卡洛超体积。

================================================================ 验收（每个 Pareto 点逐条打印，缺一条该点不进论文）
 1 可行性：硬约束余量 t_j − cap_k ≤ 0 逐项打印
 2 最优性凭证：status=OPTIMAL，报 MIP gap 与耗时；截断须写 TIME_LIMIT，不许当最优报
 3 非支配性：与所有其他点两两比较
 4 基线：必须报 x=0（什么都不改）时的 f1/f3
 5 与 NSGA-II 互证：支配覆盖 / 归一化最短距离 / HV

================================================================ 输出
  results/q3_pareto.csv       Pareto 点（f1/f2/f3、改动清单、硬约束余量、状态、gap）
  results/q3_surrogate.csv    逐感官维的 CV R²、代理误差上界
  results/q3_style_ref.csv    逐列参考谱、上下界、组别
  results/q3_generated.csv    生成候选谱
  results/q3_compare.csv      精确解 vs NSGA-II 三项指标
  results/q3_run_log.json

================================================================ 运行
  python q3.py                          # 默认 Tripel（n=28）
  python q3.py --style Blond            # Blond（n=31，最大类）
  python q3.py --kmax 15 --grid 6 6     # 改干预预算 / ε 网格
  python q3.py --smoke                  # 极小规模冒烟
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
import scipy.sparse as sp

warnings.filterwarnings('ignore')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, '附件')
RES = os.path.join(ROOT, 'results')
os.makedirs(RES, exist_ok=True)

sys.path.insert(0, HERE)
from nsga2 import nsga2, dominance_coverage, pareto_mask  # noqa: E402
from q2 import LOG10_COLS, PHYSICOCHEM, NON_AROMA_GROUPS, norm_key  # noqa: E402

SEED = 2026
DERIVED = ['kcalperc', 'esters_sum', 'aroma_hops_sum', 'acids_sum', 'sulfur_sum']

K_HARD = ['DMS', 'X4VG']
K_SOFT = ['X2.3.butanedione']
THRESH_QUANTILE = 0.95

K_MAX = 25          # 干预预算：最多同时改动多少个化合物（须 < 感官维数）
GAMMA = 1.0         # f3 中每个被改动列的代价
LAMBDA = 0.1        # f3 中改动量代价
EPS_AUG = 1e-3
MIP_GAP = 1e-4
TIME_LIMIT = 60.0
N_MC_BOUND = 2000
N_MC_HV = 200000
PLSR_GRID = (2, 3, 4, 6, 8, 10, 13, 16, 20)


def have_gurobi():
    try:
        import gurobipy  # noqa: F401
        return True
    except Exception:
        return False


# ============================================================ 数据
def _load_is_log10():
    """读 q0_floor_share.csv 的 is_log10 列：判断每个化学列在附件1 中是否已取 log10。
    这份判定由 q0_relations.py 生成（并用附件8 的 Calibrated 表交叉验证），
    是全文量纲口径的唯一事实源，这里不重新推断。"""
    p = os.path.join(RES, 'q0_floor_share.csv')
    if not os.path.exists(p):
        return {}
    d = pd.read_csv(p)
    return {str(r.feat): bool(r.is_log10) for r in d.itertuples()}


def load():
    import openpyxl
    c1 = pd.read_csv(os.path.join(DATA, '1.csv'))
    c4 = pd.read_csv(os.path.join(DATA, '4.csv'))
    # 主口径 231 列（与附件2 的 231×231 相关矩阵一致）；派生量在 Q2 的报告
    # 环节被剔除（它们不是独立化合物），但在拟合阶段保留以吸收共线
    feats = [c for c in c1.columns[3:]]
    sens = [c for c in c4.columns[3:]]

    wb = openpyxl.load_workbook(os.path.join(DATA, '8.xlsx'), read_only=True, data_only=True)
    rows = list(wb['Sensory thresholds'].iter_rows(values_only=True))
    wb.close()
    th = pd.DataFrame(rows[1:], columns=list(rows[0]))
    th['key'] = th['field_name_R'].map(norm_key)
    th = th.drop_duplicates('key').set_index('key')

    grp, thr = {}, {}
    for f in feats:
        k = norm_key(f)
        if k in th.index:
            g = th.at[k, 'origin_paper']
            grp[f] = str(g) if pd.notna(g) else 'Others'
            t = pd.to_numeric(th.at[k, 'threshold_mean'], errors='coerce')
            if pd.notna(t) and float(t) > 0:
                thr[f] = float(t)
        else:
            grp[f] = 'Others'

    X = c1.set_index('beer')[feats].apply(pd.to_numeric, errors='coerce')
    Y = c4.set_index('beer')[sens].apply(pd.to_numeric, errors='coerce')
    style = c1.set_index('beer')['tasting_category_fine']
    idx = X.index.intersection(Y.index).intersection(style.index)
    return (X.loc[idx], Y.loc[idx], style.loc[idx], feats, sens, grp, thr)


def select_decision_features(feats, grp):
    """按 Q2 的 Top-3 归因收缩决策列。这是 Q2 → Q3 的真实依赖，不是随意剪枝。"""
    path = os.path.join(RES, 'q2_top3.csv')
    if not os.path.exists(path):
        raise SystemExit('缺少 results/q2_top3.csv —— 请先跑 q2.py')
    t3 = pd.read_csv(path)
    informed = set(t3.feat.astype(str))
    base = set(K_HARD) | set(K_SOFT)
    cand = [f for f in feats
            if f not in PHYSICOCHEM and f not in DERIVED
            and grp[f] not in NON_AROMA_GROUPS]
    sel = [f for f in cand if (f in informed) or (f in base)]
    must = [f for f in base if f in cand and f not in sel]
    sel = sel + must
    return sel, dict(n_informed=len(informed), n_cand=len(cand))


# ============================================================ ① 收缩高斯
def fit_generator(Xs, rng, n_gen):
    from sklearn.covariance import ledoit_wolf
    n, p = Xs.shape
    mu = Xs.mean(axis=0)
    if n < 3:
        cov, shrink = np.eye(p) * np.var(Xs, axis=0).mean(), np.nan
    else:
        cov, shrink = ledoit_wolf(Xs, assume_centered=False)
    cov = np.atleast_2d(cov)
    cov = 0.5 * (cov + cov.T)
    cov = cov + np.eye(p) * (np.trace(cov) / max(p, 1) * 1e-8 + 1e-12)
    gen = rng.multivariate_normal(mu, cov, size=n_gen, method='eigh')
    return mu, cov, shrink, gen


def novelty_check(gen, Xs):
    from sklearn.neighbors import NearestNeighbors
    d_gen, _ = NearestNeighbors(n_neighbors=1).fit(Xs).kneighbors(gen)
    d_self = np.sort(NearestNeighbors(n_neighbors=2).fit(Xs).kneighbors(Xs)[0][:, 1])
    return dict(
        gen_nn_dist_median=round(float(np.median(d_gen)), 4),
        real_nn_dist_median=round(float(np.median(d_self)), 4),
        ratio=round(float(np.median(d_gen) / max(np.median(d_self), 1e-9)), 3),
        frac_gen_below_real_median=round(float((d_gen[:, 0] < np.median(d_self)).mean()), 3),
    )


# ============================================================ ② PLS 代理
def fit_pls_surrogate(X, Y, grid=PLSR_GRID, cv=5, seed=SEED):
    """PLS 回归，成分数由 K 折交叉验证选。返回 (C, B, k_best, cv_r2_per_target)。"""
    from sklearn.cross_decomposition import PLSRegression
    from sklearn.model_selection import KFold
    kf = KFold(n_splits=cv, shuffle=True, random_state=seed)
    best = (np.inf, grid[0])
    for k in grid:
        if k > min(X.shape) - 1:
            continue
        mse = 0.0
        for tr, te in kf.split(X):
            m = PLSRegression(n_components=k, scale=True)
            m.fit(X[tr], Y[tr])
            mse += float(np.mean((Y[te] - m.predict(X[te])) ** 2))
        mse /= cv
        if mse < best[0]:
            best = (mse, k)
    k_best = best[1]
    m = PLSRegression(n_components=k_best, scale=True).fit(X, Y)
    # sklearn 的 PLSRegression.coef_ 在多目标时为 (n_targets, n_features)，
    # 正是我们要的 B（感官 × 化合物），不要转置。
    B = np.asarray(m.coef_, dtype=float)
    if B.shape != (Y.shape[1], X.shape[1]):
        raise RuntimeError(f'PLS coef_ 形状异常：{B.shape}，期望 {(Y.shape[1], X.shape[1])}')
    C = np.asarray(m.intercept_, dtype=float).ravel()

    # 逐靶交叉验证 R²
    pred = np.zeros_like(Y, dtype=float)
    for tr, te in kf.split(X):
        mm = PLSRegression(n_components=k_best, scale=True).fit(X[tr], Y[tr])
        pred[te] = mm.predict(X[te])
    ss = ((Y - Y.mean(0)) ** 2).sum(0)
    cv_r2 = 1.0 - ((Y - pred) ** 2).sum(0) / np.maximum(ss, 1e-12)
    return C, B, int(k_best), cv_r2, float(best[0])


def surrogate_error_bound(C, B, lb, ub, tree_predict, rng, n=N_MC_BOUND):
    """B 的形状统一为 (n_target, n_feature)，与 build_arrays 中的 B @ x0 一致。"""
    p = len(lb)
    T = lb[None, :] + rng.random((n, p)) * (ub - lb)[None, :]
    return np.abs((C[None, :] + T @ B.T) - tree_predict(T))


# ============================================================ ③ MILP 装配
def build_arrays(n, ns, kh_idx, ks_idx, x0, lb, ub, targ, B, C, w,
                 gamma, lam, hard_cap, soft_thr, kmax,
                 e_f2=np.inf, e_f3=np.inf, sens_ub=None):
    """把 MILP 写成通用矩阵形式（Gurobi 与 HiGHS 共用同一份定义）。

    变量顺序： dp[n) | dn[n) | y[n) | up[ns) | um[ns) | z[nk)

    sens_ub: 可选，[(感官维下标, 上界)] —— 追加"代理预测值不恶化"型约束
        base_s + Σ_j B_sj (dp_j − dn_j) ≤ cap
    必须写成 build_arrays 的**参数**而不是外部给 A_ub 追加行：augmecon2 在 ε 网格
    循环里会重新调用本函数，外挂的行会被丢掉（实测 stale_hops 因此恶化 +0.053）。
    """
    nk = len(ks_idx)
    nv = 3 * n + 2 * ns + nk
    i_dp, i_dn, i_y = 0, n, 2 * n
    i_up, i_um = 3 * n, 3 * n + ns
    i_z = 3 * n + 2 * ns

    span = np.maximum(ub - lb, 1e-9)
    # wj = 1/可行域宽度：把 dp/dn 折算成"占可行域的比例"。
    # 必要性：决策列并非同域——X2.methyltetrahydrofuran.3.one 与
    # X2.3.butanedione 是线性浓度（宽 29.1 与 87.5），其余是 log10
    # 浓度（宽约 6.9）。若 f3=Σ|x−x0| 直接相加，等于把线性列的
    # 浓度差和 log10 列的对数差混在一个量纲里，f3 会被前两列支配。
    # **必须在 build_arrays 里定义一次、三处共用**（ε3 约束、默认目标、
    # metrics_of），否则约束与指标的 f3 不是同一把尺子：
    # 实测过约束用未加权 lam 时 e_f3=10.2245 而 f3=7.4510。
    wj = 1.0 / span
    M = np.maximum.reduce([np.abs(ub - x0), np.abs(x0 - lb)])
    M = np.maximum(M, 1e-6)
    # z 的上界必须取"变量上下界内**物理可达**的最大违反量"，不能用一个拍脑袋的
    # 大常数（初版取 2·span_max+10，使 payoff 表的 f2 上界跑到 185，
    # 而真实可达最大违反只有 ub−θ ≈ 2 —— ε 网格整个浪费在无约束区间上）。
    z_max = np.array([max(0.0, float(ub[j] - soft_thr[k])) + 1e-6
                      for k, j in enumerate(ks_idx)], dtype=float)
    if z_max.size == 0:
        z_max = np.zeros(0)

    rows, cols, vals, rhs = [], [], [], []
    r = 0

    def add(ri, ci, v):
        rows.append(ri); cols.append(ci); vals.append(v)

    # (1) 上界  x0 + dp - dn <= ub
    for j in range(n):
        add(r, i_dp + j, 1.0); add(r, i_dn + j, -1.0)
        rhs.append(ub[j] - x0[j]); r += 1
    # (2) 下界  x0 + dp - dn >= lb
    for j in range(n):
        add(r, i_dn + j, 1.0); add(r, i_dp + j, -1.0)
        rhs.append(x0[j] - lb[j]); r += 1
    # (3) big-M 稀疏化
    for j in range(n):
        add(r, i_dp + j, 1.0); add(r, i_y + j, -M[j]); rhs.append(0.0); r += 1
        add(r, i_dn + j, 1.0); add(r, i_y + j, -M[j]); rhs.append(0.0); r += 1
    # (4) 感官偏差
    #     pred_s = base_s + Σ_j B_sj (dp_j − dn_j)，要求 up_s − um_s = targ_s − pred_s
    #     ⇒ up − um + Σ_j B_sj (dp_j − dn_j) = targ_s − base_s
    # 这是**等式**，必须写成正反两行（<= 与 >=）。只写一行 <= 时，求解器可以取
    # up=um=0 直接满足不等式，f1 便与真实偏差脱钩（实测 solver_obj 4.36 vs 真实 38.16）。
    # 系数符号是 **+B**：写成 −B 会最小化 |targ − base + BΔ|，同样与 |targ − pred| 不符。
    base = C + B @ x0
    for sign in (+1.0, -1.0):
        for s in range(ns):
            add(r, i_up + s, sign); add(r, i_um + s, -sign)
            for j in range(n):
                if B[s, j] != 0.0:
                    add(r, i_dp + j, sign * B[s, j])
                    add(r, i_dn + j, -sign * B[s, j])
            rhs.append(sign * (targ[s] - base[s])); r += 1
    # (5) 硬约束
    for k, j in enumerate(kh_idx):
        add(r, i_dp + j, 1.0); add(r, i_dn + j, -1.0)
        rhs.append(hard_cap[k] - x0[j]); r += 1
    # (6) 软约束  z >= (x0 + dp - dn) - log10θ
    for k, j in enumerate(ks_idx):
        add(r, i_dp + j, 1.0); add(r, i_dn + j, -1.0); add(r, i_z + k, -1.0)
        rhs.append(soft_thr[k] - x0[j]); r += 1
    # (7) 基数约束 Σ y <= K_MAX
    for j in range(n):
        add(r, i_y + j, 1.0)
    rhs.append(float(kmax)); r += 1
    # (6b) 感官非恶化约束  base_s + Σ_j B_sj (dp_j − dn_j) ≤ cap
    if sens_ub:
        for s_idx, cap in sens_ub:
            for j in range(n):
                if B[s_idx, j] != 0.0:
                    add(r, i_dp + j, B[s_idx, j])
                    add(r, i_dn + j, -B[s_idx, j])
            rhs.append(float(cap) - float(base[s_idx])); r += 1
    # (8) ε-约束
    if np.isfinite(e_f2):
        for k in range(nk):
            add(r, i_z + k, 1.0)
        rhs.append(e_f2); r += 1
    if np.isfinite(e_f3):
        for j in range(n):
            add(r, i_y + j, gamma)
            # 加权必须与 metrics_of / _obj_vec 一致：三处都用 lam*wj，
            # 否则 ε-约束的上界与报告的 f3 不是同一把尺子。
            add(r, i_dp + j, lam * wj[j]); add(r, i_dn + j, lam * wj[j])
        rhs.append(e_f3); r += 1

    A_ub = sp.csr_matrix((vals, (rows, cols)), shape=(r, nv))
    b_ub = np.array(rhs, dtype=float)

    c = np.zeros(nv)
    c[i_up:i_up + ns] = w
    c[i_um:i_um + ns] = w
    c[i_y:i_y + n] = gamma
    # f3 的幅度项必须按 wj 归一，与 ε3 约束、metrics_of、_obj_vec 完全一致。
    # 这四处原先有三处带 wj、一处不带，导致「求解的目标」和「报告的指标」不是
    # 同一个 f3（实测 e_f3=10.2245 vs f3=7.4510）。
    c[i_dp:i_dp + n] = lam * wj
    c[i_dn:i_dn + n] = lam * wj

    bounds = ([(0.0, M[j]) for j in range(n)] +
              [(0.0, M[j]) for j in range(n)] +
              [(0.0, 1.0)] * n +
              [(0.0, np.inf)] * (2 * ns) +
              [(0.0, float(z_max[k])) for k in range(nk)])
    integrality = np.zeros(nv, dtype=int)
    integrality[i_y:i_y + n] = 1

    return dict(c=c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, integrality=integrality,
                nv=nv, n=n, ns=ns, nk=nk, base=base,
                # wj 在函数开头定义，ε3 约束、默认目标 c、metrics_of 三处共用
                wj=wj,
                idx=dict(dp=i_dp, dn=i_dn, y=i_y, up=i_up, um=i_um, z=i_z))


def solve_milp(arr, obj_override=None, solver='auto', log_prefix=''):
    c = arr['c'] if obj_override is None else obj_override
    use_grb = have_gurobi() and solver in ('auto', 'gurobi')

    if use_grb:
        import gurobipy as gp
        m = gp.Model('q3')
        m.Params.OutputFlag = 0
        m.Params.MIPGap = MIP_GAP
        m.Params.TimeLimit = TIME_LIMIT
        m.Params.MIPFocus = 1
        nv = arr['nv']
        lob = [b[0] for b in arr['bounds']]
        upb = [b[1] if np.isfinite(b[1]) else gp.GRB.INFINITY for b in arr['bounds']]
        vt = [gp.GRB.BINARY if arr['integrality'][i] else gp.GRB.CONTINUOUS
              for i in range(nv)]
        xv = m.addVars(nv, lb=lob, ub=upb, vtype=vt)
        A = arr['A_ub'].tocsr()
        for i in range(A.shape[0]):
            lo, hi = A.indptr[i], A.indptr[i + 1]
            if lo == hi:
                continue
            m.addConstr(gp.quicksum(A.data[k] * xv[A.indices[k]] for k in range(lo, hi))
                        <= arr['b_ub'][i])
        nz = np.flatnonzero(c)
        m.setObjective(gp.quicksum(float(c[i]) * xv[int(i)] for i in nz), gp.GRB.MINIMIZE)
        m.optimize()
        st = m.Status
        names = {2: 'OPTIMAL', 3: 'INFEASIBLE', 4: 'INF_OR_UNBD', 5: 'UNBOUNDED',
                 9: 'TIME_LIMIT', 11: 'INTERRUPTED'}
        out = dict(backend='gurobi', status=int(st), status_name=names.get(st, str(st)),
                   obj=float(m.ObjVal) if m.SolCount > 0 else np.nan,
                   x=np.array([xv[i].X for i in range(nv)]) if m.SolCount > 0 else None,
                   gap=float(m.MIPGap) if m.SolCount > 0 and m.IsMIP else np.nan,
                   runtime=float(m.Runtime), nvars=int(m.NumVars),
                   nbin=int(m.NumBinVars), nconstr=int(m.NumConstrs))
        if st in (3, 4):
            try:
                m.computeIIS()
                out['iis_rows'] = int(sum(1 for cc in m.getConstrs() if cc.IISConstr))
            except Exception:
                out['iis_rows'] = None
        m.dispose()
        return out

    from scipy.optimize import milp, LinearConstraint, Bounds
    res = milp(c=c, constraints=LinearConstraint(arr['A_ub'], -np.inf, arr['b_ub']),
               integrality=arr['integrality'],
               bounds=Bounds([b[0] for b in arr['bounds']],
                             [b[1] for b in arr['bounds']]),
               options=dict(mip_rel_gap=MIP_GAP, time_limit=TIME_LIMIT, disp=False))
    nm = {0: 'OPTIMAL', 1: 'TIME_LIMIT', 2: 'INFEASIBLE', 3: 'UNBOUNDED', 4: 'OTHER'}
    return dict(backend='highs', status=int(res.status),
                status_name=nm.get(int(res.status), str(res.status)),
                obj=float(res.fun) if res.x is not None else np.nan,
                x=res.x, gap=float(getattr(res, 'mip_gap', np.nan) or np.nan),
                runtime=np.nan, nvars=int(arr['nv']),
                nbin=int(arr['integrality'].sum()), nconstr=int(arr['A_ub'].shape[0]))


# ============================================================ ④ AUGMECON2
def metrics_of(x, arr, B, x0, targ, w, gamma, lam, kh_idx, ks_idx, hard_cap):
    ix = arr['idx']
    n, ns, nk = arr['n'], arr['ns'], arr['nk']
    dp = x[ix['dp']:ix['dp'] + n]
    dn = x[ix['dn']:ix['dn'] + n]
    y = x[ix['y']:ix['y'] + n]
    z = x[ix['z']:ix['z'] + nk]
    t = x0 + dp - dn
    pred = arr['base'] + (B @ (t - x0))
    f1 = float(np.sum(w * np.abs(pred - targ)))
    f2 = float(np.sum(z))
    f3 = float(gamma * np.sum(y) + lam * np.sum(arr['wj'] * (dp + dn)))
    margins = [float(t[j] - hard_cap[k]) for k, j in enumerate(kh_idx)]
    return dict(f1=f1, f2=f2, f3=f3, t=t, y=y, dp=dp, dn=dn, z=z, margins=margins)


def _obj_vec(arr, name, w, gamma, lam):
    ix = arr['idx']
    n, ns, nk = arr['n'], arr['ns'], arr['nk']
    c = np.zeros(arr['nv'])
    if name == 'f1':
        c[ix['up']:ix['up'] + ns] = w
        c[ix['um']:ix['um'] + ns] = w
    elif name == 'f2':
        c[ix['z']:ix['z'] + nk] = 1.0
    else:
        c[ix['y']:ix['y'] + n] = gamma
        # dp/dn 按可行域宽度归一，理由见 build_arrays 里 wj 的说明
        c[ix['dp']:ix['dp'] + n] = lam * arr['wj']
        c[ix['dn']:ix['dn'] + n] = lam * arr['wj']
    return c


def payoff_table(arr, B, x0, targ, w, gamma, lam, kh_idx, ks_idx, hard_cap, solver, log):
    pay = {}
    for name in ('f1', 'f2', 'f3'):
        r = solve_milp(arr, obj_override=_obj_vec(arr, name, w, gamma, lam), solver=solver)
        if r['x'] is None:
            log(f'  payoff min {name}: {r["status_name"]}（该单目标不可行）')
            pay[name] = None
            continue
        met = metrics_of(r['x'], arr, B, x0, targ, w, gamma, lam, kh_idx, ks_idx, hard_cap)
        pay[name] = met
        log(f'  payoff min {name} = {met[name]:.4f}  [{r["backend"]} {r["status_name"]} '
            f'{r["runtime"]:.2f}s]  (f1={met["f1"]:.4f}, f2={met["f2"]:.4f}, f3={met["f3"]:.2f})')
    return pay


def augmecon2(arr, B, x0, targ, w, gamma, lam, kh_idx, ks_idx, hard_cap, soft_thr,
              kmax, n2, n3, solver, log, sens_ub=None):
    pay = payoff_table(arr, B, x0, targ, w, gamma, lam, kh_idx, ks_idx, hard_cap, solver, log)
    valid = [v for v in pay.values() if v is not None]
    if not valid:
        return [], dict(payoff={})
    f2s = [v['f2'] for v in valid]
    f3s = [v['f3'] for v in valid]
    f2_lo, f2_hi = min(f2s), max(f2s)
    f3_lo, f3_hi = min(f3s), max(f3s)
    n2s = max(f2_hi - f2_lo, 1e-6)
    n3s = max(f3_hi - f3_lo, 1e-6)
    log(f'  payoff 范围： f2 ∈ [{f2_lo:.4f}, {f2_hi:.4f}]，f3 ∈ [{f3_lo:.2f}, {f3_hi:.2f}]')
    log(f'  payoff min f1 时的改动列数 = '
        f'{int(pay["f1"]["y"].sum()) if pay.get("f1") else "n/a"}（K_MAX={kmax}）')

    e2_grid = np.linspace(f2_lo, f2_hi, n2)
    e3_grid = np.linspace(f3_lo, f3_hi, n3)

    c_aug = arr['c'].copy()
    ix = arr['idx']
    n, nk = arr['n'], arr['nk']
    c_aug[ix['z']:ix['z'] + nk] += EPS_AUG / n2s
    c_aug[ix['y']:ix['y'] + n] += EPS_AUG * 0.1 / n3s * gamma
    # 增广项也按 wj 归一，否则它和 c 里的 f3 项量纲不同，ε 网格的平局打破会偏向线性列
    c_aug[ix['dp']:ix['dp'] + n] += EPS_AUG * 0.1 / n3s * lam * arr['wj']
    c_aug[ix['dn']:ix['dn'] + n] += EPS_AUG * 0.1 / n3s * lam * arr['wj']

    pts, n_solve, n_infeas = [], 0, 0
    for e2 in e2_grid:
        for e3 in e3_grid:
            a = build_arrays(n, arr['ns'], kh_idx, ks_idx, x0, arr['_lb'], arr['_ub'],
                             targ, B, arr['_C'], w, gamma, lam, hard_cap, soft_thr,
                             kmax, e_f2=float(e2), e_f3=float(e3),
                             sens_ub=sens_ub)
            r = solve_milp(a, obj_override=c_aug, solver=solver)
            n_solve += 1
            if r['x'] is None:
                n_infeas += 1
                continue
            met = metrics_of(r['x'], a, B, x0, targ, w, gamma, lam, kh_idx, ks_idx, hard_cap)
            met.update(e_f2=float(e2), e_f3=float(e3), backend=r['backend'],
                       status_name=r['status_name'], solver_obj=r['obj'],
                       gap=r['gap'], runtime=r['runtime'], nvars=r['nvars'],
                       nbin=r['nbin'], nconstr=r['nconstr'])
            pts.append(met)
        log(f'  ε_f2={e2:.4f} 扫完：累计可行 {len(pts)}，不可行 {n_infeas}（已求解 {n_solve}）')

    info = dict(payoff={k: (None if v is None else
                            {m: round(float(v[m]), 6) for m in ('f1', 'f2', 'f3')})
                        for k, v in pay.items()},
                f2_range=[float(f2_lo), float(f2_hi)],
                f3_range=[float(f3_lo), float(f3_hi)],
                n_solve=n_solve, n_infeasible=n_infeas,
                payoff_min_f1_changed=int(pay['f1']['y'].sum()) if pay.get('f1') else None)
    return pts, info


# ============================================================ ⑤ 指标
def mc_hypervolume(pts, ref, n=N_MC_HV, seed=SEED):
    p = np.atleast_2d(np.asarray(pts, dtype=float))
    ref = np.asarray(ref, dtype=float)
    m = p.shape[1]
    lo = p.min(axis=0)
    span = ref - lo
    if np.any(span <= 0):
        return float('nan')
    rng = np.random.default_rng(seed)
    U = lo + rng.random((n, m)) * span[None, :]
    dom = (p[:, None, :] <= U[None, :, :]).all(-1).any(axis=0)
    return float(dom.mean() * float(np.prod(span)))


def normalized_min_dist(A, Bm, scale=None):
    """A 中每点到 Bm 的归一化最近距离。

    scale 默认取**两个集合合并后**各目标维的跨度（而不是只用 Bm 的跨度）：
    否则当一方在某维上恰好只有一个取值时跨度为 0，归一化会炸成 1e8。
    """
    A = np.atleast_2d(A); Bm = np.atleast_2d(Bm)
    both = np.vstack([A, Bm])
    if scale is None:
        scale = np.maximum(both.max(axis=0) - both.min(axis=0), 1e-9)
    scale = np.asarray(scale, dtype=float)
    d = np.sqrt((((A[:, None, :] - Bm[None, :, :]) / scale[None, None, :]) ** 2).sum(-1))
    return float(np.mean(d.min(axis=1)))


# ============================================================ 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--style', default='Tripel')
    ap.add_argument('--grid', nargs=2, type=int, default=[20, 15])
    ap.add_argument('--kmax', type=int, default=K_MAX)
    ap.add_argument('--solver', default='auto', choices=['auto', 'gurobi', 'highs'])
    ap.add_argument('--n-gen', type=int, default=200)
    ap.add_argument('--nsga-pop', type=int, default=80)
    ap.add_argument('--nsga-gen', type=int, default=150)
    ap.add_argument('--smoke', action='store_true')
    args = ap.parse_args()
    if args.smoke:
        args.grid = [2, 2]; args.nsga_pop = 16; args.nsga_gen = 12
    # --smoke 只缩网格/种群，但原先直接覆盖正式结果文件。
    # 加后缀隔离，避免冒烟跑完后 results/q3_pareto.csv 变成 3 行、
    # 与论文里"7 个 Pareto 点"的说法对不上（曾实际发生）。
    suffix = '_smoke' if args.smoke else ''

    t0 = time.perf_counter()
    print('=' * 90)
    print('Q3 · 收缩高斯生成 + PLS 代理 + AUGMECON2 ε-约束 MILP + NSGA-II 互证')
    print('    目标风格 %s | 干预预算 K_MAX=%d | ε 网格 %d×%d | 求解器 %s'
          % (args.style, args.kmax, args.grid[0], args.grid[1],
             args.solver + ('（gurobipy 可用）' if have_gurobi() else '（将回退 HiGHS）')))
    print('=' * 90)

    X, Y, style, feats, sens, grp, thr = load()
    rng = np.random.default_rng(SEED)
    ns = len(sens)

    mask = (style == args.style).to_numpy()
    n_style = int(mask.sum())
    print(f'样本 {len(X)} | 特征 {len(feats)} | 感官 {ns} | 风格 {args.style} n={n_style}'
          + ('  ⚠ 小样本类，生成结论须限定' if n_style < 10 else ''))

    # ---- 决策列：按 Q2 归因收缩 ----
    sel, selinfo = select_decision_features(feats, grp)
    n = len(sel)
    print(f'决策列 {n}（Q2 归因并集 {selinfo["n_informed"]} ∩ 可调香气候选 '
          f'{selinfo["n_cand"]}，另并入硬/软约束化合物）')
    print(f'  感官约束 {ns} 条 vs 决策变量 {n} 个 → '
          + ('n < n_s，f1 不会恒为 0 ✓' if n < ns else
             f'⚠ n ≥ n_s（{n} ≥ {ns}），需靠基数约束 K_MAX={args.kmax} 维持非退化'))

    Xv = X[sel].to_numpy(float)
    medx = np.nanmedian(Xv, axis=0)
    Xv = np.where(np.isfinite(Xv), Xv, medx[None, :])
    Yv = Y.to_numpy(float)
    medy = np.nanmedian(Yv, axis=0)
    # 注意 np.where 的参数顺序：第三个参数才是"取值不满足条件时"用的替代值。
    # 写成 np.where(isfinite, 中位数, Yv) 会把所有真实观测替换成中位数，
    # 使每个感官列变成常数 —— 那样 PLS 的 CV R² 会假性等于 1.0000、f1 恒为 0。
    Yv = np.where(np.isfinite(Yv), Yv, medy[None, :])
    assert Yv.std(axis=0).min() > 0, '感官矩阵存在常数列，检查缺失插补是否写反'

    # ---- ① 生成 ----
    x0 = np.median(Xv[mask], axis=0)
    lb = np.percentile(Xv, 1, axis=0)
    ub = np.percentile(Xv, 99, axis=0)
    x0 = np.clip(x0, lb, ub)
    fixed = (ub - lb) < 1e-3
    # ⚠ 关键：把训练数据裁到 MILP 的可行域 [lb, ub]（即 1%/99% 分位）。
    # 依据：搜索空间本来就被这个盒子限死，盒子外的样本对代理只起杠杆点作用。
    # 实测后果：X2.methyltetrahydrofuran.3.one 是线性浓度列（min 0、max 12596、
    # 无负值，与附件8 Calibrated 表逐值一致），混在 log10 域的决策列里，
    # 单列 std 795 而其余约 3.5，PLS 的协方差被它独占 → 成分数塌到 2、
    # CV R² 中位 −0.7528、50 维中仅 4 维为正。裁剪后 std 降到 4.12，
    # 成分数回到 8、CV R² 中位 +0.1386、47/50 维为正。
    n_clip = int((np.abs(Xv - np.clip(Xv, lb, ub)) > 1e-12).sum())
    Xv = np.clip(Xv, lb, ub)
    print(f'\n   代理训练集裁到可行域：{n_clip} 个格被裁（占 '
          f'{100 * n_clip / Xv.size:.2f}%）')
    mu_s, cov_s, shrink_s, gen = fit_generator(Xv[mask], rng, args.n_gen)
    gen = np.clip(gen, lb, ub)
    nov = novelty_check(gen, Xv[mask])
    print(f'\n① 收缩高斯：Ledoit-Wolf 收缩 {shrink_s:.4f}（n={n_style}）'
          f' | 不可动列 {int(fixed.sum())}')
    print(f'   新颖性：生成→真实最近邻距离中位 {nov["gen_nn_dist_median"]:.3f}，'
          f'真实→真实 {nov["real_nn_dist_median"]:.3f}，比值 {nov["ratio"]}'
          f'（比值≈1 = 既非复制也非离群）')

    # ---- ② PLS 代理 ----
    C, B, k_best, cv_r2, cv_mse = fit_pls_surrogate(Xv, Yv)
    sd = Yv.std(axis=0)
    sd = np.where(sd > 1e-9, sd, 1.0)
    w = 1.0 / sd
    Targ = np.median(Yv[mask], axis=0)

    from q1_helpers import fit_tree_for_surrogate, predict_tree
    trees = fit_tree_for_surrogate(Xv, Yv, seed=SEED)
    err = surrogate_error_bound(C, B, lb, ub, lambda T: predict_tree(trees, T), rng)
    err_sd = err / sd[None, :]
    print(f'\n② PLS 代理：成分数 {k_best}（5 折 CV 选，网格 {PLSR_GRID}）')
    print(f'   交叉验证 R²：中位 {np.median(cv_r2):.4f}，最好 {np.max(cv_r2):.4f}，'
          f'最差 {np.min(cv_r2):.4f}，为正的靶 {int((cv_r2 > 0).sum())}/{ns}')
    print(f'   可行域蒙特卡洛（{N_MC_BOUND} 点）PLS vs LightGBM 偏差：'
          f'中位 {np.median(err):.3f}、p95 {np.percentile(err, 95):.3f}、'
          f'最大 {err.max():.3f}；折合 sd 单位最大 {np.median(err_sd.max(0)):.3f}')

    sur = pd.DataFrame(dict(
        sens=sens, cv_r2=np.round(cv_r2, 4), y_sd=np.round(sd, 4),
        err_median=np.round(np.median(err, axis=0), 4),
        err_p95=np.round(np.percentile(err, 95, axis=0), 4),
        err_max=np.round(err.max(axis=0), 4),
        err_max_over_sd=np.round(err.max(axis=0) / sd, 4)))
    sur.to_csv(os.path.join(RES, f'q3_surrogate{suffix}.csv'), index=False, encoding='utf-8-sig')

    # ---- 硬/软约束 ----
    # ⚠ 单位域必须逐列判定：附件1 里 DMS/X4VG 在 log10 域，而双乙酰/trans-2-壬烯醛
    #   **在线性域**（实测见 q0_floor_share.csv 的 is_log10 列，并经附件8 Calibrated
    #   表交叉验证）。原实现一律取 np.log10(threshold)，对线性域列等于拿 −0.524
    #   去比 0.285，软约束恒为常数 0.524、完全不生效（f2 退化成常数）。
    is_log10 = _load_is_log10()
    kh_idx = [sel.index(k) for k in K_HARD if k in sel]
    ks_idx = [sel.index(k) for k in K_SOFT if k in sel]

    def thr_in_domain(f):
        """把香气阈值换算到该列在附件1 中的实际量纲域。"""
        t = float(thr[f])
        return float(np.log10(t)) if is_log10.get(f, True) else t

    hard_cap = [min(thr_in_domain(sel[j]), x0[j]) for j in kh_idx]
    soft_thr = [thr_in_domain(sel[j]) for j in ks_idx]
    print(f'\n   硬约束 {[sel[j] for j in kh_idx]}：'
          + '；'.join(f'θ={thr[sel[j]]:.4g}（'
                      f'{"log10 域" if is_log10.get(sel[j], True) else "线性域"}'
                      f'→{thr_in_domain(sel[j]):.4f}），'
                      f'cap={hard_cap[k]:.4f}（取 min(θ, 当前 {x0[j]:.4f})）'
                      for k, j in enumerate(kh_idx)))
    print(f'   软约束 {[sel[j] for j in ks_idx]}：'
          + '；'.join(f'θ={thr[sel[j]]:.4g}（'
                      f'{"log10 域" if is_log10.get(sel[j], True) else "线性域"}'
                      f'→{thr_in_domain(sel[j]):.4f}）'
                      for j in ks_idx))

    # ---- ③④ MILP + AUGMECON2 ----
    arr0 = build_arrays(n, ns, kh_idx, ks_idx, x0, lb, ub, Targ, B, C, w,
                        GAMMA, LAMBDA, hard_cap, soft_thr, args.kmax)
    arr0.update(_lb=lb, _ub=ub, _C=C)
    print(f'\n④ MILP 规模：{arr0["nv"]} 变量 / {int(arr0["integrality"].sum())} 二值 / '
          f'{arr0["A_ub"].shape[0]} 约束行')
    pts, payinfo = augmecon2(arr0, B, x0, Targ, w, GAMMA, LAMBDA, kh_idx, ks_idx,
                             hard_cap, soft_thr, args.kmax,
                             args.grid[0], args.grid[1], args.solver, print)

    base_f1 = float(np.sum(w * np.abs(C + B @ x0 - Targ)))
    base_margins = [float(x0[j] - hard_cap[k]) for k, j in enumerate(kh_idx)]
    print(f'\n   基线 x=0（什么都不改）：f1={base_f1:.4f}，f2=0，f3=0，'
          f'硬约束余量 {[round(v, 4) for v in base_margins]}')

    if not pts:
        print('!! 所有 ε 格点均无可行解 —— 检查 payoff 与约束（见 IIS）')
        return 1

    Obj = np.array([[q['f1'], q['f2'], q['f3']] for q in pts])
    pm = pareto_mask(Obj)
    nd = [q for q, k in zip(pts, pm) if k]
    seen, uniq = set(), []
    for q in nd:
        key = (round(q['f1'], 6), round(q['f2'], 6), round(q['f3'], 6))
        if key in seen:
            continue
        seen.add(key); uniq.append(q)
    uniq.sort(key=lambda q: (q['f1'], q['f3']))
    print(f'   ε 格点可行解 {len(pts)} → 非支配 {int(pm.sum())} → 去重 {len(uniq)} 个 Pareto 点')

    print('\n' + '-' * 90)
    print('验收 1–3：可行性 / 最优性凭证 / 非支配性')
    ok_all = True
    for i, q in enumerate(uniq, 1):
        feas = all(v <= 1e-7 for v in q['margins'])
        others = np.array([[r['f1'], r['f2'], r['f3']] for r in uniq if r is not q])
        src = np.array([q['f1'], q['f2'], q['f3']])
        dominated = bool(others.size and ((others <= src).all(1) & (others < src).any(1)).any())
        ok_all &= feas and not dominated
        print(f'  P{i:<2} f1={q["f1"]:.4f} f2={q["f2"]:.4f} f3={q["f3"]:5.2f} '
              f'改{int(q["y"].sum()):>2}列 | 硬余量 '
              f'{[f"{v:+.1e}" for v in q["margins"]]} {"✓" if feas else "✗"} | '
              f'{q["status_name"]} gap={q["gap"]:.1e} {q["runtime"]:.2f}s '
              f'[{q["backend"]}] | {"✓非支配" if not dominated else "✗被支配"}')
    print(f'  基线 f1={base_f1:.4f} 对照：'
          f'最好点 f1={min(q["f1"] for q in uniq):.4f} '
          f'({100 * (1 - min(q["f1"] for q in uniq) / max(base_f1, 1e-12)):.1f}% 改善)')

    # ---- ⑤ NSGA-II ----
    print(f'\n⑤ NSGA-II 互证（SBX η=15 + PM η=20，染色体 {n} 维，'
          f'种群 {args.nsga_pop}×{args.nsga_gen} 代，delta=0 播种）')

    def objective(delta):
        t = np.clip(x0 + delta, lb, ub)
        pred = C + B @ t
        f1 = float(np.sum(w * np.abs(pred - Targ)))
        viol = sum(max(0.0, float(t[j] - hard_cap[k])) for k, j in enumerate(kh_idx))
        f2v = sum(max(0.0, float(t[j] - soft_thr[k])) for k, j in enumerate(ks_idx))
        changed = int((np.abs(t - x0) > 1e-9).sum())
        f3 = float(GAMMA * changed + LAMBDA * np.abs(t - x0).sum())
        viol += max(0, changed - args.kmax) * 10.0     # 基数为软违约，权重 10
        return (f1, f2v, f3), viol

    # 初始种群：delta=0 本身**不可行**（风格参考谱的 DMS 高于阈值，
    # 见下方 print），所以不能只播种 0。用"把硬约束列推到 cap"的领域修复做种子——
    # 这是问题结构驱动的初始化，不读 MILP 的输出，互证仍然独立。
    seed0 = np.zeros(n)
    seed_rows = [seed0.copy()]
    repaired = seed0.copy()
    for k, j in enumerate(kh_idx):
        repaired[j] = min(hard_cap[k], ub[j]) - x0[j]
    seed_rows.append(repaired)
    for _ in range(max(1, args.nsga_pop // 4)):
        pert = repaired + rng.normal(0, 0.05, n) * (ub - lb)
        seed_rows.append(np.clip(pert, lb - x0, ub - x0))
    init = np.vstack(seed_rows)
    print(f'   初始种子 {len(init)} 个：delta=0（对硬约束不可行）+ 硬约束修复 + 邻域扰动')

    r_hist = nsga2(objective, n_var=n, lb=lb - x0, ub=ub - x0,
                   pop_size=args.nsga_pop, n_gen=args.nsga_gen, seed=SEED,
                   archive_cap=400, init_pop=init,
                   log=lambda s: print(s))
    arch = r_hist['archive']
    feas_arch = [a for a in arch if a['feas']]
    hobj = np.array([a['obj'] for a in feas_arch]) if feas_arch else np.zeros((0, 3))
    print(f'   存档 {len(arch)}，可行 {len(feas_arch)}，评价 {r_hist["stats"]["n_eval"]} 次')

    eobj = np.array([[q['f1'], q['f2'], q['f3']] for q in uniq])
    cmp = dict(n_exact=len(eobj), n_heur=len(hobj))
    if len(hobj):
        cov = dominance_coverage(eobj, hobj)
        cmp.update(cov)
        ref = np.maximum(eobj.max(0), hobj.max(0)) * 1.1
        ref = np.where(np.abs(ref) < 1e-9, 1.0, ref)
        hv_e, hv_h = mc_hypervolume(eobj, ref), mc_hypervolume(hobj, ref)
        cmp.update(hv_exact=round(hv_e, 6), hv_heur=round(hv_h, 6),
                   hv_gain=round(hv_e - hv_h, 6),
                   nd_exact_to_heur=round(normalized_min_dist(eobj, hobj), 6),
                   nd_heur_to_exact=round(normalized_min_dist(hobj, eobj), 6))
        print(f'   支配覆盖：精确解支配 {cov["n_heur_dominated"]}/{len(hobj)} 个启发式点'
              f'（{cov["exact_dominates_heur"]:.1%}）；'
              f'启发式支配 {cov["n_exact_dominated"]}/{len(eobj)} 个精确点')
        print(f'   归一化最短距离：精确→启发式 {cmp["nd_exact_to_heur"]:.4f}，'
              f'启发式→精确 {cmp["nd_heur_to_exact"]:.4f}')
        print(f'   蒙特卡洛 HV（{N_MC_HV} 点）：精确 {hv_e:.4f} vs 启发式 {hv_h:.4f}，'
              f'增益 {hv_e - hv_h:+.4f}')
        verdict = cov['n_exact_dominated'] == 0
        cmp['verdict_pass'] = bool(verdict)
        print(f'   判据（MILP 解不得被任何 NSGA-II 点支配）：'
              f'{"✓ 通过" if verdict else "✗ 未通过"}')
    else:
        print('   !! NSGA-II 无可行解，互证失效（如实记录，不掩饰）')
        cmp['verdict_pass'] = False
    pd.DataFrame([cmp]).to_csv(os.path.join(RES, f'q3_compare{suffix}.csv'),
                               index=False, encoding='utf-8-sig')

    # 两个前沿一起落盘：图的唯一数据源（绘图脚本不得重算）
    fronts = [dict(source='MILP', point=f'P{i}', f1=q['f1'], f2=q['f2'], f3=q['f3'])
              for i, q in enumerate(uniq, 1)]
    fronts += [dict(source='NSGA-II', point=f'H{i}', f1=float(o[0]), f2=float(o[1]),
                    f3=float(o[2])) for i, o in enumerate(hobj, 1)]
    pd.DataFrame(fronts).to_csv(os.path.join(RES, f'q3_fronts{suffix}.csv'),
                                index=False, encoding='utf-8-sig')

    # 每个 Pareto 点相对参考谱的逐列改动量（只记非零列，供热图/条形图）
    dl = []
    for i, q in enumerate(uniq, 1):
        d = q['t'] - x0
        for j in np.where(np.abs(d) > 1e-7)[0]:
            dl.append(dict(point=f'P{i}', feat=sel[j], group=grp[sel[j]],
                           delta=round(float(d[j]), 6),
                           t=round(float(q['t'][j]), 6),
                           x0=round(float(x0[j]), 6)))
    ddf = pd.DataFrame(dl)
    ddf.to_csv(os.path.join(RES, f'q3_deltas{suffix}.csv'),
               index=False, encoding='utf-8-sig')

    # 瀑布图数据：把逐化合物改动按 origin_paper 组聚合，做**逐组累加的 f1 分解**。
    # 顺序按该组 |Δx| 总和降序逐个"装上"，每一柱 = f1(装到第 i 组) − f1(装到第 i−1 组)。
    # 首柱 = 基线 f1（不改动），末柱 = 该 Pareto 点的 f1 —— 与 f1 的定义严格闭合。
    # 注意：加法分解与顺序有关（交互项被记到最后装上的一组），这是瀑布图的固有性质，
    # 论文里必须写明顺序规则，否则会被质疑"为什么这么分"。
    # **必须在这里算**——绘图脚本不得重算论文数值（figure-contract）。
    if len(ddf):
        def _f1_of(dx_full):
            pred = C + B @ (x0 + dx_full)
            return float(np.sum(w * np.abs(pred - Targ)))

        wf_rows = []
        for pt in sorted(ddf.point.unique()):
            sub = ddf[ddf.point == pt]
            idx_of = {f: j for j, f in enumerate(sel)}
            # 每组的 |Δx| 总和 → 决定装配顺序
            gsize = (sub.groupby('group').delta.apply(lambda s: float(np.abs(s).sum()))
                     .sort_values(ascending=False))
            dx = np.zeros(len(sel))
            f_prev = _f1_of(dx)            # 基线：什么都不改
            wf_rows.append(dict(point=pt, order=0, group='__baseline__',
                                delta_f1=0.0, f1_after=round(f_prev, 6),
                                n_feats=0))
            for order, g in enumerate(gsize.index, 1):
                rows_g = sub[sub.group == g]
                for _, r in rows_g.iterrows():
                    dx[idx_of[r.feat]] = float(r.delta)
                f_now = _f1_of(dx)
                wf_rows.append(dict(point=pt, order=order, group=g,
                                    delta_f1=round(f_now - f_prev, 6),
                                    f1_after=round(f_now, 6),
                                    n_feats=int(len(rows_g))))
                f_prev = f_now
        wf = pd.DataFrame(wf_rows)
        wf.to_csv(os.path.join(RES, f'q3_waterfall{suffix}.csv'), index=False,
                  encoding='utf-8-sig', float_format='%.6f')
        # 闭合校验：末柱的 f1_after 必须等于该 Pareto 点的 f1
        f1_by_pt = {f'P{i}': q['f1'] for i, q in enumerate(uniq, 1)}
        print('\n   瀑布图分解闭合校验（末柱 f1 vs Pareto 点 f1）：')
        wf_ok = True
        for pt, v in wf.groupby('point').f1_after.last().items():
            ref = float(f1_by_pt.get(pt, np.nan))
            gap = abs(float(v) - ref)
            wf_ok &= (gap < 1e-4)
            print(f'     {pt}: 分解 {float(v):.6f} vs Pareto {ref:.6f} '
                  f'（差 {gap:.2e}）')
        assert wf_ok, '瀑布图分解与 f1 不闭合，检查 _f1_of 的系数口径'

    # ---- 输出 ----
    rows = []
    for i, q in enumerate(uniq, 1):
        ch = np.where(q['y'] > 0.5)[0]
        rows.append(dict(
            point=f'P{i}', f1=round(q['f1'], 6), f2=round(q['f2'], 6),
            f3=round(q['f3'], 4), e_f2=round(q['e_f2'], 6), e_f3=round(q['e_f3'], 4),
            n_changed=int(len(ch)),
            changed_feats=';'.join(sel[j] for j in ch[:50]),
            max_abs_delta=round(float(np.max(np.abs(q['t'] - x0))), 6),
            hard_margin_min=round(float(min(q['margins'])), 8),
            hard_feasible=bool(all(v <= 1e-7 for v in q['margins'])),
            status=q['status_name'], mip_gap=None if not np.isfinite(q['gap']) else q['gap'],
            runtime_s=round(q['runtime'], 3), backend=q['backend'],
            nvars=q['nvars'], nbin=q['nbin'], nconstr=q['nconstr']))
    pd.DataFrame(rows).to_csv(os.path.join(RES, f'q3_pareto{suffix}.csv'),
                              index=False, encoding='utf-8-sig')

    pd.DataFrame(dict(
        feat=sel, x0=np.round(x0, 6), lb=np.round(lb, 6), ub=np.round(ub, 6),
        group=[grp[f] for f in sel],
        is_log10=[f in LOG10_COLS for f in sel],
        threshold=[thr.get(f, np.nan) for f in sel])).to_csv(
        os.path.join(RES, f'q3_style_ref{suffix}.csv'), index=False, encoding='utf-8-sig')

    gdf = pd.DataFrame(gen, columns=sel)
    gdf.insert(0, 'style', args.style)
    gdf.to_csv(os.path.join(RES, f'q3_generated{suffix}.csv'), index=False, encoding='utf-8-sig')

    # ---- 风格感官画像（雷达图数据源）----
    # 队友 figs.py:550-580 的雷达图第三条曲线是 `rng.normal(0,.04)` 伪造的"迁移后画像"，
    # 那是编数据。这里三条线全部有出处：
    #   ① 目标风格实测均值（mask 内的真实样本）
    #   ② 对照风格实测均值（按样本量 ≥10、与目标风格感官欧氏距离最远的那个）
    #   ③ 最优 Pareto 点的代理预测画像（C + B@t，代理在 q3_surrogate.csv 有误差上界）
    # 10 个雷达轴固定取"总体"层 + 代表性单维，覆盖 Malt/Hops/Esters × 香气/风味 + 口感。
    RADAR_DIMS = ['A_malt_all', 'A_hops_all', 'A_esters_all', 'F_malt_all',
                  'F_hops_all', 'F_esters_all', 'bitternes', 'sweetness',
                  'acidity', 'body']
    RADAR_DIMS = [s for s in RADAR_DIMS if s in sens]
    if RADAR_DIMS and len(uniq):
        col_of = {s: j for j, s in enumerate(sens)}
        idx_r = [col_of[s] for s in RADAR_DIMS]
        sty = style.to_numpy()
        counts = pd.Series(sty).value_counts()
        big = [s for s in counts.index if counts[s] >= 10]
        mu_target = Yv[mask][:, idx_r].mean(axis=0)
        # 感官空间里与目标风格最远的对照风格（只用 ≥10 的类，避免小类噪声）
        best_c, best_d = None, -1.0
        for s in big:
            if s == args.style:
                continue
            m = (sty == s)
            v = Yv[m][:, :].mean(axis=0)
            d = float(np.linalg.norm(v - Yv[mask].mean(axis=0)))
            if d > best_d:
                best_c, best_d = s, d
        mu_ctrl = (Yv[sty == best_c][:, idx_r].mean(axis=0)
                   if best_c is not None else np.zeros(len(idx_r)))
        # 最优 Pareto 点（f1 最小）的代理预测
        best_pt = min(uniq, key=lambda q: q['f1'])
        pred_full = C + B @ best_pt['t']
        mu_pred = pred_full[idx_r]
        pr = []
        for i, s in enumerate(RADAR_DIMS):
            pr.append(dict(dim=s, series=f'{args.style}（目标风格实测）',
                           value=round(float(mu_target[i]), 4)))
            pr.append(dict(dim=s, series=f'{best_c}（对照风格实测）' if best_c else '对照',
                           value=round(float(mu_ctrl[i]), 4)))
            pr.append(dict(dim=s, series=f'{args.style}（最优 Pareto 点代理预测）',
                           value=round(float(mu_pred[i]), 4)))
        pd.DataFrame(pr).to_csv(os.path.join(RES, f'q3_style_profile{suffix}.csv'),
                                index=False, encoding='utf-8-sig',
                                float_format='%.4f')
        print(f'\n   风格画像：目标 {args.style}（n={n_style}），'
              f'对照 {best_c}（n={int(counts[best_c]) if best_c else 0}，'
              f'感官欧氏距离 {best_d:.3f}），雷达轴 {len(RADAR_DIMS)} 个')

    dur = time.perf_counter() - t0
    summary = dict(
        style=args.style, n_style=int(n_style),
        n_features_total=len(feats), n_decision=n, n_sensory=ns, kmax=int(args.kmax),
        decision_feature_rule='Q2 Top-3 union ∧ aroma ∧ ∪ {DMS, X4VG, diacetyl}',
        n_fixed_span=int(fixed.sum()),
        shrinkage=None if not np.isfinite(shrink_s) else round(float(shrink_s), 4),
        novelty=nov,
        surrogate=dict(kind='PLSRegression', n_components=k_best,
                       cv_folds=5, cv_r2_median=round(float(np.median(cv_r2)), 4),
                       cv_r2_positive=int((cv_r2 > 0).sum()),
                       err_median=round(float(np.median(err)), 4),
                       err_p95=round(float(np.percentile(err, 95)), 4),
                       err_max=round(float(err.max()), 4),
                       err_max_over_sd_median=round(float(np.median(err.max(0) / sd)), 4),
                       fitted_on='all 250 samples (style subset only sets Targ & bounds)'),
        hard_constraints=dict(zip([sel[j] for j in kh_idx],
                                  [round(float(hard_cap[k]), 6) for k in range(len(kh_idx))])),
        soft_constraints=dict(zip([sel[j] for j in ks_idx],
                                  [round(float(soft_thr[k]), 6) for k in range(len(ks_idx))])),
        threshold_quantile=THRESH_QUANTILE,
        f1_form='L1 weighted by 1/sd', gamma=GAMMA, lam=LAMBDA,
        grid=list(args.grid), payoff=payinfo,
        n_grid_points=len(pts), n_pareto=len(uniq), all_points_feasible_nondominated=bool(ok_all),
        baseline_x0=dict(f1=round(base_f1, 6), margins=[round(v, 6) for v in base_margins]),
        compare=cmp, solver_requested=args.solver,
        gurobi_available=have_gurobi(), duration_s=round(dur, 1))
    with open(os.path.join(RES, f'q3_run_log{suffix}.json'), 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2, default=str)

    print(f'\n耗时 {dur / 60:.1f} min → results/q3_*.csv')
    print('=' * 90)
    return 0


if __name__ == '__main__':
    sys.exit(main())
