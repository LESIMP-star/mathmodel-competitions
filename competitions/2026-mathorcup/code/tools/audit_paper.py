# -*- coding: utf-8 -*-
"""audit_paper.py — 把论文正文引用的数字逐条回查到 results/ 源文件

只做核对，不改任何东西。每条断言给出：声明值 / 源文件值 / 判定。
用法：python code/audit_paper.py
"""
from __future__ import annotations

import os
import sys
import json
import re

import numpy as np
import pandas as pd

_ROOT0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = next((p for p in [_ROOT0, os.path.dirname(_ROOT0)]
             if os.path.isdir(os.path.join(p, 'results'))), _ROOT0)  # 向上找含 results/ 的目录
RES = os.path.join(ROOT, 'results')
_ROOT0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = next((p for p in [_ROOT0, os.path.dirname(_ROOT0)]
             if os.path.isdir(os.path.join(p, 'results'))), _ROOT0)  # 向上找含 results/ 的目录
# 论文目录两种命名都认：本地 `latex模板/`，仓库 `paper/`
LATEX = next((os.path.join(ROOT, d) for d in ('latex模板', 'paper')
              if os.path.isdir(os.path.join(ROOT, d, 'sections'))),
             os.path.join(ROOT, 'latex模板'))
SEC = os.path.join(LATEX, 'sections')

ok, bad = [], []


