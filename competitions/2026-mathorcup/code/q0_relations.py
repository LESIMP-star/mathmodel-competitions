# -*- coding: utf-8 -*-
"""q0_relations.py — 问题零：变量关系体检（只读统计，不重训任何模型）

本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：Hermes Agent（Nous Research），底层模型 deepseek-v4-flash，
# 开发机构：Nous Research（工具）/ 深度求索 DeepSeek（模型），使用日期：2026-10-26

================================================================ 为什么单独一个脚本
Q1/Q2/Q3 的模型选择全部依赖"特征之间到底怎么相关"这件事，但此前全项目
**没有任何一份落盘的变量关系产物**：没有 226×226 相关矩阵、没有 VIF 表、
没有风格间的差异检验。verify_facts.py:520-545 算过 VIF / 有效秩，但只 print 不落盘，
下游绘图与论文正文都无法引用。

本脚本把那些散落的中间量全部固化成 CSV，供：
  - chart_plan_Q1 的"相关矩阵热力图"、
  - 论文 §5 数据预处理与 §6 特征工程的论证、
  - Q2 用"逐列置换重要性"而非"按 VIF 删变量"的选择理由。
纯读取 + 统计，约 30 秒，不重训任何模型。

================================================================ 口径（与 q1.py / q2.py 完全一致）
  - 特征 = 1.csv 的 231 个化学列 剔除 5 个派生列 = 226
  - 37 个 log10 列保持 log10 尺度（1.csv 已是 log10）
  - 真 NA 保留（相关用 pairwise-complete），不做插补——插补会人为抬高相关
  - 靶 = 4.csv 的 50 个感官维
  - 风格 = 1.csv 的 tasting_category_fine

================================================================ 为什么同时报 Pearson 与 Spearman
化学浓度跨 4 个数量级、含 LOD 地板值（-1.817819 密集重复），Pearson 会被
地板点与离群点主导。Spearman 对单调变换不变，是本题的正确默认；Pearson
只作对照，两者差异本身是"地板/离群"的证据。

================================================================ 输出
  results/q0_corr_feat.csv        226 × 227  特征间 Spearman 相关矩阵
  results/q0_corr_top.csv         高相关变量对清单（|rho| >= 0.5，降序）
  results/q0_vif.csv              226 × 6    VIF / 容差 / 条件指数
  results/q0_effective_rank.json  有效秩与主成分解释率
  results/q0_sens_corr.csv        226 × 50   特征 ↔ 感官 Spearman
  results/q0_style_kruskal.csv    226 × 8    按 22 风格的 Kruskal-Wallis + eps^2
  results/q0_crosscheck.json      与官方 2.csv / 6.csv 的一致性交叉验证
  results/q0_summary.json         汇报口径的关键数字

================================================================ 运行
  python q0_relations.py
"""
from __future__ import annotations

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

DERIVED = ['kcalperc', 'esters_sum', 'aroma_hops_sum', 'acids_sum', 'sulfur_sum']
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
PAIR_HI = 0.9     # "近似重复列"阈值
PAIR_MID = 0.5    # "中等相关"阈值


def norm_key(s):
    """与 q2.py:118 完全一致，用于跨表列名对齐。"""
    s = str(s).lower()
    for ch in ('_', '-', ' '):
        s = s.replace(ch, '.')
    while '..' in s:
        s = s.replace('..', '.')
    return s.strip('.')


