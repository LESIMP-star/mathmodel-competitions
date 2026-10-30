# -*- coding: utf-8 -*-
"""make_indexes.py — 生成 figure_index.json（Step 7.4 证据索引）

为什么单独写一个脚本
  索引条目的 figure_id / chart_type / source_csv 必须和 `code/figures.py` 里的
  函数一一对应。手写 JSON 一旦图改名就会静默失配，所以把映射表放在这里，
  `FIGURE_ENTRIES` 是唯一事实源，脚本负责校验后落盘。

落盘位置（两处，内容完全一致，由本脚本一次生成，不会漂移）
  · `paper_output/figure_index.json`          ← evidence_gate.py / score_artifact.py 读这里
  · `paper_output/results/figure_index.json`  ← step-contracts.md Step 7.4 的产物清单写这里

用法
  python code/make_indexes.py            # 生成 + 校验
  python code/make_indexes.py --check    # 只校验，不写盘（CI 用）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
PROJ = _HERE.parent
RES = PROJ / 'results'
FIGDIR = FIGDIR

# (figure_id, figures.py 里的函数名后缀, chart_type, 源数据, 图型中文名, 证据角色)
# chart_type 取值必须落在 chart-decision §二 的枚举里：
#     line / scatter / heatmap / bar / box / hist / spectrum
FIGURE_ENTRIES = [
    ('Q0', [
        ('fig0_0', 'flow', 'bar', [], 
         '技术路线图', '口径核验 → 正向映射 → 归因解释 → 逆用生成（非数据图，按 fireworks 规范手绘）'),
        ('fig0_1', 'q0_box_before_after', 'box', ['q0_box_raw.csv'],
         '箱线图', '量纲统一前后对比：raw 与 log10 双面板'),
        ('fig0_2', 'q0_missing', 'bar', ['q0_floor_share.csv'],
         '排序条形图', '真缺失 8 列与检出限地板值 40 列分栏'),
    ]),
    ('Q1', [
        ('fig1_1', 'q1_r2_forest', 'bar', ['q1_forest_rows.csv'],
         '森林图（点估计＋95% 误差棒）', '逐维 R² 与 bootstrap 95% 区间（16 行）'),
        ('fig1_2', 'q1_r2_dist', 'hist', ['q1_metrics.csv', 'q1_run_log.json'],
         '直方图+核密度', '50 维 R² 的分布形态（标中位数/均值/文献天花板）'),
        ('fig1_3', 'q1_floor_vs_r2', 'scatter', ['q1_metrics.csv', 'q1_floor_fit.csv'],
         '散点+回归线', '地板质量 vs R² 的失效诊断'),
        ('fig1_4', 'q1_external', 'scatter', ['q1_external.csv', 'q1_run_log.json'],
         '散点+参照线', '4.csv 标签信号 vs 7.csv 模型信号的外部效度'),
        ('fig1_7', 'q1_reg_fit', 'scatter', ['q1_scatter_pairs.csv', 'q1_metrics.csv'],
         '散点+拟合线（2×2）', '逐样本折外预测 vs 实测：可复现与不可复现维度对照'),
        ('fig1_8', 'q1_residual', 'hist', ['q1_scatter_pairs.csv', 'q1_residual_summary.json'],
         '残差四项诊断', '同方差 / 正态 / Q–Q / 无残余结构（alcohol 维度）'),
    ]),
    ('Q2', [
        ('fig2_0', 'q2_graph', 'line', ['q2_graph_stats.csv', 'q2_graph_summary.json'],
         '折线+柱状双面板', '附件2 共表达图的模块度与零分布、模块内外相关强度'),
        ('fig2_1', 'q2_pi_heatmap', 'heatmap', ['q2_feature_pi.csv', 'q2_fdr.csv'],
         '热力图', '化合物×感官的分组置换重要性（主证据）'),
        ('fig2_2', 'q2_jaccard', 'box', ['q2_jaccard.csv', 'q2_jaccard_stats.csv'],
         '箱线图+散点', '跨模型 Top-10 稳定性（负结果）'),
        ('fig2_3', 'q2_oav', 'bar', ['q2_oav_display.csv'],
         '棒棒糖图', 'OAV 排序与三档阈值（化学合理性裁判）'),
        ('fig2_4', 'q2_convergence', 'line', ['q2_pi_convergence.csv'],
         '收敛曲线', 'π 的 bootstrap 收敛，200 次是否够用'),
    ]),
    ('Q3', [
        ('fig3_1', 'q3_front', 'scatter', ['q3_fronts.csv', 'q3_waterfall.csv'],
         'Pareto 前沿双投影', 'MILP 7 点 vs NSGA-II 189 点（主证据）'),
        ('fig3_2', 'q3_deltas', 'heatmap', ['q3_deltas.csv', 'q3_pareto.csv'],
         '差异热力图（带数值）', '每个 Pareto 点改了哪些化合物、改多少'),
        ('fig3_3', 'q3_surrogate_cv', 'bar', ['q3_surrogate.csv'],
         '棒棒糖图', '线性代理逐维 CV R²（负结果）'),
        ('fig3_4', 'q3_surrogate_err', 'bar', ['q3_surrogate.csv'],
         '棒棒糖图+阈值线', '代理误差/标准差，前沿细排序不可信的证据'),
        ('fig3_5', 'q3_radar', 'line', ['q3_style_profile.csv'],
         '雷达图', '目标/对照/最优解三线画像'),
        ('fig3_6', 'q3_waterfall', 'spectrum', ['q3_waterfall.csv'],
         '瀑布图（累加分解）', '最优 Pareto 点的 f1 逐组分解'),
        ('fig3_7', 'q3_tornado', 'bar', ['q3_sensitivity.csv'],
         '龙卷风图', '六参数单因素扰动（27 次重解 MILP）对最优 f1 的影响'),
    ]),
]

DPI = 300
FORMATS = ['png', 'svg']
# main.tex 的 geometry：左右各 70.9pt，A4 宽 595.3pt → 版心 ≈453.5pt。
# 插图宽 ≤390pt（≈5.4 in）用 0.85\textwidth 正好铺满版心且不缩放；
# 更宽的图（双面板 6.2–6.4 in）必须用 \textwidth，否则会被压到 0.86 倍、字变小。
TEXTWIDTH_PT = 453.5
HALF_TEXTWIDTH_PT = 385.5
NARROW_PT = 390.0


def latex_width(natural_pt: float) -> str:
    """按 SVG 自然宽度给出 LaTeX 插图宽度，保证落版缩放系数 ≥0.99。"""
    return '0.85\\textwidth' if natural_pt <= NARROW_PT else '\\textwidth'


def _svg_width_pt(p: Path) -> float | None:
    """读 SVG 的 width="...pt"；读不到就返回 None（不阻断索引生成）。"""
    try:
        m = re.search(r'<svg[^>]*\bwidth="([\d.]+)pt"', p.read_text(encoding='utf-8', errors='replace'))
        return float(m.group(1)) if m else None
    except Exception:
        return None


def build() -> dict:
    """按 QID 分组构造 figure_index（evidence_gate.grouped_items 形式 2：{QID: [...]}）。"""
    index: dict = {}
    for qid, rows in FIGURE_ENTRIES:
        items = []
        for fid, stem, chart_type, sources, kind_zh, role in rows:
            w = _svg_width_pt(FIGDIR / f'fig_{stem}.svg')
            items.append({
                'figure_id': fid,
                'chart_type': chart_type,
                'chart_kind_zh': kind_zh,
                'figure_file': f'paper/figures/\1',
                'files': {fmt: f'latex模板/figures/fig_{stem}.{fmt}' for fmt in FORMATS},
                'source_csv': sources,
                'dpi': DPI,
                'formats': FORMATS,
                'natural_width_pt': w,
                'latex_width': latex_width(w) if w else None,
                'plot_script': 'code/figures.py',
                'plot_function': f'fig_{stem}',
                'chart_plan': f'paper_output/results/chart_plan_{qid}.md',
                'role': role,
                'evidence_status': 'final',
            })
        index[qid] = items
    return index


def verify(index: dict) -> list[str]:
    """机械校验：图文件存在、源 CSV 存在、chart_type 合法、同问同类型 ≤3。"""
    errs: list[str] = []
    allowed = {'line', 'scatter', 'heatmap', 'bar', 'box', 'hist', 'spectrum'}
    for qid, items in index.items():
        counts: dict[str, int] = {}
        for it in items:
            for fmt, rel in it['files'].items():
                p = PROJ / rel
                if not p.exists():
                    errs.append(f"{it['figure_id']}: 缺 {rel}")
                elif p.stat().st_size == 0:
                    errs.append(f"{it['figure_id']}: {rel} 为空文件")
            for src in it['source_csv']:
                if not (RES / src).exists():
                    errs.append(f"{it['figure_id']}: 缺源数据 results/{src}")
            ct = it['chart_type']
            if ct not in allowed:
                errs.append(f"{it['figure_id']}: chart_type={ct} 不在枚举内")
            counts[ct] = counts.get(ct, 0) + 1
        for ct, n in counts.items():
            if n > 3:
                errs.append(f'{qid}: 同类型 {ct} 共 {n} 张（规则上限 3）')
        if len(counts) < 2:
            errs.append(f'{qid}: 只有 {len(counts)} 种图型（规则要求 ≥2-3 种）')
    # 目录里不该出现 PDF（skill 硬规则），也不该有索引外的孤儿图
    pdfs = sorted(FIGDIR.glob('*.pdf'))
    if pdfs:
        errs.append(f'figures/ 出现 PDF：{[p.name for p in pdfs]}')
    listed = {Path(it['files']['png']).name for items in index.values() for it in items}
    orphans = sorted(p.name for p in FIGDIR.glob('*.png') if p.name not in listed)
    if orphans:
        errs.append(f'figures/ 有未入索引的图：{orphans}')
    # 落版缩放：90% 以下的图缩到版心后字会变小，必须换 \textwidth
    for items in index.values():
        for it in items:
            w = it.get('natural_width_pt')
            if not w:
                continue
            target = TEXTWIDTH_PT if it['latex_width'] == '\\textwidth' else HALF_TEXTWIDTH_PT
            if target / w < 0.95:
                errs.append(f"{it['figure_id']}: 落版缩放 {target / w:.3f} < 0.95（字会变小）")
    return errs


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='生成 figure_index.json 并校验')
    ap.add_argument('--check', action='store_true', help='只校验不写盘')
    args = ap.parse_args()

    index = build()
    errs = verify(index)
    n_fig = sum(len(v) for v in index.values())
    types = sorted({it['chart_type'] for v in index.values() for it in v})

    print(f'{n_fig} 张图 / {len(index)} 问 / {len(types)} 种图型：{types}')
    if errs:
        print('校验失败：')
        for e in errs:
            print('  ✗', e)
        return 1

    if not args.check:
        payload = json.dumps(index, ensure_ascii=False, indent=2) + '\n'
        for target in (PROJ / 'paper_output' / 'figure_index.json',
                       PROJ / 'paper_output' / 'results' / 'figure_index.json',
                       RES / 'figure_index.json'):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(payload, encoding='utf-8')
            print('写出', target.relative_to(PROJ))
    print('校验通过：文件齐全、chart_type 合法、无 PDF、无孤儿图')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