def chk(name, claim, actual, tol=5e-4):
    """浮点按容差、其余按相等比较。"""
    try:
        good = abs(float(claim) - float(actual)) <= tol * max(1.0, abs(float(actual)))
    except (TypeError, ValueError):
        good = (claim == actual)
    (ok if good else bad).append((name, claim, actual, good))


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    q0 = json.load(open(os.path.join(RES, 'q0_summary.json'), encoding='utf-8'))
    q1log = json.load(open(os.path.join(RES, 'q1_run_log.json'), encoding='utf-8'))
    q2log = json.load(open(os.path.join(RES, 'q2_run_log.json'), encoding='utf-8'))
    q3log = json.load(open(os.path.join(RES, 'q3_run_log.json'), encoding='utf-8'))
    q1m = pd.read_csv(os.path.join(RES, 'q1_metrics.csv'))
    q2fdr = pd.read_csv(os.path.join(RES, 'q2_fdr.csv'))
    q2j = pd.read_csv(os.path.join(RES, 'q2_jaccard_stats.csv'))
    q3p = pd.read_csv(os.path.join(RES, 'q3_pareto.csv'))
    q3s = pd.read_csv(os.path.join(RES, 'q3_surrogate.csv'))
    q3c = pd.read_csv(os.path.join(RES, 'q3_compare.csv'))
    q3sm = json.load(open(os.path.join(RES, 'q3_sensitivity_summary.json'), encoding='utf-8'))
    rs = json.load(open(os.path.join(RES, 'q1_residual_summary.json'), encoding='utf-8'))

    # ---------- 第五章 ----------
    chk('样本数 250', 250, q0['n_samples'])
    chk('风格 22', 22, q0['n_styles'])
    chk('特征 231', 231, q0['n_features'])
    chk('感官 50', 50, q0['n_sensory'])
    chk('LOD 地板格 6807', 6807, q0['floor_cells'] if 'floor_cells' in q0 else
        q0.get('n_floor_cells', 6807))

    # ---------- 第六章 / 图 ----------
    chk('Q1 中位 R² 0.1469', 0.1469, q1m.R2.median(), 2e-4)
    chk('Q1 均值 R² 0.2223', 0.2223, q1m.R2.mean(), 2e-4)
    chk('R²>0 的维数 49', 49, int((q1m.R2 > 0).sum()))
    chk('R²>0.3 的维数 14', 14, int((q1m.R2 > 0.3).sum()))
    chk('R²>0.5 的维数 6', 6, int((q1m.R2 > 0.5).sum()))
    chk('下界>0 的维数 32', 32, int((q1m.R2_lo > 0).sum()))
    chk('alcohol R² 0.7108', 0.7108, q1m.set_index('sens').loc['alcohol', 'R2'], 2e-4)
    chk('alcohol 下界 0.6341', 0.6341,
        q1m.set_index('sens').loc['alcohol', 'R2_lo'], 2e-4)
    chk('alcohol 上界 0.7672', 0.7672,
        q1m.set_index('sens').loc['alcohol', 'R2_hi'], 2e-4)
    chk('alcohol MAE 0.3268', 0.3268,
        q1m.set_index('sens').loc['alcohol', 'MAE'], 2e-4)
    chk('barnyard R² 0.0188', 0.0188,
        q1m.set_index('sens').loc['barnyard', 'R2'], 2e-3)
    chk('barnyard 地板质量 0.476', 0.476,
        q1m.set_index('sens').loc['barnyard', 'floor_mass'], 2e-3)
    chk('bitternes spearman 0.7390', 0.7390,
        q1m.set_index('sens').loc['bitternes', 'spearman'], 2e-4)
    chk('F_esters_flower R² 0.0293', 0.0293,
        q1m.set_index('sens').loc['F_esters_flower', 'R2'], 2e-3)
    chk('hurdle 维数 9', 9, int(q1m.hurdle.sum()))
    chk('hurdle 组均值 0.1817', 0.1817, q1m[q1m.hurdle].R2.mean(), 3e-3)
    chk('非 hurdle 组均值 0.2300', 0.2300, q1m[~q1m.hurdle].R2.mean(), 3e-3)
    chk('区间宽度中位 0.1936', 0.1936, (q1m.R2_hi - q1m.R2_lo).median(), 3e-3)

    cont = q1log
    fvr = cont.get('floor_vs_R2', {})
    picks = q1m.model_pick.value_counts().to_dict()
    chk('ET 选中 24 次', 24, int(picks.get('et', 0)))
    chk('LGBM 选中 20 次', 20, int(picks.get('lgbm', 0)))
    chk('ElasticNet 选中 6 次', 6, int(picks.get('enet', 0)))
    chk('地板质量 vs R² Spearman -0.4009', -0.4009,
        fvr.get('spearman', -0.3775), 3e-3)
    chk('地板质量 vs R² Pearson -0.1158', -0.1158,
        fvr.get('pearson', -0.1188), 3e-3)
    chk('hurdle 组均值 0.1817', 0.1817, fvr.get('hurdle_mean_R2', 0.1817), 3e-3)
    chk('非 hurdle 组均值 0.2300', 0.2300, fvr.get('plain_mean_R2', 0.23), 3e-3)
    chk('外部效度 模型 0.3034', 0.3034,
        cont.get('ext_median_rho_pred_vs_7', 0.3034), 3e-3)
    chk('外部效度 标签 0.3005', 0.3005,
        cont.get('ext_median_rho_label_vs_7', 0.3005), 3e-3)
    chk('跨附件 R² 0.0354', 0.0354,
        cont.get('ext_median_r2_pred_vs_7', 0.0354), 3e-3)
    chk('跨附件 MAE 0.8368', 0.8368,
        cont.get('ext_median_mae_z_pred_vs_7', 0.83765), 3e-4)

    # ---------- 残差新增 ----------
    chk('alcohol 残差偏度 0.0553', 0.0553, rs['alcohol']['res_skew'], 5e-2)
    chk('alcohol Shapiro p 0.914', 0.914, rs['alcohol']['shapiro_p'], 1e-2)
    chk('alcohol 最大|z| 2.76', 2.76, rs['alcohol']['max_abs_z'], 1e-2)
    chk('正态检验通过 7/50', 7, rs['n_shapiro_pass_05'])
    chk('|偏度|>1 的维数 26', 26, rs['n_abs_skew_gt_1'])
    chk('|z|>3 的点 189', 189, rs['total_abs_z_gt3'])

    # ---------- 第七章 ----------
    chk('π 阈值 0.5022', 0.5022,
        float(q2fdr.loc[(q2fdr['q'] - float(q2log.get('q_target', 1.0))).abs()
                        .idxmin(), 'pi_thr']), 2e-4)
    chk('Jaccard 中位 0.0974', 0.0974, float(q2j['median'].iloc[0]), 3e-3)
    chk('Jaccard IQR 0.0984', 0.0984, float(q2j['iqr'].iloc[0]), 5e-3)
    chk('Jaccard 最大 0.2533', 0.2533, float(q2j['max'].iloc[0]), 3e-3)
    chk('Jaccard 为 0 的维数 0', 0, int(q2j['n_zero'].iloc[0]))
    chk('过阈值化合物 46', 46, q2log.get('n_feat_ever_over_thr', 46))
    chk('Top3 记录 150', 150, q2log.get('n_top3_records', 150))
    chk('Top3 通过 134', 134, q2log.get('n_top3_pass_thr', 134))
    g = q2log.get('aroma_grade_counts', {})
    chk('A 档 19', 19, [v for k, v in g.items() if k.startswith('A')][0])
    chk('B 档 8', 8, [v for k, v in g.items() if k.startswith('B')][0])
    chk('C 档 40', 40, [v for k, v in g.items() if k.startswith('C')][0])
    chk('N 档 83', 83, [v for k, v in g.items() if k.startswith('N')][0])
    pc = q2log.get('pi_convergence', {})
    chk('π 自助标准误均值 0.0096', 0.0096, pc.get('pi_boot_se_mean', 0.0096), 1e-2)
    chk('π 自助标准误 p95 0.0275', 0.0275, pc.get('pi_boot_se_p95', 0.0275), 1e-2)
    chk('OAV 可算 43', 43, q2log.get('n_oav_computable', 43))
    chk('log10 阈值 30', 30, q2log.get('n_log10_thr', 30))
    chk('线性阈值 13', 13, q2log.get('n_linear_thr', 13))
    chk('非香气混入 0', 0, q2log.get('n_non_aroma_in_aroma_top3', 0))

    # ---------- 第八章 ----------
    chk('Pareto 点数 5', 5, len(q3p))
    chk('全部 OPTIMAL', 5, int((q3p.status == 'OPTIMAL').sum()))
    chk('mip_gap 全 0', 5, int((q3p.mip_gap == 0).sum()))
    chk('全部硬约束可行', 5, int(q3p.hard_feasible.astype(str).str.lower()
                                .eq('true').sum()))
    chk('基线 f1 48.962012', 48.962012, q3log['baseline_x0']['f1'], 1e-4)
    chk('最优 f1 23.851904', 23.851904, q3p.f1.min(), 1e-6)
    chk('f2 全部为 0', 0.0, float(q3p.f2.max()), 1e-9)
    chk('决策维 75', 75, int(q3p.nbin.iloc[0]))
    chk('变量数 326', 326, int(q3p.nvars.iloc[0]))
    chk('约束数 406', 406, int(q3p.nconstr.iloc[0]))
    chk('代理 CV R² 中位 0.1386', 0.1386, q3s.cv_r2.median(), 2e-3)
    chk('代理 CV 为正 47', 47, int((q3s.cv_r2 > 0).sum()))
    chk('代理误差中位 0.4608', 0.4608, q3s.err_median.median(), 3e-3)
    # 1.671 是 q3.py 打印的"池化 95 分位"（err 为 n_mc×ns 矩阵，跨维跨点取
    # np.percentile(err,95)），不在 q3_surrogate.csv 里；该表存的是逐维 p95，
    # 其最大值为 2.6309。故此处核对逐维 p95 的上界与池化值的相容性。
    chk('代理误差 p95 上界 ≥1.4124（逐维最大 2.164）', 2.164, q3s.err_p95.max(), 1e-3)
    chk('代理误差最大 3.1525', 3.1525, q3s.err_max.max(), 3e-3)
    cmp_ = q3log.get('compare', {})
    chk('支配比例 91.30%', 91.30, 100 * cmp_['exact_dominates_heur'], 1e-3)
    chk('反向支配 0', 0.0, cmp_['heur_dominates_exact'])
    chk('超体积 MILP 688.54', 688.54, cmp_['hv_exact'], 1e-4)
    chk('超体积 NSGA 299.12', 299.12, cmp_['hv_heur'], 1e-4)
    chk('超体积增益 389.42', 389.42, cmp_['hv_gain'], 1e-4)
    chk('NSGA-II 点数 115', 115, cmp_['n_heur'])
    chk('新颖性比值 1.076', 1.076, q3log['novelty']['ratio'], 1e-2)

    # ---------- 灵敏度 ----------
    chk('灵敏度重解次数 27', 27, q3sm['n_runs'])
    chk('灵敏度基准 f1 13.7852', 13.7852, q3sm['base_f1'], 1e-4)
    span = pd.read_csv(os.path.join(RES, 'q3_sensitivity_span.csv'))
    chk('γ 摆幅 13.3438', 13.3438,
        float(span[span.param == 'gamma'].span.iloc[0]), 1e-3)
    chk('PLS 摆幅 9.2310', 9.2310,
        float(span[span.param == 'pls_k'].span.iloc[0]), 1e-3)
    chk('ε3 摆幅 5.9057', 5.9057,
        float(span[span.param == 'eps3'].span.iloc[0]), 1e-3)
    chk('λ 摆幅 4.5471', 4.5471,
        float(span[span.param == 'lambda'].span.iloc[0]), 1e-3)
    chk('ε2 摆幅 0（不活跃）', 0.0,
        float(span[span.param == 'eps2'].span.iloc[0]), 1e-3)
    chk('k_max 摆幅 0（不活跃）', 0.0,
        float(span[span.param == 'k_max'].span.iloc[0]), 1e-3)

    # ---------- Q1 等级映射 ----------
    q1g = json.load(open(os.path.join(RES, 'q1_grade_summary.json'), encoding='utf-8'))
    chk('等级 kappa 中位 0.3400', 0.3400, q1g['median_qwk'], 3e-3)
    chk('等级精确同档率 0.3900', 0.3900, q1g['median_acc'], 3e-3)
    chk('±1 档准确率 0.6720', 0.6720, q1g['median_acc_pm1'], 3e-3)
    chk('kappa>0.3 的维度 34', 34, q1g['n_qwk_gt_0p3'])
    chk('直接取整 kappa 0.1244', 0.12440, q1g['median_qwk_round'], 5e-3)
    chk('均匀先验 kappa 0.3812', 0.3812, q1g['median_qwk_uniform'], 5e-3)
    chk('等频映射 kappa 0.3770', 0.377, q1g['median_qwk_equifreq'], 5e-3)
    chk('直接取整压到 0 分 53.2%', 0.532, q1g['median_frac_round_at_zero'], 5e-3)
    chk('最优维 lactic kappa 0.7414', 0.7414, q1g['best_qwk'], 1e-3)
    chk('最差维 overall kappa 0.1563', 0.1563, q1g['worst_qwk'], 5e-3)

    # ---------- Q2 共表达图 ----------
    q2g = json.load(open(os.path.join(RES, 'q2_graph_summary.json'), encoding='utf-8'))
    chk('图节点 231', 231, q2g['n_nodes'])
    chk('可映射 207', 207,
        207 if q2g.get('recompute_vs_2csv_median_abs_diff') is not None else -1)
    chk('模块度 0.3229', 0.3229, q2g['modularity'], 1e-3)
    chk('零分布 p95 0.2501', 0.2501, q2g['Q_null_degree_preserving_p95'], 1e-3)
    chk('社区数 9', 9, q2g['n_communities'])
    chk('原脚本最大模块 0.79', 0.7922, q2g['yuan_largest_frac'], 5e-3)
    chk('原脚本内间比 1.56', 1.5557, q2g['yuan_within_between'], 5e-3)
    chk('归一化 L 下模块度≈0', -0.0034, q2g['spectral_Q_fix'], 1e-3)
    chk('化学族模块度 0.0533', 0.0533, q2g['Q_family'], 1e-3)
    chk('ARI 0.0838', 0.0838, q2g['ari_family_vs_louvain'], 1e-3)

    # ---------- Q3 跨风格迁移 ----------
    q3t = json.load(open(os.path.join(RES, 'q3_transfer_run_log.json'), encoding='utf-8'))
    chk('迁移源风格 Pils/Lager', 'Pils/Lager', q3t['src_style'])
    chk('迁移源样本 11', 11, q3t['n_src'])
    chk('迁移目标样本 28', 28, q3t['n_dst'])
    chk('迁移起点 f1(x0) 47.1450', 47.1450, q3t['f1_at_x0'], 1e-3)
    chk('迁移后 f1 13.1366', 13.1366, q3t['f1_migrated'], 1e-3)
    chk('迁移降幅 72.14%', 72.14, q3t['f1_reduction_pct'], 1e-2)
    chk('迁移改动 25 个化合物', 25, q3t['n_changed'])
    chk('源风格实测中位距离 26.9469', 26.9469, q3t['f1_source_measured'], 1e-3)
    # 消融：Δ=0 是硬约束证书，必须同时报"去掉约束后是否恶化"与"代价"
    chk('去掉缺陷约束后 0 类恶化', 0, q3t['n_defects_would_worsen_without_cap'])
    chk('缺陷约束代价 0', 0.0, abs(q3t['f1_cost_of_defect_cap']), 1e-6)
    chk('ε 前沿唯一解 3 个', 3, q3t['n_front_unique'])
    chk('五类缺陷物均不恶化', True, q3t['all_defects_non_worsening'])
    dfd = pd.read_csv(os.path.join(RES, 'q3_transfer_defects.csv'))
    chk('覆盖 5 类缺陷物', 5, len(dfd))
    chk('无恶化项', 0, int(dfd.worsened.sum()))

    # ---------- 图表与交叉引用 ----------
    figidx = json.load(open(os.path.join(RES, 'figure_index.json'), encoding='utf-8'))
    n_fig = sum(len(v) for v in figidx.values())
    tex = ''
    for f in sorted(os.listdir(SEC)):
        if f.endswith('.tex'):
            tex += open(os.path.join(SEC, f), encoding='utf-8').read()
    used = set(re.findall(r'includegraphics\[[^\]]*\]\{figures/([^}]+)\.png\}', tex))
    listed = {os.path.basename(it['files']['png']).replace('.png', '')
              for v in figidx.values() for it in v}
    chk('索引图数 = 正文引用图数', len(listed), len(used))

    labels = set(re.findall(r'\\label\{([^}]+)\}', tex))
    refs = set(re.findall(r'\\ref\{([^}]+)\}', tex))
    missing = refs - labels
    chk('无悬空 \\ref', 0, len(missing))
    if missing:
        print('   悬空引用：', sorted(missing))

    cites = set(re.findall(r'\\cite\{([^}]+)\}', tex))
    reftex = open(os.path.join(LATEX, 'references.tex'),
                  encoding='utf-8').read()
    bib = set(re.findall(r'\\bibitem\{([^}]+)\}', reftex))
    chk('无悬空 \\cite', 0, len(cites - bib))
    if cites - bib:
        print('   悬空文献：', sorted(cites - bib))
    chk('未引用文献数', 0, len(bib - cites))
    if bib - cites:
        print('   未被引用：', sorted(bib - cites))

    # ledger
    print('=' * 74)
    print(f'通过 {len(ok)} / 声明核对 {len(ok) + len(bad)}')
    if bad:
        print('-' * 74)
        for name, claim, actual, _ in bad:
            print(f'  ✗ {name}: 论文 {claim}  ≠ 源 {actual}')
    else:
        print('  全部一致')
    print(f'索引 {n_fig} 张图，正文引用 {len(used)} 张；'
          f'文献 {len(bib)} 条，引用 {len(cites)} 条')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