def build_name_maps():
    """官方 2.csv / 6.csv 用的是化学名与"面板反馈"列名，与我方的 field_name_python
    与 4.csv 的 R 名完全不同。8.xlsx 同时提供两套名字，是唯一可用的桥。

    2.csv  → index 是 chemical_name / chemical_name_short（如 'Isoamyl acetate'）
    6.csv  → 行是 chemical_name_short，列是 CleanName_PanelFeedback
    4.csv  → 列是 R_name（如 A_esters_all）

    实测映射率：2.csv 231 行 → 212 行可对应到我方 226 特征；6.csv 44 行 → 43 行。
    """
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(DATA, '8.xlsx'),
                                read_only=True, data_only=True)
    r_th = list(wb['Sensory thresholds'].iter_rows(values_only=True))
    r_sn = list(wb['Sensory names'].iter_rows(values_only=True))
    wb.close()

    th = pd.DataFrame(r_th[1:], columns=list(r_th[0]))
    sn = pd.DataFrame(r_sn[1:], columns=list(r_sn[0]))

    # 化学名 → 我方特征名。
    # 注意：1.csv 的列名是 `field_name_R`（如 'X2.3.butanedione'），不是
    # `field_name_python`（'2,3-butanedione'）。q2.py:135 也是拿 field_name_R
    # 做 norm_key 去匹配 feats，这里保持同一口径。
    chem2feat = {}
    for _, r in th.iterrows():
        r_name = r.get('field_name_R')
        if pd.isna(r_name):
            continue
        for k in ('chemical_name', 'chemical_name_short', 'field_name_python',
                  'field_name_R'):
            v = r.get(k)
            if pd.notna(v):
                chem2feat.setdefault(norm_key(v), str(r_name))

    # 4.csv 的 R 名 ↔ 6.csv 的"面板反馈"列名。
    # 必须只取 dataset == 'Trained panel'：Sensory names 里 Trained panel 与
    # Ratebeer 各 50/51 行，两套 CleanName_PanelFeedback 大量同名，
    # 不过滤会让 Ratebeer 的 R 名覆盖掉训练面板的，映射率从 49/50 掉到 6/50。
    sens2panel = {}
    for _, r in sn.iterrows():
        if str(r.get('dataset', '')).strip() != 'Trained panel':
            continue
        rn, pf = r.get('R_name'), r.get('CleanName_PanelFeedback')
        if pd.notna(rn) and pd.notna(pf):
            sens2panel[str(rn)] = str(pf).strip()
    return chem2feat, sens2panel


def hr(title):
    print('\n' + '=' * 72)
    print('  ' + title)
    print('=' * 72)


# ============================================================ 数据
def load():
    c1 = pd.read_csv(os.path.join(DATA, '1.csv'))
    c4 = pd.read_csv(os.path.join(DATA, '4.csv'))

    # 主口径 231 列（与附件2 的 231×231 相关矩阵一致），见 q1.py 顶部说明
    feats = list(c1.columns[3:])
    sens = list(c4.columns[3:])
    assert len(feats) == 231, f'特征数应为 231，实际 {len(feats)}'
    assert len(sens) == 50, f'靶数应为 50，实际 {len(sens)}'

    assert c1['beer'].is_unique and c4['beer'].is_unique
    meta = c1.set_index('beer')[['tasting_category_fine']]
    X = c1.set_index('beer')[feats].apply(pd.to_numeric, errors='coerce')
    Y = c4.set_index('beer')[sens].apply(pd.to_numeric, errors='coerce')
    idx = X.index.intersection(Y.index)
    assert len(idx) == 250, f'交集应为 250，实际 {len(idx)}'
    return X.loc[idx], Y.loc[idx], meta.loc[idx], feats, sens


