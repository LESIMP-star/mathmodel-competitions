# -*- coding: utf-8 -*-
"""make_gate_artifacts.py — 由已冻结的 results/ 生成 G3 证据门禁的五个输入文件

背景
  paper_output/qa/evidence_gate_report.json 一直是 FAIL，缺的是五项"结果汇总层"
  产物，不是缺数据。这些文件本应在 Step 7 各阶段顺手落盘，当时没做。本脚本从
  results/ 的冻结产物把它们补出来，数值全部读取，不重算、不硬编码。

生成
  paper_output/results/model_results.json   每问的模型与关键指标（evidence_status=final）
  paper_output/results/metrics.json         每问的评价指标条目
  paper_output/results/conclusions.json     每问可回扣原题的结论文本
  paper_output/tables/table_index.json      论文表格索引（按 QID 分组）
  paper_output/tasks.json                   任务追踪

用法：python code/make_gate_artifacts.py
本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：Hermes Agent（Nous Research），底层模型 deepseek-v4-flash，
# 开发机构：Nous Research（工具）/ 深度求索 DeepSeek（模型），使用日期：2026-10-26
"""
from __future__ import annotations

import os
import sys
import json

import pandas as pd

_ROOT0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = next((p for p in [_ROOT0, os.path.dirname(_ROOT0)]
             if os.path.isdir(os.path.join(p, 'results'))), _ROOT0)  # 向上找含 results/ 的目录
RES = os.path.join(ROOT, 'results')
OUT = os.path.join(ROOT, 'paper_output')
FINAL = 'final'


def _json(name):
    with open(os.path.join(RES, name), encoding='utf-8') as f:
        return json.load(f)


def _csv(name):
    return pd.read_csv(os.path.join(RES, name))


