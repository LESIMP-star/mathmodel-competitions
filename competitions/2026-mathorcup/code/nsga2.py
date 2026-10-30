# -*- coding: utf-8 -*-
"""nsga2.py — 纯 numpy 的 NSGA-II 核心（Q3 精确解 vs 启发式互证用）

本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：Hermes Agent（Nous Research），底层模型 deepseek-v4-flash，
# 开发机构：Nous Research（工具）/ 深度求索 DeepSeek（模型），使用日期：2026-10-26

来源与改动（务必如实写进论文"算法实现"一节）：
  骨架抽取自本队 2026 华数杯 C 题 `huashubei/output/code/q2_solve.py` 的 L66-204，
  并按 Deh 2002 原始定义修正两处实现错误、替换进化算子：

  [修正 1] fast_nondominated_sort 的支配计数方向
      原实现  n_dom = dom.sum(axis=1)   # = "i 支配了多少个解"
      正确    n_dom = dom.sum(axis=0)   # = "有多少个解支配 i"
      实测后果：9 点混合种群下原版第 0 层返回最差的 [6,7,8]，正解应为 [0,1,2]。
      当年华数杯结果未崩，是因为 update_archive / pareto_mask 用了独立的支配掩码，
      层排序错误被存档层掩盖——属运气而非设计。

  [修正 2] crowding_distance 的边界处理
      原实现  len(front) <= 2 时直接返回全 0
      正确    返回全 inf（边界解无限拥挤，必须保留），且边界点无条件置 inf 后再跳过零跨度目标

  [改动 3] 进化算子
      原为整数编码的均匀交叉 + 值域随机重置变异（任务调度问题专用）
      本模块改为实数 SBX（η=15）+ 多项式变异（η=20），以适配 Q3 连续的 log10 调整量 x

公开接口：
  fast_nondominated_sort(objs)                  -> list[np.ndarray]   分层
  crowding_distance(objs, front)                -> np.ndarray
  rank_population(objs, viols)                  -> (rank, crowd)
  tournament_compare(a, b, rank, crowd, viols)  -> int
  update_archive(archive, sols, cap)            -> list
  sbx_crossover(x1, x2, lb, ub, eta, rng)
  polynomial_mutation(x, lb, ub, eta, pm, rng)
  pareto_mask(objs)                             -> np.ndarray[bool]
  dominance_coverage(exact_objs, heur_objs)     -> dict
  nsga2(objective, n_var, lb, ub, ...)          -> dict

自检：python nsga2.py
"""
from __future__ import annotations

import numpy as np

__all__ = [
    'fast_nondominated_sort', 'crowding_distance', 'rank_population',
    'tournament_compare', 'update_archive', 'sbx_crossover',
    'polynomial_mutation', 'pareto_mask', 'dominance_coverage',
    'domination_matrix', 'nsga2',
]


# ---------------------------------------------------------------- 支配关系
def domination_matrix(objs):
    """返回 (N,N) 布尔矩阵 dom，dom[i, j] = True 表示 i 支配 j（最小化口径）。

    本模块所有支配判断的唯一实现，其余函数一律复用它，避免出现两套口径
    （这正是华数杯那处 bug 的根因：两套独立写法互相掩盖）。
    """
    o = np.asarray(objs, dtype=float)
    le = (o[:, None, :] <= o[None, :, :]).all(-1)
    lt = (o[:, None, :] < o[None, :, :]).any(-1)
    return le & lt


def pareto_mask(objs):
    """非支配解掩码（最小化）。等价于 q4_solve.py L89 的同名函数。"""
    dom = domination_matrix(objs)
    return ~dom.any(axis=0)