# ============================================================ 1. 特征间相关
def feat_corr(X, feats):
    hr('1. 特征间相关（Spearman 主、Pearson 对照）')
    S = X.corr(method='spearman')
    Sp = X.corr(method='pearson')
    S.index.name = 'feat'
    S.to_csv(os.path.join(RES, 'q0_corr_feat.csv'), encoding='utf-8-sig',
             float_format='%.4f')

    iu = np.triu_indices_from(S.values, 1)
    rs = S.values[iu]
    rp = Sp.values[iu]
    ok = ~(np.isnan(rs) | np.isnan(rp))
    rs, rp = rs[ok], rp[ok]

    pairs = pd.DataFrame({
        'feat_a': [feats[i] for i in iu[0][ok]],
        'feat_b': [feats[j] for j in iu[1][ok]],
        'rho_spearman': rs,
        'r_pearson': rp,
    })
    pairs['abs_rho'] = pairs.rho_spearman.abs()
    pairs = pairs[pairs.abs_rho >= PAIR_MID].sort_values('abs_rho', ascending=False)
    pairs.to_csv(os.path.join(RES, 'q0_corr_top.csv'), index=False,
                 encoding='utf-8-sig', float_format='%.4f')

    n_all = int(ok.sum())
    stats = {
        'n_pairs': n_all,
        'median_abs_rho': float(np.median(np.abs(rs))),
        'n_abs_rho_gt_0.5': int((np.abs(rs) > PAIR_MID).sum()),
        'n_abs_rho_gt_0.9': int((np.abs(rs) > PAIR_HI).sum()),
        'median_abs_r_pearson': float(np.median(np.abs(rp))),
        'n_abs_r_gt_0.9_pearson': int((np.abs(rp) > PAIR_HI).sum()),
        'spearman_vs_pearson_median_abs_diff': float(np.median(np.abs(rs - rp))),
    }
    print(f'  变量对 {n_all} 个（{len(feats)} 维两两组合）')
    print(f'  |rho| 中位数 {stats["median_abs_rho"]:.4f}；'
          f'|rho|>{PAIR_MID} 的 {stats["n_abs_rho_gt_0.5"]} 对；'
          f'|rho|>{PAIR_HI} 的 {stats["n_abs_rho_gt_0.9"]} 对')
    print(f'  Pearson 对照：|r| 中位数 {stats["median_abs_r_pearson"]:.4f}，'
          f'|r|>{PAIR_HI} 的 {stats["n_abs_r_gt_0.9_pearson"]} 对')
    print(f'  Spearman−Pearson 中位绝对差 {stats["spearman_vs_pearson_median_abs_diff"]:.4f}')
    if len(pairs):
        print(f'  最强 {min(5, len(pairs))} 对：')
        for _, r in pairs.head(5).iterrows():
            print(f'    {r.feat_a:32s} × {r.feat_b:32s} rho={r.rho_spearman:+.3f}')
    return stats, S, Sp