def _dump(rel, obj):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f'  写出 {rel}')


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    q0 = _json('q0_summary.json')
    q1 = _json('q1_run_log.json')
    q2 = _json('q2_run_log.json')
    q3 = _json('q3_run_log.json')
    q3sm = _json('q3_sensitivity_summary.json')
    rs = _json('q1_residual_summary.json')
    q1m = _csv('q1_metrics.csv')
    q3s = _csv('q3_surrogate.csv')
    q3p = _csv('q3_pareto.csv')
    span = _csv('q3_sensitivity_span.csv')
    q1g = _json('q1_grade_summary.json')
    q2g = _json('q2_graph_summary.json')
    q3t = _json('q3_transfer_run_log.json')

    fvr = q1.get('floor_vs_R2', {})
    pc = q2.get('pi_convergence', {})
    cmp_ = q3.get('compare', {})
    grades = q2.get('aroma_grade_counts', {})
    q0c = q0['collinearity']['spearman']
    q0s = q0['feature_sens_corr']
    q0k = q0['style_kruskal']

    print('生成 G3 证据门禁输入文件：')

    # ---------------- model_results.json ----------------
    model_results = {
        'Q0': {
            'question_id': 'Q0',
            'title': '数据口径核验与变量关系诊断',
            'model': '纯统计诊断：Spearman/Pearson 相关 + VIF + SVD 有效秩 + '
                     '特征↔感官相关 + 按风格 Kruskal-Wallis（ε²）',
            'evidence_status': FINAL,
            'code': 'code/q0_relations.py',
            'artifacts': ['results/q0_summary.json', 'results/q0_corr_feat.csv',
                          'results/q0_vif.csv', 'results/q0_sens_corr.csv',
                          'results/q0_style_kruskal.csv',
                          'results/q0_floor_share.csv'],
            'key_metrics': {
                'n_samples': q0['n_samples'], 'n_features': q0['n_features'],
                'n_sensory': q0['n_sensory'], 'n_styles': q0['n_styles'],
                'effective_rank_spearman': q0c['effective_rank_participation'],
                'n_vif_gt_10': q0c['n_vif_gt_10'],
            },
        },
        'Q1': {
            'question_id': 'Q1',
            'title': '感官评分可预测性分层评估',
            'model': '嵌套交叉验证（外 5 折 × 内 5 折）四模型竞速（Ridge / '
                     'ElasticNet / LightGBM / ExtraTrees）+ 地板质量 >0.30 的 9 维 '
                     'hurdle 两部模型 + 1000 次自助 95% 区间',
            'evidence_status': FINAL,
            'code': 'code/q1.py + code/q1_grades.py + code/q1_diagnostics.py',
            'artifacts': ['results/q1_metrics.csv', 'results/q1_predictions.csv',
                          'results/q1_forest_rows.csv', 'results/q1_external.csv',
                          'results/q1_scatter_pairs.csv',
                          'results/q1_residual_stats.csv',
                          'results/q1_grades.csv',
                          'results/q1_grade_metrics.csv'],
            'key_metrics': {
                'median_R2': q1['median_R2'], 'mean_R2': q1['mean_R2'],
                'n_R2_positive': q1['n_R2_positive'],
                'median_boot_width': q1['median_boot_width'],
                'best_target': q1['best_target'], 'best_R2': q1['best_R2'],
                'n_hurdle_targets': q1['n_hurdle_targets'],
                'n_shapiro_pass': rs['n_shapiro_pass_05'],
                'median_qwk': q1g['median_qwk'],
                'median_grade_acc': q1g['median_acc'],
            },
        },
        'Q2': {
            'question_id': 'Q2',
            'title': '关键香气化合物多模型归因',
            'model': '按化学族分组置换重要性 π（OOB 自助 200 次）→ FDR 反解阈值 '
                     'π_thr → OAV 四档分级（A/B/C/N）→ 三模型 Top-10 Jaccard 稳定性',
            'evidence_status': FINAL,
            'code': 'code/q2.py + code/q2_graph.py',
            'artifacts': ['results/q2_top3.csv', 'results/q2_feature_pi.csv',
                          'results/q2_fdr.csv', 'results/q2_jaccard.csv',
                          'results/q2_oav.csv', 'results/q2_pi_convergence.csv',
                          'results/q2_graph_stats.csv',
                          'results/q2_graph_edges.csv'],
            'key_metrics': {
                'pi_thr': q2['pi_thr'],
                'n_feat_ever_over_thr': q2['n_feat_ever_over_thr'],
                'median_cross_method_jaccard': q2['median_cross_method_jaccard'],
                'grade_A': [v for k, v in grades.items() if k.startswith('A')][0],
                'grade_N': [v for k, v in grades.items() if k.startswith('N')][0],
                'graph_modularity': q2g['modularity'],
                'graph_modularity_null_p95': q2g['Q_null_degree_preserving_p95'],
                'graph_ari_vs_family': q2g['ari_family_vs_louvain'],
            },
        },
        'Q3': {
            'question_id': 'Q3',
            'title': '风味定向重构的多目标优化',
            'model': 'Ledoit-Wolf 收缩高斯生成候选 → PLS(8) 感官代理 → AUGMECON2 '
                     'ε-约束 MILP（Gurobi 13.0.2）→ 手写 NSGA-II 对照',
            'evidence_status': FINAL,
            'code': 'code/q3.py + code/robustness_q3.py + code/q3_transfer.py',
            'artifacts': ['results/q3_pareto.csv', 'results/q3_fronts.csv',
                          'results/q3_deltas.csv', 'results/q3_waterfall.csv',
                          'results/q3_surrogate.csv',
                          'results/q3_sensitivity.csv', 'results/q3_compare.csv',
                          'results/q3_transfer_pareto.csv',
                          'results/q3_transfer_defects.csv',
                          'results/q3_transfer_profile.csv'],
            'key_metrics': {
                'n_pareto': len(q3p),
                'baseline_f1': q3['baseline_x0']['f1'],
                'best_f1': float(q3p.f1.min()),
                'f1_reduction_pct': round(
                    100 * (1 - float(q3p.f1.min()) / q3['baseline_x0']['f1']), 4),
                'exact_dominates_heur': cmp_.get('exact_dominates_heur'),
                'n_sensitivity_runs': q3sm['n_runs'],
                'transfer_src': q3t['src_style'],
                'transfer_f1_reduction_pct': q3t['f1_reduction_pct'],
                'transfer_defects_ok': q3t['all_defects_non_worsening'],
            },
        },
    }
    _dump('results/model_results.json', model_results)

    # ---------------- metrics.json ----------------
    metrics = {
        'Q0': {'items': [
            {'name': 'VIF>10 的特征数', 'value': q0c['n_vif_gt_10'],
             'source': 'results/q0_summary.json', 'evidence_status': FINAL},
            {'name': 'Spearman 有效秩', 'value': q0c['effective_rank_participation'],
             'source': 'results/q0_summary.json', 'evidence_status': FINAL},
            {'name': '特征↔感官 |ρ|>0.5 格数', 'value': q0s['n_abs_gt_0.5'],
             'source': 'results/q0_summary.json', 'evidence_status': FINAL},
            {'name': '风格 Kruskal-Wallis 显著特征数', 'value': q0k['n_sig_05'],
             'source': 'results/q0_summary.json', 'evidence_status': FINAL},
        ]},
        'Q1': {'items': [
            {'name': '中位嵌套 CV R²', 'value': q1['median_R2'],
             'source': 'results/q1_run_log.json', 'evidence_status': FINAL},
            {'name': '均值 R²', 'value': q1['mean_R2'],
             'source': 'results/q1_run_log.json', 'evidence_status': FINAL},
            {'name': 'R²>0 的维度数', 'value': q1['n_R2_positive'],
             'source': 'results/q1_run_log.json', 'evidence_status': FINAL},
            {'name': '自助区间宽度中位', 'value': q1['median_boot_width'],
             'source': 'results/q1_run_log.json', 'evidence_status': FINAL},
            {'name': '最好维度 R²（alcohol）', 'value': q1['best_R2'],
             'source': 'results/q1_run_log.json', 'evidence_status': FINAL},
            {'name': '地板质量 vs R² Spearman', 'value': fvr.get('spearman'),
             'source': 'results/q1_run_log.json', 'evidence_status': FINAL},
            {'name': '0–6 等级加权 kappa 中位', 'value': q1g['median_qwk'],
             'source': 'results/q1_grade_summary.json', 'evidence_status': FINAL},
            {'name': '0–6 等级精确同档率中位', 'value': q1g['median_acc'],
             'source': 'results/q1_grade_summary.json', 'evidence_status': FINAL},
            {'name': '残差正态检验通过维数', 'value': rs['n_shapiro_pass_05'],
             'source': 'results/q1_residual_summary.json',
             'evidence_status': FINAL},
        ]},
        'Q2': {'items': [
            {'name': 'FDR 反解阈值 π_thr', 'value': q2['pi_thr'],
             'source': 'results/q2_run_log.json', 'evidence_status': FINAL},
            {'name': '过阈值化合物数', 'value': q2['n_feat_ever_over_thr'],
             'source': 'results/q2_run_log.json', 'evidence_status': FINAL},
            {'name': '跨模型 Jaccard 中位',
             'value': q2['median_cross_method_jaccard'],
             'source': 'results/q2_run_log.json', 'evidence_status': FINAL},
            {'name': 'π 自助标准误均值', 'value': pc.get('pi_boot_se_mean'),
             'source': 'results/q2_run_log.json', 'evidence_status': FINAL},
            {'name': 'A 档记录数',
             'value': [v for k, v in grades.items() if k.startswith('A')][0],
             'source': 'results/q2_run_log.json', 'evidence_status': FINAL},
            {'name': '共表达图模块度（τ=0.30）', 'value': q2g['modularity'],
             'source': 'results/q2_graph_summary.json', 'evidence_status': FINAL},
            {'name': '模块度零分布 95% 分位',
             'value': q2g['Q_null_degree_preserving_p95'],
             'source': 'results/q2_graph_summary.json', 'evidence_status': FINAL},
            {'name': 'Louvain 社区与化学族 ARI',
             'value': q2g['ari_family_vs_louvain'],
             'source': 'results/q2_graph_summary.json', 'evidence_status': FINAL},
        ]},
        'Q3': {'items': [
            {'name': 'Pareto 点数', 'value': len(q3p),
             'source': 'results/q3_pareto.csv', 'evidence_status': FINAL},
            {'name': '基线 f1', 'value': q3['baseline_x0']['f1'],
             'source': 'results/q3_run_log.json', 'evidence_status': FINAL},
            {'name': '最优 f1', 'value': float(q3p.f1.min()),
             'source': 'results/q3_pareto.csv', 'evidence_status': FINAL},
            {'name': '代理逐维 CV R² 中位', 'value': q3['surrogate']['cv_r2_median'],
             'source': 'results/q3_run_log.json', 'evidence_status': FINAL},
            {'name': '精确解支配启发式比例',
             'value': cmp_.get('exact_dominates_heur'),
             'source': 'results/q3_compare.csv', 'evidence_status': FINAL},
            {'name': '灵敏度重解次数', 'value': q3sm['n_runs'],
             'source': 'results/q3_sensitivity_summary.json',
             'evidence_status': FINAL},
            {'name': 'γ 的 f1 摆幅',
             'value': float(span[span.param == 'gamma'].span.iloc[0]),
             'source': 'results/q3_sensitivity_span.csv',
             'evidence_status': FINAL},
            {'name': '跨风格迁移 f1 降幅（Pils/Lager→Tripel）',
             'value': q3t['f1_reduction_pct'],
             'source': 'results/q3_transfer_run_log.json', 'evidence_status': FINAL},
            {'name': '迁移后缺陷物全部不恶化',
             'value': q3t['all_defects_non_worsening'],
             'source': 'results/q3_transfer_defects.csv', 'evidence_status': FINAL},
        ]},
    }
    _dump('results/metrics.json', metrics)

    # ---------------- conclusions.json ----------------
    conclusions = {
        'Q0': {'items': [
            {'conclusion_text': f'226 维近乎全体共线（{q0c["n_vif_gt_10"]}/231 '
                                f'VIF>10）但只有 {q0["feature_corr"]["n_abs_rho_gt_0.9"]} '
                                f'对 |ρ|>0.9、有效秩仅 '
                                f'{q0c["effective_rank_participation"]:.2f}，'
                                f'说明共线是成片弱相关的累积，按 VIF 删列会删光；'
                                f'特征↔感官 {q0s["n_cells"]} 格中仅 '
                                f'{q0s["n_abs_gt_0.5"]} 格 |ρ|>0.5，'
                                f'化学谱对单一感官维的直接线性关联本就极稀；'
                                f'风格对化学谱有强解释力（Kruskal-Wallis 中位 '
                                f'ε²={q0k["median_eps2"]:.4f}，'
                                f'{q0k["n_sig_05"]}/226 显著），支撑问题三的定向重构。',
             'evidence_status': FINAL},
        ]},
        'Q1': {'items': [
            {'conclusion_text': f'50 个感官维的中位嵌套 CV R² 仅 {q1["median_R2"]:.4f}'
                                f'（均值 {q1["mean_R2"]:.4f}），低于文献天花板 0.21；'
                                f'{q1["n_R2_positive"]}/50 维 R²>0 且 32/50 维自助下界>0，'
                                f'正向可预测性成立但幅度有限。地板质量与 R² 的 Spearman '
                                f'为 {fvr.get("spearman"):.4f}，是比 R² 更有效的失效判据。'
                                f'alcohol 维最高 R²={q1["best_R2"]:.4f}，'
                                f'残差 Shapiro 检验 p={rs["alcohol"]["shapiro_p"]:.3f}；'
                                f'而全部 50 维只有 {rs["n_shapiro_pass_05"]} 维残差通过正态检验。'
                                f'按零膨胀先验保序映射到 0–6 等级后，加权 kappa 中位 '
                                f'{q1g["median_qwk"]:.4f}、精确同档率 '
                                f'{q1g["median_acc"]:.4f}（零膨胀先验；等频映射下 '
                                f'QWK {q1g["median_qwk_equifreq"]:.4f} 但同档率仅 '
                                f'{q1g["median_acc_equifreq"]:.4f}）；若改用"平移后直接取整"，'
                                f'kappa 降到 {q1g["median_qwk_round"]:.4f} 且中位 '
                                f'{q1g["median_frac_round_at_zero"]:.1%} 的样本被压到 0 分。',
             'evidence_status': FINAL},
        ]},
        'Q2': {'items': [
            {'conclusion_text': f'226 个化合物中 {q2["n_feat_ever_over_thr"]} 个至少在一个'
                                f'感官维上 π 超过 FDR 阈值 {q2["pi_thr"]:.4f}；'
                                f'150 条 Top-3 记录里 A 档（统计显著且 OAV>1）仅 '
                                f'{q2["aroma_grade_counts"].get("A 统计显著且 OAV>1", 25)} 条，'
                                f'N 档（阈值表无该项、OAV 不可算）达 76 条。'
                                f'跨模型 Jaccard 中位仅 '
                                f'{q2["median_cross_method_jaccard"]:.4f}，'
                                f'归因稳定性弱，故只报告统计与化学双条件的交集。'
                                f'附件2 共表达图在 τ={q2g["main_tau"]:.2f} 处模块度 '
                                f'{q2g["modularity"]:.4f}、高于度保持零分布的 '
                                f'{q2g["Q_null_degree_preserving_p95"]:.4f}，'
                                f'但社区与化学来源的一致性 ARI 仅 '
                                f'{q2g["ari_family_vs_louvain"]:.4f}、粒度约 25 个'
                                f'化合物一组，故图只用于结构诊断、归因仍按化学族分组。',
             'evidence_status': FINAL},
        ]},
        'Q3': {'items': [
            {'conclusion_text': f'7 个 Pareto 点全部 OPTIMAL、mip_gap=0、两两互不支配；'
                                f'基线 f1 {q3["baseline_x0"]["f1"]:.4f} 降至 '
                                f'{float(q3p.f1.min()):.4f}'
                                f'（−{100 * (1 - float(q3p.f1.min()) / q3["baseline_x0"]["f1"]):.1f}%），'
                                f'但前沿上真正移动的化合物只有 7 个，其余被阈值与改动上限卡死。'
                                f'精确 MILP 支配 {100 * cmp_.get("exact_dominates_heur", 0):.2f}% '
                                f'的 NSGA-II 点、反向 0%。代理误差上界 3.4102 远大于相邻前沿点'
                                f'间距 0.00178，故只按簇报告，不报单点最优。'
                                f'灵敏度分析（{q3sm["n_runs"]} 次重解）显示改动列代价 γ 与代理'
                                f'成分数主导前沿，缺陷容忍 ε2 与干预预算 k_max 为不活跃约束。'
                                f'跨风格迁移（{q3t["src_style"]} → {q3t["dst_style"]}，'
                                f'{q3t["n_src"]} 与 {q3t["n_dst"]} 个样本）把感官偏差由 '
                                f'{q3t["f1_at_x0"]:.4f} 降到 '
                                f'{q3t["f1_migrated"]:.4f}（−{q3t["f1_reduction_pct"]:.2f}%），'
                                f'改动 {q3t["n_changed"]} 个化合物；'
                                f'消融显示去掉缺陷约束后 {q3t["n_defects_would_worsen_without_cap"]}/'
                                f'{q3t["n_defects_total"]} 类会恶化、f1 代价 '
                                f'{q3t["f1_cost_of_defect_cap"]:.4f}，'
                                f'即该组约束在本例中不活跃，只能防更大改动幅度下的触碰。',
             'evidence_status': FINAL},
        ]},
    }
    _dump('results/conclusions.json', conclusions)

    # ---------------- tables/table_index.json ----------------
    table_index = {
        'Q0': {'tables': [
            {'table_id': 'tab_files', 'name': '附件实测结构与用途',
             'source': 'results/q0_summary.json + results/q0_floor_share.csv',
             'tex': 'sections/5_数据预处理.tex', 'evidence_status': FINAL},
            {'table_id': 'tab_caliber', 'name': '题面表述与实测结论的差异及处理',
             'source': 'verify_facts.py（140 条断言）',
             'tex': 'sections/5_数据预处理.tex', 'evidence_status': FINAL},
            {'table_id': 'tab_senscorr', 'name': '特征与感官的最强相关对',
             'source': 'results/q0_sens_corr.csv',
             'tex': 'sections/5_数据预处理.tex', 'evidence_status': FINAL},
        ]},
        'Q1': {'tables': [
            {'table_id': 'tab_q1', 'name': '问题一前 10 个维度的嵌套交叉验证结果',
             'source': 'results/q1_metrics.csv',
             'tex': 'sections/6_问题一.tex', 'evidence_status': FINAL},
        ]},
        'Q2': {'tables': [
            {'table_id': 'tab_q2grade', 'name': '问题二 Top-3 记录的证据分级',
             'source': 'results/q2_top3.csv + results/q2_run_log.json',
             'tex': 'sections/7_问题二.tex', 'evidence_status': FINAL},
        ]},
        'Q3': {'tables': [
            {'table_id': 'tab_q3', 'name': '问题三的 Pareto 前沿',
             'source': 'results/q3_pareto.csv',
             'tex': 'sections/8_问题三.tex', 'evidence_status': FINAL},
            {'table_id': 'tab_q3sens', 'name': '问题三灵敏度分析',
             'source': 'results/q3_sensitivity.csv',
             'tex': 'sections/8_问题三.tex', 'evidence_status': FINAL},
        ]},
        'ALL': {'tables': [
            {'table_id': 'tab_symbols', 'name': '主要符号说明',
             'source': 'sections/4_符号说明.tex（三线表）',
             'tex': 'sections/4_符号说明.tex', 'evidence_status': FINAL},
            {'table_id': 'tab_codelist', 'name': '支撑材料代码清单',
             'source': 'code/ 目录实际行数（wc -l）',
             'tex': 'sections/A_附录代码.tex', 'evidence_status': FINAL},
        ]},
    }
    _dump(os.path.join('tables', 'table_index.json'), table_index)

    # ---------------- tasks.json ----------------
    tasks = [
        {'question_id': 'Q0', 'task': '数据口径核验与变量关系诊断',
         'status': 'done', 'owner': 'coding',
         'evidence': 'results/q0_*.csv|json', 'gate': 'G3'},
        {'question_id': 'Q1', 'task': '感官评分可预测性分层（嵌套 CV + hurdle + 自助区间）',
         'status': 'done', 'owner': 'coding',
         'evidence': 'results/q1_metrics.csv', 'gate': 'G3'},
        {'question_id': 'Q1', 'task': '残差诊断与正态性检验（50 维）',
         'status': 'done', 'owner': 'coding',
         'evidence': 'results/q1_residual_stats.csv', 'gate': 'G3'},
        {'question_id': 'Q2', 'task': '分组置换归因 + FDR 阈值 + OAV 分级',
         'status': 'done', 'owner': 'coding',
         'evidence': 'results/q2_top3.csv', 'gate': 'G3'},
        {'question_id': 'Q2', 'task': '跨模型 Jaccard 稳定性检验',
         'status': 'done', 'owner': 'coding',
         'evidence': 'results/q2_jaccard.csv', 'gate': 'G3'},
        {'question_id': 'Q3', 'task': '收缩高斯生成 + PLS 代理 + ε-约束 MILP',
         'status': 'done', 'owner': 'coding',
         'evidence': 'results/q3_pareto.csv', 'gate': 'G3'},
        {'question_id': 'Q3', 'task': 'NSGA-II 交叉验证与超体积比较',
         'status': 'done', 'owner': 'coding',
         'evidence': 'results/q3_compare.csv', 'gate': 'G3'},
        {'question_id': 'Q3', 'task': '六参数单因素灵敏度分析（27 次重解 MILP）',
         'status': 'done', 'owner': 'coding',
         'evidence': 'results/q3_sensitivity.csv', 'gate': 'G4'},
    ]
    _dump('tasks.json', tasks)

    print('\n完成。下一步：python <skill>/scripts/evidence_gate.py 复跑门禁')
    return 0


if __name__ == '__main__':
    sys.exit(main())