# ---------------------------------------------------------------- 非支配排序
def fast_nondominated_sort(objs):
    """快速非支配排序（Deb 2002 式(15)）。返回层列表，每层是索引数组。

    [修正 1] n_dom 取 axis=0：数"支配 i 的解个数"，而非"i 支配的解个数"。
    """
    o = np.asarray(objs, dtype=float)
    n = len(o)
    if n == 0:
        return []
    dom = domination_matrix(o)
    n_dom = dom.sum(axis=0)                 # ← 关键：axis=0（原实现误用 axis=1）
    fronts, rem = [], np.ones(n, dtype=bool)
    while rem.any():
        f_idx = np.flatnonzero(rem & (n_dom == 0))
        if len(f_idx) == 0:                 # 兜底：仅当出现 NaN 等病态输入才会触发
            f_idx = np.flatnonzero(rem)
        fronts.append(f_idx)
        for i in f_idx:
            n_dom[dom[i] & rem] -= 1
        rem[f_idx] = False
    return fronts


def crowding_distance(objs, front):
    """拥挤度距离（Deb 2002 式(16)）。

    [修正 2] 边界点无条件置 inf（而非按 span<=0 才跳过导致小前沿退化为全 0）。
    """
    front = np.asarray(front, dtype=int)
    if len(front) == 0:
        return np.zeros(0)
    if len(front) <= 2:                     # 单点/两点前沿：无"中间解"，全部视为边界
        return np.full(len(front), np.inf)
    o = np.asarray(objs, dtype=float)[front]
    m = o.shape[1]
    d = np.zeros(len(front))
    for j in range(m):
        order = np.argsort(o[:, j], kind='stable')
        d[order[0]] = np.inf
        d[order[-1]] = np.inf
        span = o[order[-1], j] - o[order[0], j]
        if span <= 0:                       # 该目标上全部并列：中间解不加分
            continue
        d[order[1:-1]] += (o[order[2:], j] - o[order[:-2], j]) / span
    return d


# ---------------------------------------------------------------- 约束支配
def rank_population(objs, viols):
    """约束支配分层（Deb 约束支配准则 + 分级惩罚排序）。

    viols[i] <= 0 视为可行。可行解之间按非支配排序；不可行解按违反量升序
    排在所有可行层之后，不进入任何前沿。
    """
    n = len(objs)
    feas = np.asarray(viols, dtype=float) <= 0.0
    rank = np.full(n, -1, dtype=np.int32)
    crowd = np.zeros(n)
    n_fronts = 0
    if feas.any():
        sub = np.asarray(objs, dtype=float)[feas]
        fronts = fast_nondominated_sort(sub)
        idx_feas = np.flatnonzero(feas)
        for k, fr in enumerate(fronts):
            rank[idx_feas[fr]] = k
            crowd[idx_feas[fr]] = crowding_distance(sub, fr)
        n_fronts = len(fronts)
    if (~feas).any():
        idx = np.flatnonzero(~feas)
        order = idx[np.argsort(np.asarray(viols, dtype=float)[idx], kind='stable')]
        rank[order] = n_fronts + 1 + np.arange(len(order))
    return rank, crowd


def tournament_compare(a, b, rank, crowd, viols):
    """二元锦标赛：可行 > 不可行；同可行性下 层小者优 → 拥挤度大者优。"""
    fa, fb = viols[a] <= 0, viols[b] <= 0
    if fa != fb:
        return a if fa else b
    if not fa:                              # 两者皆不可行：违反量小者优
        return a if viols[a] <= viols[b] else b
    if rank[a] != rank[b]:
        return a if rank[a] < rank[b] else b
    return a if crowd[a] >= crowd[b] else b


# ---------------------------------------------------------------- 全局存档
def update_archive(archive, sols, cap=None):
    """跨代全局帕累托存档：并入新的可行解 → 去重 → 剔被支配 → 超容按拥挤度截断。

    archive / sols 元素为 dict，必须含键 'obj'（目标向量）与 'feas'（bool）。
    与 q2_solve.py L180 同语义，但解除了对问题对象 p 的依赖。
    """
    cand = list(archive) + [s for s in sols if s.get('feas', False)]
    if not cand:
        return []
    objs = np.array([s['obj'] for s in cand], dtype=float)
    _, first = np.unique(np.round(objs, 10), axis=0, return_index=True)
    cand = [cand[i] for i in np.sort(first)]
    if len(cand) == 1:
        return cand
    objs = np.array([s['obj'] for s in cand], dtype=float)
    keep = np.flatnonzero(pareto_mask(objs))
    cand = [cand[i] for i in keep]
    if cap is not None and len(cand) > cap:
        objs = np.array([s['obj'] for s in cand], dtype=float)
        d = crowding_distance(objs, np.arange(len(cand)))
        sel = np.argsort(d)[::-1][:cap]
        cand = [cand[i] for i in sel]
    return cand