# ============================================================ 2. VIF / 有效秩
def vif_rank(X, feats):
    """VIF 用相关矩阵伪逆的对角；同时给条件数与有效秩。

    **Pearson 与 Spearman 各算一遍**，这不是冗余：
      verify_facts.py:516-545 用的是 Pearson + 剔除含 NA 的列（218 列），
      本脚本主口径用 Spearman + pairwise（226 列）。
    两者的差异（见输出）全部来自 LOD 地板值 -1.817819 的密集重复与
    跨 4 个数量级的离群点——Pearson 被它们放大，Spearman 不受影响。
    论文必须两个都报，只说一个会被质疑口径。
    """
    hr('2. VIF / 容差 / 条件指数 / 有效秩（Pearson 与 Spearman 双口径）')

    def _calc(corr_df, mask_cols=None):
        R = corr_df.values.astype(float)
        R = np.nan_to_num(R, nan=0.0)
        np.fill_diagonal(R, 1.0)
        vif = np.clip(np.diag(np.linalg.pinv(R)), 0, None)
        ev = np.clip(np.linalg.eigvalsh(R)[::-1], 0, None)
        ratio = np.cumsum(ev) / ev.sum()
        cond = float(ev[0] / ev[ev > 1e-12].min()) if (ev > 1e-12).any() else float('inf')
        ci = np.sqrt(ev[0] / np.clip(ev, 1e-12, None))
        return vif, ev, ratio, cond, ci

    S = X.corr(method='spearman')
    P = X.corr(method='pearson')
    vif_s, ev_s, ratio_s, cond_s, ci_s = _calc(S)
    vif_p, ev_p, ratio_p, cond_p, ci_p = _calc(P)

    def _pack(vif, ev, ratio, cond, ci):
        return {
            'n_pc_for_90pct': int(np.searchsorted(ratio, 0.90) + 1),
            'n_pc_for_95pct': int(np.searchsorted(ratio, 0.95) + 1),
            'pc1_explained_pct': float(ratio[0] * 100),
            'pc10_explained_pct': float(ratio[9] * 100),
            'pc50_explained_pct': float(ratio[49] * 100),
            'n_eigen_gt_1': int((ev > 1.0).sum()),
            'effective_rank_participation': float(ev.sum() ** 2 / (ev ** 2).sum()),
            'condition_number': cond,
            'max_condition_index': float(ci.max()),
            'vif_median': float(np.median(vif)),
            'vif_max': float(vif.max()),
            'n_vif_gt_10': int((vif > 10).sum()),
            'n_vif_gt_100': int((vif > 100).sum()),
        }

    st_s = _pack(vif_s, ev_s, ratio_s, cond_s, ci_s)
    st_p = _pack(vif_p, ev_p, ratio_p, cond_p, ci_p)

    out = pd.DataFrame({
        'feat': feats,
        'vif_spearman': vif_s,
        'vif_pearson': vif_p,
        'tolerance_spearman': 1.0 / np.clip(vif_s, 1e-12, None),
        'condition_index': ci_s,
        'is_log10': [f in LOG10_COLS for f in feats],
    }).sort_values('vif_spearman', ascending=False).reset_index(drop=True)
    out.to_csv(os.path.join(RES, 'q0_vif.csv'), index=False,
               encoding='utf-8-sig', float_format='%.4f')

    payload = {
        'spearman': st_s,
        'pearson': st_p,
        'delta_n_pc90': st_p['n_pc_for_90pct'] - st_s['n_pc_for_90pct'],
        'delta_n_vif_gt_10': st_p['n_vif_gt_10'] - st_s['n_vif_gt_10'],
        'eigenvalues_top20': [float(v) for v in ev_s[:20]],
        'note_pearson_baseline': 'verify_facts.py:516-545 用 Pearson + 剔除含 NA 列（218 列）',
    }
    with open(os.path.join(RES, 'q0_effective_rank.json'), 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f'  Spearman（主口径，226 列）：VIF 中位 {st_s["vif_median"]:.1f}，'
          f'最大 {st_s["vif_max"]:.0f}；VIF>10 的 {st_s["n_vif_gt_10"]}/{len(feats)}，'
          f'>100 的 {st_s["n_vif_gt_100"]}；条件数 {cond_s:.0f}')
    print(f'    PC1 {st_s["pc1_explained_pct"]:.1f}% | 前10 {st_s["pc10_explained_pct"]:.1f}% '
          f'| 前50 {st_s["pc50_explained_pct"]:.1f}% | 到90% 需 {st_s["n_pc_for_90pct"]} 个 PC '
          f'| 特征值>1 的 {st_s["n_eigen_gt_1"]} 个 | 有效秩 {st_s["effective_rank_participation"]:.1f}')
    print(f'  Pearson（对照，与 verify_facts 同口径）：VIF>10 的 {st_p["n_vif_gt_10"]}，'
          f'到90% 需 {st_p["n_pc_for_90pct"]} 个 PC，PC1 {st_p["pc1_explained_pct"]:.1f}%')
    print(f'  两口径差：PC90 多 {payload["delta_n_pc90"]} 个，'
          f'VIF>10 多 {payload["delta_n_vif_gt_10"]} 列（LOD 地板与离群所致）')
    return payload, out