# ---------------------------------------------------------------- 实数进化算子
def sbx_crossover(x1, x2, lb, ub, eta=15.0, rng=None):
    """模拟二进制交叉（Deb & Agrawal 1995 SBX），实数编码，逐基因独立。

    注意：skill 库 `algorithms/optimization/genetic_algorithm.py` L54 注释写的是 SBX，
    但实现是算术交叉 αp₁+(1−α)p₂，不含分布指数 η、不做子代对称扩展——两者不可混称。
    """
    rng = np.random.default_rng() if rng is None else rng
    x1 = np.asarray(x1, dtype=float)
    u = rng.random(x1.shape)
    beta = np.where(u <= 0.5,
                    (2.0 * u) ** (1.0 / (eta + 1.0)),
                    (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (eta + 1.0)))
    c1 = 0.5 * ((1.0 + beta) * x1 + (1.0 - beta) * x2)
    c2 = 0.5 * ((1.0 - beta) * x1 + (1.0 + beta) * x2)
    return np.clip(c1, lb, ub), np.clip(c2, lb, ub)


def polynomial_mutation(x, lb, ub, eta=20.0, pm=None, rng=None):
    """多项式变异（Deb 2001），实数编码。pm 缺省取 1/n（每代期望一个基因变异）。"""
    rng = np.random.default_rng() if rng is None else rng
    x = np.asarray(x, dtype=float)
    n = x.size
    pm = 1.0 / max(n, 1) if pm is None else pm
    mask = rng.random(n) < pm
    u = rng.random(n)
    delta = np.where(u < 0.5,
                     (2.0 * u) ** (1.0 / (eta + 1.0)) - 1.0,
                     1.0 - (2.0 * (1.0 - u)) ** (1.0 / (eta + 1.0)))
    y = x + delta * (np.asarray(ub) - np.asarray(lb))
    return np.where(mask, np.clip(y, lb, ub), x)