# ============================================================ 3. 特征 ↔ 感官
def sens_corr(X, Y, feats, sens):
    hr('3. 特征 ↔ 感官相关')
    Z = pd.concat([X, Y], axis=1)
    C = Z.corr(method='spearman').loc[feats, sens]
    C.index.name = 'feat'
    C.to_csv(os.path.join(RES, 'q0_sens_corr.csv'), encoding='utf-8-sig',
             float_format='%.4f')

    V = C.values
    stats = {
        'n_cells': int(V.size),
        'median_abs': float(np.nanmedian(np.abs(V))),
        'n_abs_gt_0.3': int((np.abs(V) > 0.3).sum()),
        'n_abs_gt_0.5': int((np.abs(V) > 0.5).sum()),
        'n_abs_gt_0.7': int((np.abs(V) > 0.7).sum()),
        'max_abs': float(np.nanmax(np.abs(V))),
    }
    # 每个感官维最强的 1 个特征
    best = []
    for j, s in enumerate(sens):
        col = np.abs(V[:, j])
        if np.isnan(col).all():
            continue
        i = int(np.nanargmax(col))
        best.append((s, feats[i], float(V[i, j])))
    best.sort(key=lambda t: -abs(t[2]))
    stats['top_sens_feat_pairs'] = [
        {'sens': a, 'feat': b, 'rho': round(c, 4)} for a, b, c in best[:10]]

    print(f'  {stats["n_cells"]} 个格（226 特征 × 50 感官）；|rho| 中位 {stats["median_abs"]:.4f}')
    print(f'  |rho|>0.3 的 {stats["n_abs_gt_0.3"]} 格，'
          f'>0.5 的 {stats["n_abs_gt_0.5"]} 格，>0.7 的 {stats["n_abs_gt_0.7"]} 格')
    print('  各感官维最强特征（前 6）：')
    for a, b, c in best[:6]:
        print(f'    {a:20s} <- {b:32s} rho={c:+.3f}')
    return stats, C


# ============================================================ 4. 风格间差异
def style_kruskal(X, meta, feats):
    """Kruskal-Wallis：该特征在 22 个风格间是否有分布差异。
    eps^2 = (H - k + 1) / (n - k)，对异常值稳健的效应量。
    """
    from scipy.stats import kruskal
    hr('4. 风格间差异（Kruskal-Wallis + eps²）')
    styles = meta['tasting_category_fine'].astype(str)
    counts = styles.value_counts()
    # 样本数 < 3 的组统计功效极低，保留但单列标记
    groups_all = list(counts.index)

    rows = []
    for f in feats:
        v = X[f]
        buckets, used = [], []
        for g in groups_all:
            s = v[styles == g].dropna().to_numpy(float)
            if len(s) >= 2:
                buckets.append(s)
                used.append(g)
        k = len(buckets)
        n = int(sum(len(b) for b in buckets))
        if k < 3 or n <= k + 2:
            rows.append(dict(feat=f, H=np.nan, p=np.nan, eps2=np.nan,
                             n_groups=k, n_samples=n, n_groups_ge5=0))
            continue
        try:
            H, p = kruskal(*buckets)
        except ValueError:
            H, p = np.nan, np.nan
        eps2 = (H - k + 1) / (n - k) if np.isfinite(H) else np.nan
        rows.append(dict(feat=f, H=float(H), p=float(p), eps2=float(eps2),
                         n_groups=k, n_samples=n,
                         n_groups_ge5=int(sum(1 for b in buckets if len(b) >= 5))))

    out = pd.DataFrame(rows).sort_values('eps2', ascending=False).reset_index(drop=True)
    out.to_csv(os.path.join(RES, 'q0_style_kruskal.csv'), index=False,
               encoding='utf-8-sig', float_format='%.6f')

    valid = out.dropna(subset=['p'])
    stats = {
        'n_features': len(out),
        'n_tested': int(len(valid)),
        'n_sig_05': int((valid.p < 0.05).sum()),
        'n_sig_bonferroni': int((valid.p < 0.05 / max(len(valid), 1)).sum()),
        'median_eps2': float(valid.eps2.median()),
        'max_eps2': float(valid.eps2.max()),
        'n_eps2_gt_0.14': int((valid.eps2 > 0.14).sum()),   # 大效应量惯例阈值
        'n_styles': int(len(groups_all)),
        'style_sizes': {str(k): int(v) for k, v in counts.items()},
    }
    print(f'  {stats["n_styles"]} 个风格，样本量 {counts.min()}–{counts.max()}（中位 {int(counts.median())}）')
    print(f'  可检验特征 {stats["n_tested"]}/{len(out)}；p<0.05 的 {stats["n_sig_05"]} 个，'
          f'Bonferroni 后 {stats["n_sig_bonferroni"]} 个')
    print(f'  eps² 中位 {stats["median_eps2"]:.4f}，最大 {stats["max_eps2"]:.4f}；'
          f'eps²>0.14（大效应）的 {stats["n_eps2_gt_0.14"]} 个')
    print('  效应量最大的 6 个特征：')
    for _, r in out.dropna(subset=['eps2']).head(6).iterrows():
        print(f'    {r.feat:32s} eps²={r.eps2:.4f}  H={r.H:8.2f}  p={r.p:.3e}')
    return stats, out