# ---------------------------------------------------------------- 主循环
def nsga2(objective, n_var, lb, ub, pop_size=100, n_gen=200, seed=2026,
          pc=0.9, eta_c=15.0, eta_m=20.0, pm=None, archive_cap=300,
          init_pop=None, log=None):
    """NSGA-II 主循环。

    objective(x) -> (obj_vector, violation)    violation <= 0 表示可行
    init_pop: 可选 (k, n_var) 初始个体（如 MILP 的 x=0 基线、或单目标最优点）

    返回 dict: archive / pop / front / stats
    """
    rng = np.random.default_rng(seed)
    lb = np.broadcast_to(np.asarray(lb, dtype=float), (n_var,)).copy()
    ub = np.broadcast_to(np.asarray(ub, dtype=float), (n_var,)).copy()

    def evaluate(x):
        obj, viol = objective(x)
        return dict(x=np.array(x, dtype=float), obj=np.asarray(obj, dtype=float),
                    viol=float(viol), feas=float(viol) <= 0.0)

    # ---- 初始化 ----
    pop = []
    if init_pop is not None:
        for x in np.atleast_2d(init_pop)[:pop_size]:
            pop.append(evaluate(np.clip(x, lb, ub)))
    while len(pop) < pop_size:
        pop.append(evaluate(lb + rng.random(n_var) * (ub - lb)))

    archive = []
    stats = dict(gen_best=[], archive_sizes=[], n_eval=len(pop))

    for g in range(n_gen):
        objs = np.array([s['obj'] for s in pop])
        viols = np.array([s['viol'] for s in pop])
        rank, crowd = rank_population(objs, viols)

        # ---- 产生子代：锦标赛 → SBX → 多项式变异 ----
        offspring = []
        while len(offspring) < pop_size:
            ia, ib = rng.integers(0, pop_size, size=2)
            if ia == ib:
                continue
            p1 = pop[tournament_compare(ia, ib, rank, crowd, viols)]
            ia, ib = rng.integers(0, pop_size, size=2)
            if ia == ib:
                continue
            p2 = pop[tournament_compare(ia, ib, rank, crowd, viols)]
            if rng.random() < pc:
                c1, c2 = sbx_crossover(p1['x'], p2['x'], lb, ub, eta_c, rng)
            else:
                c1, c2 = p1['x'].copy(), p2['x'].copy()
            for c in (c1, c2):
                offspring.append(evaluate(polynomial_mutation(c, lb, ub, eta_m, pm, rng)))
                if len(offspring) >= pop_size:
                    break

        # ---- 精英保留：父子合并 → 分层 + 拥挤度截断 ----
        merged = pop + offspring
        objs = np.array([s['obj'] for s in merged])
        viols = np.array([s['viol'] for s in merged])
        rank, crowd = rank_population(objs, viols)
        order = np.lexsort((-crowd, rank))          # rank 升序、crowd 降序
        pop = [merged[i] for i in order[:pop_size]]

        archive = update_archive(archive, pop, archive_cap)

        feas_f1 = [s['obj'][0] for s in pop if s['feas']]
        stats['gen_best'].append(min(feas_f1) if feas_f1 else np.nan)
        stats['archive_sizes'].append(len(archive))
        stats['n_eval'] += len(offspring)
        if log is not None and ((g + 1) % max(1, n_gen // 10) == 0 or g == n_gen - 1):
            log(f'  gen {g + 1:>4}/{n_gen} | 可行 {len(feas_f1)}/{pop_size} | '
                f'存档 {len(archive)} | 最优 f1={stats["gen_best"][-1]:.4g}')

    archive = update_archive(archive, pop, archive_cap)
    return dict(archive=archive, pop=pop, stats=stats)


# ---------------------------------------------------------------- 精确解 vs 启发式
def dominance_coverage(exact_objs, heur_objs):
    """精确前沿对启发式前沿的支配覆盖统计（最小化口径）。

    写法取自 `huashubei/output/code/milp_q2_exact.py` L445-465，抽成独立函数。
    返回 dict：
      exact_dominates_heur  精确解至少支配一个启发式点的比例
      heur_dominates_exact  启发式解至少支配一个精确点的比例（>0 说明精确解漏了解）
      n_exact / n_heur

    ⚠ 两个方向必须**各自算**。支配关系不对称，"x 支配 y"的布尔矩阵转置
    并不等于"y 支配 x"（转置给出的是同一个命题换了索引顺序）。
    原 huashubei 版本用 `h_dom_e = e_dom_h.T`，会把方向判反，
    把"精确解支配了哪个启发式点"错报成"精确解被哪个启发式点支配"。
    """
    e = np.atleast_2d(np.asarray(exact_objs, dtype=float))
    h = np.atleast_2d(np.asarray(heur_objs, dtype=float))

    def _dom(A, Bm):
        le = (A[:, None, :] <= Bm[None, :, :]).all(-1)
        lt = (A[:, None, :] < Bm[None, :, :]).any(-1)
        return le & lt

    e_dom_h = _dom(e, h)          # [i, j] = exact_i 支配 heur_j
    h_dom_e = _dom(h, e)          # [j, i] = heur_j 支配 exact_i
    return dict(
        n_exact=int(len(e)), n_heur=int(len(h)),
        exact_dominates_heur=float(e_dom_h.any(axis=0).mean()),
        heur_dominates_exact=float(h_dom_e.any(axis=0).mean()),
        n_heur_dominated=int(e_dom_h.any(axis=0).sum()),
        n_exact_dominated=int(h_dom_e.any(axis=0).sum()),
    )


# ---------------------------------------------------------------- 自检
def _self_test():
    """4 个 handcrafted 用例 + 与 pareto_mask 的一致性检查。全部通过才算可用。"""
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print(f'  [{"PASS" if good else "FAIL"}] {name}')
        if not good:
            print(f'         got  = {got}')
            print(f'         want = {want}')

    print('用例 1：4 点链（修正 1 的关键回归）')
    objs = np.array([[0., 0.], [1., 1.], [2., 2.], [3., 3.]])
    check('层结构', [f.tolist() for f in fast_nondominated_sort(objs)],
          [[0], [1], [2], [3]])

    print('用例 2：真实种群形态（3 真非支配 + 6 被支配）')
    pts = np.array([[0.1, 0.9], [0.5, 0.5], [0.9, 0.1],
                    [0.2, 0.9], [0.6, 0.6], [1.0, 0.2],
                    [0.3, 0.95], [0.7, 0.7], [1.1, 0.3]])
    f = fast_nondominated_sort(pts)
    check('层 0 是真正前沿', f[0].tolist(), [0, 1, 2])
    check('层 1', f[1].tolist(), [3, 4, 5])
    check('层 2', f[2].tolist(), [6, 7, 8])

    print('用例 3：拥挤度边界（修正 2）')
    check('单点前沿 -> inf', crowding_distance(objs, np.array([0])).tolist(), [np.inf])
    check('两点前沿 -> [inf, inf]',
          crowding_distance(objs, np.array([0, 1])).tolist(), [np.inf, np.inf])
    d3 = crowding_distance(np.array([[0., 3.], [1.5, 1.5], [3., 0.]]), np.array([0, 1, 2]))
    check('三点典型前沿 -> 边界 inf、中间有限', (np.isinf(d3[0]) and np.isinf(d3[2]) and np.isfinite(d3[1])), True)

    print('用例 4：分层与 pareto_mask 的一致性（2 目标 + 3 目标）')
    for trial, m in [(0, 2), (1, 3)]:
        rng = np.random.default_rng(trial)
        many = rng.random((40, m))
        layer0 = fast_nondominated_sort(many)[0]
        check(f'{m} 目标：层 0 == pareto_mask', sorted(layer0.tolist()),
              sorted(np.flatnonzero(pareto_mask(many)).tolist()))

    print('用例 5：SBX / 多项式变异的边界与形状')
    rng = np.random.default_rng(0)
    c1, c2 = sbx_crossover(np.full(5, -1.0), np.full(5, 1.0), -1.0, 1.0, 15.0, rng)
    check('SBX 子代在界内', bool((np.abs(c1) <= 1).all() and (np.abs(c2) <= 1).all()), True)
    mut = polynomial_mutation(np.zeros(200), -1.0, 1.0, 20.0, 0.5, rng)
    check('变异产生变化且不越界', bool((mut != 0).any() and (np.abs(mut) <= 1).all()), True)

    print('用例 6：约束支配把不可行解排除在前沿之外')
    objs6 = np.array([[0., 0.], [0.1, 0.1], [0.2, 0.2]])
    viol6 = np.array([0.0, 1.0, 0.0])
    rank6, _ = rank_population(objs6, viol6)
    check('不可行解 rank > 所有可行层', bool(rank6[1] > max(rank6[0], rank6[2])), True)

    print('用例 7：dominance_coverage 两个方向各自独立计算（支配关系不对称）')
    E = np.array([[0., 1.], [1., 0.], [0.5, 0.5]])   # 三个精确点
    H = np.array([[2., 2.], [1.5, 1.5]])             # 两个都被 E 支配的启发式点
    c7 = dominance_coverage(E, H)
    check('精确点把两个启发式点都支配', c7['n_heur_dominated'], 2)
    check('精确点自己不被任何启发式点支配', c7['n_exact_dominated'], 0)
    # 反过来：启发式点支配精确点的情况（E 取更差的点）
    c7b = dominance_coverage(np.array([[3., 3.]]), np.array([[1., 1.]]))
    check('反向：启发式点支配精确点', c7b['n_exact_dominated'], 1)

    print()
    print('ALL PASS' if ok else 'SOME TESTS FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(_self_test())