# ============================================================ 5. 绘图数据落盘
def dump_plot_data(X, feats, S):
    """绘图脚本只许读 results/ 下的落盘文件，不许碰原始数据、不许现算统计量
    （figure-contract 的 Source data 规则）。所以这里把三张图要用的原始矩阵与
    聚合量一次性倒出来，figures.py 只做转置/排序这类显示层操作。
    """
    hr('6. 绘图数据落盘（供 figures.py 只读消费）')
    out = {}

    # (a) 33 个"原始线性浓度"列的原始值矩阵 —— 箱线图 raw/log10 双面板要用真数据
    lin = [f for f in feats if f not in LOG10_COLS]
    raw = X[lin].copy()
    raw.insert(0, 'beer', raw.index)
    raw.to_csv(os.path.join(RES, 'q0_box_raw.csv'), index=False,
               encoding='utf-8-sig', float_format='%.6g')
    out['box_raw_cols'] = len(lin)
    print(f'  q0_box_raw.csv：{len(lin)} 个线性列 × {len(X)} 样本')

    # (b) 缺失 / 地板值结构
    rows = []
    for f in feats:
        v = X[f]
        nn = v.dropna()
        if len(nn) == 0:
            continue
        vc = nn.value_counts()
        rows.append(dict(
            feat=f,
            missing_n=int(v.isna().sum()),
            missing_pct=round(float(v.isna().mean() * 100), 3),
            mode_share=round(float(vc.iloc[0] / len(nn)), 4),
            mode_value=round(float(vc.index[0]), 6),
            n_unique=int(nn.nunique()),
            is_log10=f in LOG10_COLS,
        ))
    fl = pd.DataFrame(rows)
    fl.to_csv(os.path.join(RES, 'q0_floor_share.csv'), index=False,
              encoding='utf-8-sig')
    out['n_missing_cols'] = int((fl.missing_n > 0).sum())
    out['n_floor_gt30'] = int((fl.mode_share >= 0.30).sum())
    out['max_floor_share'] = float(fl.mode_share.max())
    print(f'  q0_floor_share.csv：有缺失的 {out["n_missing_cols"]} 列；'
          f'同一取值占比 ≥30% 的 {out["n_floor_gt30"]} 列（最大 {out["max_floor_share"]:.1%}）')

    # (c) 相关矩阵的出图排序：按 origin_paper 分组连续排列，暴露块结构
    _, grp = _load_groups(feats)
    order = sorted(range(len(feats)), key=lambda i: (grp[feats[i]], feats[i]))
    pd.DataFrame(dict(
        feat=[feats[i] for i in order],
        group=[grp[feats[i]] for i in order],
        pos=list(range(len(order))),
    )).to_csv(os.path.join(RES, 'q0_corr_order.csv'), index=False,
              encoding='utf-8-sig')
    out['n_groups'] = int(len(set(grp[f] for f in feats)))
    print(f'  q0_corr_order.csv：按 {out["n_groups"]} 个 origin_paper 组连续排序')

    with open(os.path.join(RES, 'q0_plotdata.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def _load_groups(feats):
    """origin_paper 分组，口径与 q2.py:135 一致（field_name_R → norm_key）。"""
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(DATA, '8.xlsx'),
                                read_only=True, data_only=True)
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
    return thr, grp


# ============================================================ 6. 官方表交叉验证
def crosscheck(S, C, feats, sens):
    """官方 2.csv 是 231×231 相关矩阵、6.csv 是 44×50 特征↔感官。
    它们覆盖不全，但能验证我们自算的口径没走样。

    名字桥：8.xlsx 的 chemical_name_short / field_name_python / CleanName_PanelFeedback
    （见 build_name_maps）。2.csv 231 行实测 212 行可对应，6.csv 44 行 43 行。
    """
    hr('5. 与官方 2.csv / 6.csv 交叉验证')
    out = {}
    chem2feat, sens2panel = build_name_maps()

    p2 = os.path.join(DATA, '2.csv')
    if os.path.exists(p2):
        o = pd.read_csv(p2, index_col=0)
        # 官方表的行/列名 → 我方 feat 名
        row2feat = {i: chem2feat.get(norm_key(i)) for i in o.index}
        col2feat = {c: chem2feat.get(norm_key(c)) for c in o.columns}
        n_mapped = sum(1 for f in row2feat.values() if f in S.index)

        diffs, ov, mv = [], [], []
        for io in o.index:
            fa = row2feat.get(io)
            if fa not in S.index:
                continue
            for co in o.columns:
                fb = col2feat.get(co)
                if fb not in S.columns or fb == fa:
                    continue
                vo = pd.to_numeric(o.at[io, co], errors='coerce')
                if not np.isfinite(vo):
                    continue
                vm = float(S.loc[fa, fb])
                if not np.isfinite(vm):
                    continue
                diffs.append(abs(float(vo) - vm))
                ov.append(float(vo))
                mv.append(vm)
        if diffs:
            out['official_2csv'] = {
                'n_rows_official': int(len(o)),
                'n_rows_mapped_to_226': int(n_mapped),
                'n_compared_pairs': int(len(diffs)),
                'median_abs_diff': float(np.median(diffs)),
                'p90_abs_diff': float(np.percentile(diffs, 90)),
                'max_abs_diff': float(np.max(diffs)),
                'pearson_agreement': float(np.corrcoef(ov, mv)[0, 1]),
            }
            st = out['official_2csv']
            print(f'  2.csv：{st["n_rows_official"]} 行，'
                  f'{st["n_rows_mapped_to_226"]} 行映到我方 226 特征；'
                  f'比对 {st["n_compared_pairs"]} 对')
            print(f'    中位绝对差 {st["median_abs_diff"]:.4f}，'
                  f'P90 {st["p90_abs_diff"]:.4f}，最大 {st["max_abs_diff"]:.4f}，'
                  f'相关系数 {st["pearson_agreement"]:.4f}')
        else:
            out['official_2csv'] = {'error': '无可比对对'}
            print('  2.csv：无可比对对')

    p6 = os.path.join(DATA, '6.csv')
    if os.path.exists(p6):
        o6 = pd.read_csv(p6, index_col=0)
        row2feat = {i: chem2feat.get(norm_key(i)) for i in o6.index}
        panel2sens = {v.strip(): k for k, v in sens2panel.items()}
        col2sens = {c: panel2sens.get(str(c).replace('\r', '').replace('\n', '').strip())
                    for c in o6.columns}

        diffs, ov, mv = [], [], []
        for io in o6.index:
            f = row2feat.get(io)
            if f not in C.index:
                continue
            for co in o6.columns:
                s = col2sens.get(co)
                if s is None or s not in C.columns:
                    continue
                vo = pd.to_numeric(o6.at[io, co], errors='coerce')
                if not np.isfinite(vo):
                    continue
                vm = float(C.loc[f, s])
                if not np.isfinite(vm):
                    continue
                diffs.append(abs(float(vo) - vm))
                ov.append(float(vo))
                mv.append(vm)
        out['official_6csv'] = {
            'n_rows': int(len(o6)),
            'n_rows_mapped': int(sum(1 for f in row2feat.values() if f in C.index)),
            'n_cols': int(o6.shape[1]),
            'n_cols_mapped': int(sum(1 for s in col2sens.values() if s in C.columns)),
            'n_compared_cells': int(len(diffs)),
            'median_abs_diff': float(np.median(diffs)) if diffs else None,
            'pearson_agreement': float(np.corrcoef(ov, mv)[0, 1]) if len(diffs) > 2 else None,
            'coverage_of_226x50': round(len(diffs) / (len(feats) * len(sens)), 4),
        }
        st = out['official_6csv']
        print(f'  6.csv：{st["n_rows"]}×{st["n_cols"]}，'
              f'行映到 {st["n_rows_mapped"]}、列映到 {st["n_cols_mapped"]}')
        print(f'    比对 {st["n_compared_cells"]} 格'
              f'（占 226×50 的 {st["coverage_of_226x50"]:.1%}），'
              f'中位绝对差 {st["median_abs_diff"]:.4f}，'
              f'相关系数 {st["pearson_agreement"]:.4f}')

    with open(os.path.join(RES, 'q0_crosscheck.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


# ============================================================ main
def main():
    t0 = time.time()
    print('Q0 · 变量关系体检（只读，不重训模型）')

    X, Y, meta, feats, sens = load()
    print(f'样本 {X.shape[0]} | 特征 {X.shape[1]} | 靶 {Y.shape[1]} | '
          f'风格 {meta.tasting_category_fine.nunique()}')
    print(f'log10 列 {sum(1 for f in feats if f in LOG10_COLS)} | '
          f'真 NA 格 {int(X.isna().sum().sum())}（{int((X.isna().sum() > 0).sum())} 列）')

    corr_stats, S, Sp = feat_corr(X, feats)
    vif_stats, _ = vif_rank(X, feats)
    sens_stats, C = sens_corr(X, Y, feats, sens)
    style_stats, _ = style_kruskal(X, meta, feats)
    plot_stats = dump_plot_data(X, feats, S)
    check = crosscheck(S, C, feats, sens)

    summary = {
        'n_samples': int(X.shape[0]),
        'n_features': len(feats),
        'n_sensory': len(sens),
        'n_styles': int(meta.tasting_category_fine.nunique()),
        'n_log10_cols': int(sum(1 for f in feats if f in LOG10_COLS)),
        'n_true_na_cells': int(X.isna().sum().sum()),
        'n_true_na_cols': int((X.isna().sum() > 0).sum()),
        'feature_corr': corr_stats,
        'collinearity': {k: v for k, v in vif_stats.items()
                         if k not in ('eigenvalues_top20',)},
        'feature_sens_corr': sens_stats,
        'style_kruskal': {k: v for k, v in style_stats.items() if k != 'style_sizes'},
        'plot_data': plot_stats,
        'crosscheck': check,
    }
    with open(os.path.join(RES, 'q0_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    hr('完成')
    print(f'  耗时 {time.time() - t0:.1f} s')
    print(f'  输出 12 个文件 → {RES}')
    print('    q0_corr_feat.csv / q0_corr_top.csv / q0_vif.csv / '
          'q0_effective_rank.json')
    print('    q0_sens_corr.csv / q0_style_kruskal.csv / q0_crosscheck.json / '
          'q0_summary.json')


if __name__ == '__main__':
    main()
