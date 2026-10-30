# -*- coding: utf-8 -*-
"""figures.py — 论文插图（只读 results/，不重算任何论文数值）

设计约束
  1. 唯一数据源是 results/ 下由 q0_relations.py / q1.py / q2.py / q3.py 落盘的
     CSV/JSON。本脚本只做筛选、排序、转置这类"显示层"操作，**不计算任何进入论文的
     统计量**。缺哪个数就回去改求解脚本补存，绝不在这里现算（figure-contract）。
  2. 输出一律 PNG(300dpi) + SVG，禁 PDF（finalize_figure 的默认行为）。
  3. 图内不加总标题（论文的 \\caption 负责题注）；多面板只用 (a)(b)(c) 面板标签。
     `_notitle` 兜底，任何以"图"开头的标题都会被清空。
  4. 配色一律取数模素材库的冷色盘（PALETTE_COOL / COOL_SEQ / COOL_DIV），
     与队友 A2600001 的 figs.py 完全一致；网格 #E5E8EC / 边框 #333333 同样照抄，
     但网格结构按 skill 规则**只保留 y 轴**（见 state/decision_log.json 的偏差登记）。
     冷色盘 blue/blue2/teal/mint 明度相邻，黑白打印区分度弱，因此凡是多系列图
     一律叠加 marker（o/s/D/^/v）与线型做冗余编码。
  5. figsize 按版面反推：main.tex 的 geometry 使有效文本宽 ≈453.5 pt，插图按
     0.85\\textwidth 排 = 385.5 pt = 5.35 in。故单面板宽 ≤5.4 in、双面板 ≤6.4 in，
     否则缩放后字号会掉到 6 pt 以下（这正是旧版 9 张图字号全崩的根因）。

二十一张图的证据分工
  Q0  fig_q0_missing          缺失结构与检出限地板值占比
  Q0  fig_q0_box_before_after 量纲统一前后（raw vs log10）箱线
  --  fig_flow                全文技术路线（四行：数据体检 → Q1 → Q2 → Q3）
  Q1  fig_q1_r2_forest        逐维 R² 及 bootstrap 95% 区间（Top-10 + 聚合 + Bottom-5）
  Q1  fig_q1_r2_dist          50 维 R² 的分布形态（直方 + 核密度，标中位数/天花板）
  Q1  fig_q1_reg_fit          四个代表项的折外预测 vs 实测散点 —— 拟合形态
  Q1  fig_q1_residual         alcohol 项残差四项诊断（散点/QQ/直方/序列）
  Q1  fig_q1_floor_vs_r2      左尾占比 vs R² + OLS 线 —— 失效诊断
  Q1  fig_q1_external         标签信号 vs 模型信号在 7.csv 上的效度 —— 外部效度
  Q2  fig_q2_graph            共表达图结构诊断（Louvain 模块度 + 三种聚类对比）
  Q2  fig_q2_pi_heatmap       化合物 × 感官的逐列置换重要性 —— 主证据
  Q2  fig_q2_jaccard          跨模型 Top-10 稳定性 —— 负结果
  Q2  fig_q2_oav              浓度/阈值比排序 —— 化学合理性裁判
  Q2  fig_q2_convergence      π 的 bootstrap 收敛曲线 —— 200 次重采样是否够
  Q3  fig_q3_front            Pareto 前沿双投影，MILP vs NSGA-II —— 主证据
  Q3  fig_q3_deltas           每个 Pareto 点改了哪些化合物、改多少
  Q3  fig_q3_surrogate_cv     线性代理的逐维 CV R² —— 负结果
  Q3  fig_q3_surrogate_err    代理误差上界 / 标准差 —— 负结果
  Q3  fig_q3_radar            目标风格 / 对照风格 / 最优解代理预测的三线画像
  Q3  fig_q3_waterfall        最优 Pareto 点的 f1 逐组分解
  Q3  fig_q3_tornado          六参数单因素扰动的 f1 极差 —— 灵敏度

本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：Hermes Agent（Nous Research），底层模型 deepseek-v4-flash，
# 开发机构：Nous Research（工具）/ 深度求索 DeepSeek（模型），使用日期：2026-10-26
"""
from __future__ import annotations

import json
import os
import sys
import argparse
from pathlib import Path

# ── 绘图包引导：plotting 在 skill 的 algorithms/ 下，不在项目目录里 ──
_HERE = Path(__file__).resolve().parent
_SKILL_ALG = Path('C:/Users/asus/.claude/skills/math-modeling-contest/algorithms')
if _SKILL_ALG.is_dir() and str(_SKILL_ALG) not in sys.path:
    sys.path.insert(0, str(_SKILL_ALG))
# 数模素材库：冷色盘的唯一事实源（CLAUDE.md：改样式只改 common/）
_LIB_COMMON = Path('e:/知识库/Mathmodel all/数模素材库/common')
if _LIB_COMMON.is_dir() and str(_LIB_COMMON) not in sys.path:
    sys.path.insert(0, str(_LIB_COMMON))

import matplotlib                       # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402
from matplotlib.colors import LinearSegmentedColormap   # noqa: E402
from matplotlib.lines import Line2D                     # noqa: E402
from matplotlib.patches import Patch, FancyBboxPatch, FancyArrowPatch  # noqa: E402

from plotting.api import (               # noqa: E402
    apply_publication_style,
    make_forest_plot,
    add_panel_label,
    finalize_figure,
)
from plot_style import PALETTE_COOL, COOL_SEQ, COOL_DIV, COOL_GRID, COOL_EDGE  # noqa: E402

import _notitle                          # noqa: E402,F401  （副作用：屏蔽图内总标题）

_P0 = _HERE.parent
# 向上找含 results/ 的目录（本地在 code/ 下一级，仓库可能在 code/ 下一级）
PROJ = next((p for p in [_P0, _P0.parent] if (p / 'results').is_dir()), _P0)
RES = PROJ / 'results'
# 论文插图目录两种命名都认：本地 `latex模板/figures`，仓库 `paper/figures`
OUT = next((p for p in [PROJ / 'latex模板' / 'figures', PROJ / 'paper' / 'figures']
            if p.parent.is_dir()), PROJ / 'latex模板' / 'figures')

# 冷色盘（与队友 figs.py:48-64 同值）
C_DEEP = PALETTE_COOL['deep']
C_BLUE = PALETTE_COOL['blue']
C_BLUE2 = PALETTE_COOL['blue2']
C_TEAL = PALETTE_COOL['teal']
C_MINT = PALETTE_COOL['mint']
C_PALE = PALETTE_COOL['pale']
C_PURPLE = PALETTE_COOL['purple']
C_GRAY = PALETTE_COOL['gray']
C_WARN = PALETTE_COOL['warn']
CAT = [C_DEEP, C_BLUE, C_BLUE2, C_TEAL, C_MINT, C_PURPLE, C_GRAY, C_PALE]

CMAP_SEQ = LinearSegmentedColormap.from_list('cool_seq', COOL_SEQ)
CMAP_DIV = LinearSegmentedColormap.from_list('cool_div', COOL_DIV)


# ─────────────────────────────────────────────────────────────
# 读取（只做类型/形状校验，不改数值）
# ─────────────────────────────────────────────────────────────

def _read(name, **kw):
    p = RES / name
    if not p.exists():
        raise SystemExit(f'缺少 {p} —— 请先跑对应的求解脚本')
    d = pd.read_csv(p, **kw)
    if d.empty:
        raise SystemExit(f'{p} 为空表，不应进图')
    return d


def _read_json(name):
    p = RES / name
    if not p.exists():
        raise SystemExit(f'缺少 {p} —— 请先跑对应的求解脚本')
    with open(p, encoding='utf-8') as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────
# 版式助手（队友 figs.py:20-44 的视觉语言；网格只留 y 轴）
# ─────────────────────────────────────────────────────────────

def _style_ax(ax, ygrid=True, spines=True):
    ax.set_facecolor('white')
    if spines:
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
        for side in ('left', 'bottom'):
            ax.spines[side].set_visible(True)
            ax.spines[side].set_color(COOL_EDGE)
            ax.spines[side].set_linewidth(1.1)
    if ygrid:
        # matplotlib 没有全局"仅 y 轴"开关，必须在每个 ax 上显式开
        ax.grid(axis='y', color=COOL_GRID, linewidth=0.7, linestyle='-')
        ax.grid(axis='x', visible=False)
    ax.set_axisbelow(True)


def _diag_dir(ax):
    """y=x 这条对角线在屏幕坐标下的单位方向向量与单位法向。

    x、y 两轴量纲不同，数据坐标里的 45° 在屏幕上并不是 45°，所以必须先把
    两端点转到显示坐标再取方向；否则"垂直于对角线"的偏移会偏掉。
    法向指向图区左上（即点在对角线上方时该走的方向）。
    """
    (x0, y0), (x1, y1) = ax.transData.transform([(0.0, 0.0), (1.0, 1.0)])
    theta = np.arctan2(y1 - y0, x1 - x0)
    return np.cos(theta), np.sin(theta), -np.sin(theta), np.cos(theta)


def _pcolormesh(ax, M, x_labels, y_labels, cmap, cbar_label=None, vmin=None,
                vmax=None, annotate=False, fmt='{:.2f}', annot_fontsize=7):
    """用 pcolormesh 画热力图。

    不用 make_heatmap 的原因：它内部走 ax.imshow，SVG 导出时会把整张图内嵌成
    base64 位图（实测 2 张旧图不可编辑）。pcolormesh 是真正的矢量网格。
    """
    M = np.asarray(M, dtype=float)
    mesh = ax.pcolormesh(M, cmap=cmap, vmin=vmin, vmax=vmax,
                         edgecolors='none', shading='flat', rasterized=False)
    ax.set_xlim(0, M.shape[1])
    ax.set_ylim(M.shape[0], 0)                 # y 轴翻转：第 0 行在顶部
    ax.set_xticks(np.arange(M.shape[1]) + 0.5)
    ax.set_xticklabels(x_labels)
    ax.set_yticks(np.arange(M.shape[0]) + 0.5)
    ax.set_yticklabels(y_labels)
    ax.set_frame_on(False)
    ax.tick_params(length=0)
    if annotate:
        norm = matplotlib.colors.Normalize(
            vmin=M.min() if vmin is None else vmin,
            vmax=M.max() if vmax is None else vmax)
        for (i, j), val in np.ndenumerate(M):
            r, g, b, _ = cmap(norm(val))
            ax.text(j + 0.5, i + 0.5, fmt.format(val), ha='center', va='center',
                    fontsize=annot_fontsize,
                    color='white' if (0.299 * r + 0.587 * g + 0.114 * b) < 0.5 else 'black')
    if cbar_label:
        cbar = ax.figure.colorbar(mesh, ax=ax, fraction=0.045, pad=0.02)
        # colorbar 的色条默认 rasterized=True，SVG 里会被内嵌成 base64 位图，
        # 实测这正是旧图"打开不可编辑"的来源（与 imshow 无关）。必须显式关掉。
        cbar.solids.set_rasterized(False)
        cbar.set_label(cbar_label, fontsize=10.5)
        cbar.ax.tick_params(labelsize=9)
        cbar.outline.set_linewidth(0.6)
        cbar.outline.set_edgecolor(COOL_EDGE)
    return mesh


# ─────────────────────────────────────────────────────────────
# Q0（复刻队友 figs.py 的图型，数据换成本项目实测）
# ─────────────────────────────────────────────────────────────

BOX_COLS = ['X2.3.butanedione', 'linalool', 'ethyl.butyrate',
            'furfural', 'citronellol', 'alpha.humulene']
BOX_LABELS = ['2,3-丁二酮', '芳樟醇', '丁酸乙酯', '糠醛', '香茅醇', 'α-蛇麻烯']


def fig_q0_box_before_after():
    """量纲统一前后：同一批化合物在原始浓度与 log10 浓度下的分布。

    版式照抄队友 figs.py:180-208（patch_artist / widths=.55 / 小圆离群点 /
    symlog 轴 / CAT 逐箱配色），只改三处：去掉图内总标题、缩到双面板 6.2 in、
    y 向网格。
    """
    b = _read('q0_box_raw.csv')
    missing = [c for c in BOX_COLS if c not in b.columns]
    if missing:
        raise SystemExit(f'q0_box_raw.csv 缺列 {missing}')
    fig, axes = plt.subplots(1, 2, figsize=(6.2, 3.8))
    for ax, stage in zip(axes, ('raw', 'log')):
        data = []
        for c in BOX_COLS:
            v = pd.to_numeric(b[c], errors='coerce').dropna().to_numpy(float)
            data.append(v if stage == 'raw' else np.log10(np.clip(v, 1e-6, None)))
        bp = ax.boxplot(data, tick_labels=BOX_LABELS, patch_artist=True, widths=0.55,
                        showfliers=True, whis=1.5,
                        flierprops=dict(marker='o', ms=2.4, mfc=C_WARN, mec='none', alpha=0.5),
                        medianprops=dict(color=C_DEEP, lw=1.5),
                        boxprops=dict(lw=1.0, edgecolor=COOL_EDGE),
                        whiskerprops=dict(lw=0.9, color=C_GRAY),
                        capprops=dict(lw=0.9, color=C_GRAY))
        for patch, col in zip(bp['boxes'], CAT):
            patch.set_facecolor(col)
            patch.set_alpha(0.42)
        if stage == 'raw':
            ax.set_yscale('symlog', linthresh=1e-3)
            ax.set_ylabel('原始浓度', fontsize=11)
        else:
            ax.set_ylabel('$\\log_{10}$(浓度)', fontsize=11)
        # 6 个中文类别名在同一块 142 pt 宽的轴里只有 23.7 pt 间距，而"2,3-丁二酮"
        # 单行就占 46.8 pt。原来用 20°，相邻两条标签基线的垂直间距只有
        # 23.7*sin20° = 8.1 pt，小于 9 pt 字高，所以"2,3-丁二酮/芳樟醇"、
        # "丁酸乙酯/糠醛"、"香茅醇/α-蛇麻烯"三处压字（实测最差重叠 10.1 pt）。
        # 45° 后垂直间距 16.8 pt，净空 6 pt；标签底端距图底 8.0 pt，不出界。
        ax.tick_params(axis='x', labelsize=9, rotation=45)
        ax.tick_params(axis='y', labelsize=9)
        _style_ax(ax)
        add_panel_label(ax, '(a)' if stage == 'raw' else '(b)', x=-0.20, y=1.03, fontsize=11)
    return finalize_figure(fig, OUT / 'fig_q0_box_before_after')


def fig_q0_missing():
    """(a) 真缺失的最小结构（只有 8 列）。(b) 检出限地板值占比（≥30% 的 18 列）。

    版式照抄队友 figs.py:261-287（双面板 + width_ratios + 30% 警戒线）。
    地板值不是缺失：它是"低于检出限"的占位，所以必须与真缺失分栏呈现。
    """
    fs = _read('q0_floor_share.csv')
    miss = fs[fs.missing_n > 0].sort_values('missing_pct').reset_index(drop=True)
    fl = fs[fs.mode_share >= 0.30].sort_values('mode_share').tail(18).reset_index(drop=True)

    fig, axes = plt.subplots(1, 2, figsize=(6.2, 4.2),
                             gridspec_kw={'width_ratios': [1.0, 1.35]})
    ax = axes[0]
    ax.barh(np.arange(len(miss)), miss.missing_pct, color=C_BLUE, height=0.62)
    for i, r in miss.iterrows():
        ax.text(r.missing_pct + 0.15, i, f'{int(r.missing_n)}', va='center',
                fontsize=9, color=C_GRAY)
    ax.set_yticks(np.arange(len(miss)))
    ax.set_yticklabels(miss.feat, fontsize=9)
    ax.set_xlabel('缺失率 (%)', fontsize=10.5)
    ax.set_xlim(0, miss.missing_pct.max() * 1.22)
    _style_ax(ax)
    add_panel_label(ax, '(a)', x=-0.28, y=1.04, fontsize=10.5)

    ax = axes[1]
    ax.barh(np.arange(len(fl)), fl.mode_share * 100, color=C_WARN, height=0.66, alpha=0.88)
    ax.axvline(30, ls='--', lw=1.1, color=C_DEEP)
    ax.text(31, len(fl) - 0.6, '30% 阈值', fontsize=9, color=C_DEEP, va='top')
    ax.set_yticks(np.arange(len(fl)))
    ax.set_yticklabels(fl.feat, fontsize=8.5)
    ax.set_xlabel('同一取值占比 (%)', fontsize=10.5)
    ax.set_xlim(0, 100)
    _style_ax(ax)
    add_panel_label(ax, '(b)', x=-0.24, y=1.04, fontsize=10.5)
    return finalize_figure(fig, OUT / 'fig_q0_missing')


# ─────────────────────────────────────────────────────────────
# Q1
# ─────────────────────────────────────────────────────────────

def fig_q1_r2_forest():
    """逐维 R² + bootstrap 95% 区间（Top-10 / 其余中位 / Bottom-5，共 16 行）。

    50 维全画要 10.5 in 高，缩到 0.85\\textwidth 后刻度只剩 4.7 pt。行集合与
    "其余 35 维的中位数"由 q1.py 落盘在 q1_forest_rows.csv，本脚本只排序。
    """
    f = _read('q1_forest_rows.csv')
    colors = [C_BLUE if lo > 0 else C_GRAY for lo in f.ci_low]
    fig, ax = plt.subplots(figsize=(5.4, 5.6))
    make_forest_plot(ax, labels=f.label.tolist(), estimates=f.estimate.tolist(),
                     ci_low=f.ci_low.tolist(), ci_high=f.ci_high.tolist(),
                     colors=colors, ref=0.0, marker='o', markersize=4.5, lw=1.3,
                     xlabel='嵌套交叉验证 $R^2$')
    ax.tick_params(axis='y', labelsize=9.5)
    ax.tick_params(axis='x', labelsize=9.5)
    # 聚合行用斜体强调它不是单个感官维
    for lbl in ax.get_yticklabels():
        if lbl.get_text().startswith('其余'):
            lbl.set_fontstyle('italic')
    ax.axvline(0.21, color=C_WARN, linestyle=':', linewidth=1.4)
    ax.text(0.215, len(f) - 0.6, '文献天花板 $R^2\\approx0.21$',
            color=C_WARN, fontsize=9, va='top')
    handles = [Line2D([], [], color=C_BLUE, marker='o', lw=1.3, ms=4.5,
                      label='95% 区间不含 0'),
               Line2D([], [], color=C_GRAY, marker='o', lw=1.3, ms=4.5,
                      label='95% 区间含 0')]
    ax.legend(handles=handles, loc='lower right', fontsize=9)
    ax.set_xlabel('嵌套交叉验证 $R^2$（点=均值，横线=bootstrap 95% 区间）', fontsize=10.5)
    _style_ax(ax, ygrid=False)
    ax.grid(axis='x', color=COOL_GRID, linewidth=0.7)
    ax.grid(axis='y', visible=False)
    return finalize_figure(fig, OUT / 'fig_q1_r2_forest')


def fig_q1_floor_vs_r2():
    """地板质量 vs R²。拟合线与 95% 置信带由 q1.py 落盘在 q1_floor_fit.csv
    （绘图脚本禁止重算回归），散点按是否走 hurdle 分两组标记。"""
    m = _read('q1_metrics.csv')
    fit = _read('q1_floor_fit.csv')
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    ax.fill_between(fit.floor_mass, fit.band_lo, fit.band_hi,
                    color=C_BLUE2, alpha=0.18, linewidth=0, zorder=1)
    ax.plot(fit.floor_mass, fit.fit, color=C_DEEP, linewidth=1.8,
            linestyle=(0, (5, 2)), zorder=2)
    for flag, color, lab, marker in ((False, C_BLUE, '普通回归', 'o'),
                                     (True, C_WARN, '两部模型（hurdle）', '^')):
        d = m[m.hurdle == flag]
        ax.scatter(d.floor_mass, d.R2, s=42, color=color, marker=marker,
                   edgecolor='white', linewidth=0.7, label=lab, zorder=3)
    ax.axhline(0.0, color=C_GRAY, linestyle='--', linewidth=1.1)
    ax.set_xlabel('左尾占比（该感官维落在 $y_{min}+0.15$ 以内的比例）', fontsize=10.5)
    ax.set_ylabel('嵌套交叉验证 $R^2$', fontsize=10.5)
    ax.set_xlim(-0.03, 0.83)
    ax.tick_params(labelsize=9.5)
    ax.legend(loc='upper center', fontsize=9)
    # 标注两个极端点，坐标取自 q1_metrics.csv。偏移按当前数据手调：
    # alcohol 所在的 (0.01, 0.71) 旁边 0.048 处还有一个近重合的点，标签必须
    # 往下让开它，否则字压在点上；barnyard 的点在 x≈0.47，原来把标签放在
    # x≈0.24（-0.24）——那一片正好是蓝点最密的地方，整段文字都压在点上。
    for name, dx, dy in (('alcohol', 0.03, -0.05), ('barnyard', -0.16, 0.02)):
        row = m[m.sens == name]
        if len(row):
            fx, fy = float(row.floor_mass.iloc[0]), float(row.R2.iloc[0])
            ax.annotate(name, (fx, fy), xytext=(fx + dx, fy + dy),
                        fontsize=9, color=C_DEEP,
                        arrowprops=dict(arrowstyle='-', color=C_GRAY, lw=0.9))
    _style_ax(ax)
    return finalize_figure(fig, OUT / 'fig_q1_floor_vs_r2')


def fig_q1_external():
    """外部效度：4.csv 标签与 7.csv 论坛词的真实相关（横轴） vs
    模型预测在 7.csv 上的相关（纵轴）。点落在对角线附近 = 模型继承了标签信号。

    指标框里的三个中位数全部读自 q1_run_log.json（由 q1.py 计算落盘），
    绘图脚本不算任何均值/中位数。
    """
    e = _read('q1_external.csv')
    log = _read_json('q1_run_log.json')
    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    ax.plot([-0.15, 0.75], [-0.15, 0.75], color=C_GRAY, linestyle='--',
            linewidth=1.2, label='$y=x$（完全继承标签信号）')
    ax.axhline(0.0, color=COOL_GRID, linewidth=1.0)
    ax.axvline(0.0, color=COOL_GRID, linewidth=1.0)
    ax.scatter(e.rho_label7_vs_4, e.rho_pred_vs_7, s=58, color=C_BLUE, marker='o',
               edgecolor='white', linewidth=0.9, zorder=3, label=f'{len(e)} 组对齐概念')
    # 只标偏离对角线最大的 3 点（全标会叠成一团）。先定坐标范围，后面按最终
    # 比例算屏幕法向。
    ax.set_xlim(-0.15, 0.78)
    ax.set_ylim(-0.15, 0.78)
    # 标签放在 y=x 的外侧并加引线。原来固定 (5,-10) 偏移（右下），而这三点都在
    # 对角线上方，右下正好朝参考线走——文字被虚线从中间穿过；diacetyl 与 dms
    # 在屏幕上只隔 6 pt，固定偏移还会让两个标签叠在一起。
    dev = (e.rho_pred_vs_7 - e.rho_label7_vs_4).abs().sort_values(ascending=False)
    ux, uy, nx, ny = _diag_dir(ax)            # 对角线方向 / 法向（法向指左上）
    px_per_pt = fig.dpi / 72.0
    seen = []
    for i in dev.index[:3]:
        r = e.loc[i]
        p = ax.transData.transform((r.rho_label7_vs_4, r.rho_pred_vs_7))
        # 与已标点的屏幕距离过近时，沿对角线方向错开，且朝远离那个点的一侧
        # 走。不能翻到对角线另一侧：这两个点本就离线不远，翻过去标签正好压在
        # 线上（dms 离线只有 15.6 pt）。
        shift = 0.0
        for q in seen:
            if np.hypot(*(p - q)) < 14 * px_per_pt:
                shift = -26.0 * (np.sign((p - q) @ np.array([ux, uy])) or 1.0)
                break
        seen.append(p)
        above = 1.0 if r.rho_pred_vs_7 >= r.rho_label7_vs_4 else -1.0
        ox = above * 15 * nx + shift * ux
        oy = above * 15 * ny + shift * uy
        ax.annotate(r.sens_4csv, (r.rho_label7_vs_4, r.rho_pred_vs_7),
                    xytext=(ox, oy), textcoords='offset points',
                    fontsize=9, color=C_DEEP,
                    ha='right' if ox < 0 else 'left',
                    va='bottom' if oy > 0 else 'top',
                    arrowprops=dict(arrowstyle='-', color=C_GRAY, lw=0.9))
    ax.set_xlabel('标签信号：$\\rho$(4.csv 感官分, 7.csv 对应词)', fontsize=10.5)
    ax.set_ylabel('模型信号：$\\rho$(模型预测, 7.csv 对应词)', fontsize=10.5)
    ax.tick_params(labelsize=9.5)
    ax.legend(loc='upper left', fontsize=9)
    txt = (f'中位 $R^2_{{pred}}$ = {log["ext_median_r2_pred_vs_7"]:+.3f}\n'
           f'中位 MAE$_z$ = {log["ext_median_mae_z_pred_vs_7"]:.3f}\n'
           f'中位 $\\rho_{{pred}}$ = {log["ext_median_rho_pred_vs_7"]:.3f}\n'
           f'中位 $\\rho_{{label}}$ = {log["ext_median_rho_label_vs_7"]:.3f}')
    ax.text(0.98, 0.03, txt, transform=ax.transAxes, ha='right', va='bottom',
            fontsize=9, color=C_DEEP, linespacing=1.45,
            bbox=dict(boxstyle='round,pad=0.45', facecolor=C_PALE,
                      edgecolor=C_BLUE2, linewidth=0.8, alpha=0.65))
    _style_ax(ax)
    return finalize_figure(fig, OUT / 'fig_q1_external')


def fig_q1_r2_dist():
    """50 个感官维 R² 的单变量分布（直方图 + 核密度），标中位数与文献天花板。

    为什么需要这张：Q1 现有三张图都是散点家族，`chart-decision §二` 规则 3 要求
    "每问至少 2–3 种图类型"，而"50 维 R² 到底分布成什么样"本身是
    `chart-decision §一` 的"单变量分布 → 直方图"行，散点图无法替代。
    分箱边界属显示层选择；图中的中位数/均值读自 q1_run_log.json，不在本脚本重算。
    """
    m = _read('q1_metrics.csv')
    log = _read_json('q1_run_log.json')
    r2 = m.R2.to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    bins = np.linspace(np.floor(r2.min() * 10) / 10, np.ceil(r2.max() * 10) / 10, 16)
    n, edges, patches = ax.hist(r2, bins=bins, color=C_BLUE2, alpha=0.55,
                                edgecolor='white', linewidth=0.9, zorder=2)
    # 逐柱按 R² 高低上色：<0 用警示色，与森林图的"区间含 0"同语义
    for cnt, left, patch in zip(n, edges[:-1], patches):
        patch.set_facecolor(C_WARN if left < 0 else C_BLUE2)
    # 核密度只作形态提示，纵轴仍用计数（避免两套量纲）
    if len(r2) > 2 and r2.std() > 0:
        kde_x = np.linspace(bins[0], bins[-1], 200)
        try:
            from scipy.stats import gaussian_kde
            dens = gaussian_kde(r2)(kde_x)
            dens = dens / dens.max() * n.max() * 0.85          # 归一到计数尺度
            ax.plot(kde_x, dens, color=C_DEEP, linewidth=1.6, zorder=3,
                    label='核密度（归一化到计数）')
        except Exception:
            pass
    med = float(log['median_R2'])
    mean = float(log['mean_R2'])
    # 三条参考线不再用旋转 90° 的行内文字标注：均值 0.2213 与文献天花板 0.21
    # 只差 0.011，行内标注必然重叠。改为统一放进图例，靠线型区分，不占绘图区。
    ref_handles = []
    for v, col, lab, ls in ((med, C_DEEP, f'中位 {med:.4f}', '-'),
                            (mean, C_TEAL, f'均值 {mean:.4f}', '--'),
                            (0.21, C_WARN, '原文 GBR 0.21', ':')):
        ax.axvline(v, color=col, linestyle=ls, linewidth=1.5, zorder=4)
        ref_handles.append(Line2D([], [], color=col, linestyle=ls, lw=1.5, label=lab))
    ax.set_xlabel('嵌套交叉验证 $R^2$', fontsize=10.5)
    ax.set_ylabel('感官维个数', fontsize=10.5)
    ax.set_ylim(0, n.max() * 1.42)
    ax.tick_params(labelsize=9.5)
    handles = [Patch(facecolor=C_BLUE2, alpha=0.55, edgecolor='white', label='$R^2\geq0$'),
               Patch(facecolor=C_WARN, alpha=0.55, edgecolor='white', label='$R^2<0$'),
               Line2D([], [], color=C_DEEP, lw=1.6, label='核密度（归一化到计数）')]
    ax.legend(handles=handles + ref_handles, loc='upper right', fontsize=8.0,
              ncol=2, columnspacing=0.9, handletextpad=0.5, borderaxespad=0.3)
    _style_ax(ax)
    return finalize_figure(fig, OUT / 'fig_q1_r2_dist')


def fig_q1_reg_fit():
    """回归拟合散点：可复现维度 vs 不可复现维度对照（1×4 横排，省纵向版面）。

    版式照抄队友 figs.py:289-325 的 fig_reg（散点 + 最小二乘线 + y=x 虚线 +
    面板标题标 R²/Spearman + 图例），只改三处：①去掉总标题（\\caption 负责）；
    ②改为 1 行 4 列横排，便于在正文中与文字混排而非独占一页；
    ③配对数据读自 results/q1_scatter_pairs.csv，R²/Spearman 读自 q1_metrics.csv，
      不在绘图脚本里现算（figure-contract）。
    """
    pairs = _read('q1_scatter_pairs.csv')
    met = _read('q1_metrics.csv').set_index('sens')

    dims = ['alcohol', 'acidity', 'bitternes', 'F_esters_flower']
    titles = ['(a) alcohol', '(b) acidity', '(c) bitternes', '(d) F_esters_flower']

    # 1×4 横排：单panel约 1.85 in，四张合计约 7.6 in，适合 0.95\textwidth
    fig, axes = plt.subplots(1, 4, figsize=(7.6, 2.5))
    fig.subplots_adjust(wspace=0.32)
    for ax, s, ttl in zip(axes.ravel(), dims, titles):
        yt = pairs[f'{s}_true'].to_numpy(float)
        yp = pairs[f'{s}_pred'].to_numpy(float)
        ok = np.isfinite(yt) & np.isfinite(yp)
        yt, yp = yt[ok], yp[ok]

        ax.scatter(yt, yp, s=6, color=C_BLUE, alpha=0.45,
                   edgecolor='white', lw=0.2)
        lim = [min(yt.min(), yp.min()), max(yt.max(), yp.max())]
        ax.plot(lim, lim, ls='--', color=C_GRAY, lw=0.9, label='$y=x$')
        k, b = np.polyfit(yt, yp, 1)
        xs = np.linspace(lim[0], lim[1], 50)
        ax.plot(xs, k * xs + b, color=C_WARN, lw=1.2, label='最小二乘')

        r2 = float(met.loc[s, 'R2'])
        rho = float(met.loc[s, 'spearman'])
        ax.set_title(f'{ttl}\n$R^2$={r2:.3f}, $\\rho$={rho:.3f}', fontsize=7.6, pad=4)
        ax.set_xlabel('实测', fontsize=7.2, labelpad=1)
        # 四个面板量程不同，每张都标 y 轴，避免误读为共享纵轴
        ax.set_ylabel('折外预测', fontsize=7.2, labelpad=1)
        ax.tick_params(labelsize=6.2, length=2, pad=1.5)
        _style_ax(ax)
    axes.ravel()[0].legend(loc='upper left', frameon=False, fontsize=6.2,
                           handlelength=1.4, handletextpad=0.4, borderpad=0.2)
    return finalize_figure(fig, OUT / 'fig_q1_reg_fit')


def fig_q1_residual():
    """残差四项诊断（alcohol 维度）：同方差、正态、Q–Q、无残余结构。

    版式照抄队友 figs.py:325-381 的 fig_resid（2×2：残差–拟合值 / 直方图+正态参照 /
    Q–Q / 残差–样本序），改动同上：数据读自 results/q1_scatter_pairs.csv，
    残差统计读自 q1_residual_summary.json，不在绘图中现算。
    """
    from statistics import NormalDist

    pairs = _read('q1_scatter_pairs.csv')
    rst = _read_json('q1_residual_summary.json')

    s = 'alcohol'
    yt = pairs[f'{s}_true'].to_numpy(float)
    yp = pairs[f'{s}_pred'].to_numpy(float)
    ok = np.isfinite(yt) & np.isfinite(yp)
    yt, yp = yt[ok], yp[ok]
    res = yt - yp
    a = rst['alcohol']
    mu, sd = float(a['res_mean']), float(a['res_sd'])

    fig, axes = plt.subplots(2, 2, figsize=(6.6, 5.6))

    ax = axes[0, 0]
    ax.scatter(yp, res, s=12, color=C_BLUE, alpha=0.5, edgecolor='white', lw=0.3)
    ax.axhline(0, color=C_WARN, lw=1.1)
    ax.set_xlabel('拟合值', fontsize=8.5)
    ax.set_ylabel('残差', fontsize=8.5)
    ax.set_title('(a)', fontsize=8.4)
    _style_ax(ax)

    ax = axes[0, 1]
    ax.hist(res, bins=24, color=C_TEAL, alpha=0.6, edgecolor='white', lw=0.4,
            density=True)
    xs = np.linspace(res.min(), res.max(), 200)
    ax.plot(xs, np.exp(-(xs - mu) ** 2 / (2 * sd ** 2)) / (sd * np.sqrt(2 * np.pi)),
            color=C_DEEP, lw=1.4, label='正态参照')
    ax.set_xlabel('残差', fontsize=8.5)
    ax.set_ylabel('密度', fontsize=8.5)
    ax.set_title('(b)', fontsize=8.4)
    ax.legend(frameon=False, fontsize=7.0)
    _style_ax(ax)

    ax = axes[1, 0]
    z = np.sort((res - mu) / sd)
    q = (np.arange(1, len(z) + 1) - 0.5) / len(z)
    ND = NormalDist()
    tq = np.array([ND.inv_cdf(float(x)) for x in q])
    ax.scatter(tq, z, s=10, color=C_PURPLE, alpha=0.6)
    lim = [min(tq.min(), z.min()), max(tq.max(), z.max())]
    ax.plot(lim, lim, '--', color=C_WARN, lw=1.2)
    ax.set_xlabel('理论分位数', fontsize=8.5)
    ax.set_ylabel('标准化残差', fontsize=8.5)
    ax.set_title('(c)', fontsize=8.4)
    _style_ax(ax)

    ax = axes[1, 1]
    ax.plot(np.arange(len(res)), res, marker='o', ms=1.8, lw=0.5,
            color=C_BLUE2, alpha=0.75)
    ax.axhline(0, color=C_WARN, lw=1.0)
    ax.set_xlabel('样本序号', fontsize=8.5)
    ax.set_ylabel('残差', fontsize=8.5)
    ax.set_title('(d)', fontsize=8.4)
    _style_ax(ax)

    fig.tight_layout()
    return finalize_figure(fig, OUT / 'fig_q1_residual')


# ─────────────────────────────────────────────────────────────
# Q2
# ─────────────────────────────────────────────────────────────

def fig_q2_pi_heatmap():
    """化合物 × 感官的逐列置换重要性（主证据）。

    完全照队友 figs.py:508-550 的 fig_heat_clust 逻辑：
    ① 取重要性最强的前 TOPN 感官 × TOPN 化合物子阵（队友取 16，本图取 20）；
    ② 行、列各自 average-linkage 聚类后重排，让高值成块；
    ③ 格内标数值，字号按格宽自适应，深色格用白字；
    ④ 白色细格线、去四边框、无刻度长度。
    仅一处不同：队友用 imshow，本图用 pcolormesh —— imshow 导出 SVG 会把矩阵
    内嵌成 base64 位图（打开不可编辑），pcolormesh 才是真矢量。
    全量 50×46 矩阵见 results/q2_feature_pi.csv。
    """
    from scipy.cluster.hierarchy import linkage, leaves_list

    TOPN = 20

    # π_thr 必须取 q* = q_target（q2_run_log 记的 1.0）那一行 = 0.5022，
    # 不是 pi_thr 的最大值（那是 q=5 的 0.5111，会把 46 列筛成 44 列）。
    fdr = _read('q2_fdr.csv')
    qlog = _read_json('q2_run_log.json')
    q_target = float(qlog.get('q_target', 1.0))
    row = fdr.iloc[(fdr['q'] - q_target).abs().argmin()]
    pi_thr = float(row['pi_thr'])

    pi = _read('q2_feature_pi.csv')
    feats = [c for c in pi.columns if c != 'sens']
    V = pi[feats].to_numpy(dtype=float)                 # (50 感官, 231 化合物)
    keep = V.max(axis=0) >= pi_thr
    feats_kept = [f for f, k in zip(feats, keep) if k]
    Vk = V[:, keep]                                     # (50, 46)

    # ① 取最强的 TOPN 行 × TOPN 列
    ri = np.argsort(-Vk.max(axis=1))[:TOPN]
    ci = np.argsort(-Vk.max(axis=0))[:TOPN]
    Vk = Vk[np.ix_(ri, ci)]
    sens_kept = [pi.sens.tolist()[i] for i in ri]
    feats_kept = [feats_kept[i] for i in ci]

    # ② 行列聚类重排（队友的 linkage + leaves_list）
    if Vk.shape[0] >= 2 and Vk.shape[1] >= 2:
        ro = leaves_list(linkage(Vk, method='average', metric='euclidean'))
        co = leaves_list(linkage(Vk.T, method='average', metric='euclidean'))
        Vk = Vk[np.ix_(ro, co)]
        sens_kept = [sens_kept[i] for i in ro]
        feats_kept = [feats_kept[i] for i in co]

    # 宽扁版式：宽 6.5in = 468pt，落 \textwidth 后缩放 0.969（>0.95），字不会变小
    fig, ax = plt.subplots(figsize=(6.5, 4.9))
    mesh = _pcolormesh(ax, Vk, feats_kept, sens_kept, CMAP_SEQ,
                       cbar_label='逐列置换重要性 $\\pi$', vmin=0.0,
                       annotate=True, fmt='{:.2f}', annot_fontsize=5.6)
    ax.tick_params(axis='x', labelsize=6.4, rotation=90)
    ax.tick_params(axis='y', labelsize=6.8)
    for lbl in ax.get_xticklabels():
        lbl.set_ha('center')
    # ③ 白色细格线（队友 fig_heat_clust 的 minor grid）
    ax.set_xticks(np.arange(Vk.shape[1] + 1), minor=True)
    ax.set_yticks(np.arange(Vk.shape[0] + 1), minor=True)
    ax.grid(which='minor', color='white', lw=0.8)
    ax.tick_params(which='minor', length=0)
    ax.set_xlabel(f'化合物（重要性前 {TOPN}，最大 $\\pi\\geq${pi_thr:.4f}）', fontsize=9.5)
    ax.set_ylabel(f'感官维度（重要性前 {TOPN}，行序经聚类重排）', fontsize=9.5)
    ax.set_title('', fontsize=1)
    return finalize_figure(fig, OUT / 'fig_q2_pi_heatmap')


def fig_q2_graph():
    """共表达图社区结构诊断：三种口径并置。

    (a) Louvain 模块度 Q 随阈值 τ 的变化，叠加度保持零分布的 95% 分位带；
    (b) 三种口径（原脚本组合拉普拉斯 / 归一化拉普拉斯 / Louvain）的
        模块内与模块间平均 |ρ| 对比 —— 原脚本的内间比 1.56 来自退化划分，
        归一化后升到 1.76，Louvain 社区下才拉开到约 2。
    """
    d = _read('q2_graph_stats.csv')
    s = _read_json('q2_graph_summary.json')

    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.9),
                             gridspec_kw={'width_ratios': [1.15, 1.0]})

    ax = axes[0]
    ax.plot(d.tau, d.modularity, '-o', ms=3.4, lw=1.3, color=C_BLUE,
            label='Louvain 模块度 $Q$')
    ax.fill_between(d.tau, 0, d.Q_null_p95, color=C_WARN, alpha=0.18, lw=0,
                    label='度保持零分布 95% 分位')
    ax.plot(d.tau, d.Q_null_p95, '--', lw=1.0, color=C_WARN)
    ax.plot(d.tau, d.spectral_Q_fix, '-s', ms=3.0, lw=1.1, color=C_GRAY,
            label='谱聚类（归一化 $L$）$Q$')
    ax.axvline(s['main_tau'], ls=':', lw=1.0, color=C_DEEP)
    # 标注挪到竖线左侧的空白里：原来放在 (τ+0.012, 0.30)，而零分布 95% 分位
    # 那条橙色虚线是斜的（0.25→0.39），从文字左端下方穿到右端上方，整段字都被
    # 斜线切过。新位置在虚线之下、灰色方块之上，两头都不碰。
    ax.annotate(f'主阈值 $\\tau$={s["main_tau"]:.2f}',
                xy=(s['main_tau'], 0.03),
                xytext=(s['main_tau'] - 0.14, 0.055),
                fontsize=6.4, color=C_DEEP,
                arrowprops=dict(arrowstyle='-', lw=0.6, color=C_DEEP))
    ax.set_xlabel('边阈值 $\\tau$（$|\\rho|\\geq\\tau$）', fontsize=8.4)
    ax.set_ylabel('模块度 $Q$', fontsize=8.4)
    ax.tick_params(labelsize=7.4)
    # 主阈值竖虚线是画满整个高度的，而图例放在左上、宽度占了轴宽的 2/3，
    # 虚线正好从"95% 分位"和"Q"中间穿过去，字被切成两半。图例加不透明白底，
    # 让虚线从图例后面走；这块区域（Q 0.47–0.63）没有曲线，白底不遮数据。
    ax.legend(frameon=True, facecolor='white', edgecolor=COOL_GRID,
              framealpha=1.0, fontsize=6.4, loc='upper left',
              bbox_to_anchor=(0.012, 1.0), borderaxespad=0.0,
              borderpad=0.45, handletextpad=0.55)
    _style_ax(ax)
    add_panel_label(ax, '(a)', x=-0.22, y=1.04, fontsize=7.8)

    ax = axes[1]
    x = np.arange(len(d))
    ax.plot(x, d.within_between_yuan, '-o', ms=3.0, lw=1.2, color=C_WARN,
            label='原脚本（组合 $L$）')
    ax.plot(x, d.within_between_fix, '-^', ms=3.0, lw=1.2, color=C_GRAY,
            label='谱聚类（归一化 $L$）')
    ax.plot(x, d.within_between_louvain, '-s', ms=3.0, lw=1.3, color=C_BLUE,
            label='Louvain')
    ax.axhline(1.0, ls=':', lw=1.0, color=C_DEEP)
    # y=1.03 时 6.4 pt 字的下缘正好压在这条 y=1 的点线上，抬到 1.10 留出约 3 pt。
    ax.text(0.1, 1.10, '比值 = 1（社区无信息）', fontsize=6.4, color=C_DEEP)
    ax.set_xticks(x)
    ax.set_xticklabels([f'{t:.2f}' for t in d.tau], fontsize=7.0, rotation=45)
    ax.set_xlabel('边阈值 $\\tau$', fontsize=8.4)
    ax.set_ylabel('模块内/间平均 $|\\rho|$ 之比', fontsize=8.4)
    ax.tick_params(axis='y', labelsize=7.4)
    ax.set_ylim(0.9, max(d.within_between_fix.max(),
                         d.within_between_louvain.max()) * 1.32)
    # 三个条目横排会撑到 183 pt，而这块面板只有 139 pt 宽，图例因此整体溢出到
    # 坐标轴外、压住 y 轴刻度。改两列后宽约 100 pt，能完整落在轴内；再加白底，
    # 因为第二行正好压在 3.0 那条 y 网格线上。
    ax.legend(frameon=True, facecolor='white', edgecolor=COOL_GRID,
              framealpha=1.0, fontsize=6.2, loc='upper left', ncol=2,
              columnspacing=0.9, handletextpad=0.4, borderpad=0.4)
    _style_ax(ax)
    add_panel_label(ax, '(b)', x=-0.24, y=1.04, fontsize=7.8)

    fig.tight_layout()
    return finalize_figure(fig, OUT / 'fig_q2_graph')


def fig_q2_jaccard():
    """跨模型 Top-10 的 Jaccard 相似度（负结果）。

    箱体由 ax.boxplot 直接从 q2_jaccard.csv 的 50 个观测画出（箱线本身就定义为
    数据的分位数，不是"重算论文数字"）；图内标注的中位数读自
    q2_jaccard_stats.csv，由 q2.py 落盘。
    """
    j = _read('q2_jaccard.csv')
    st = _read('q2_jaccard_stats.csv').iloc[0]
    cols = ['j_lgbm_et', 'j_lgbm_ridge', 'j_et_ridge', 'j_mean']
    labs = ['LightGBM\nvs ExtraTrees', 'LightGBM\nvs Ridge',
            'ExtraTrees\nvs Ridge', '三法平均']
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    data = [j[c].to_numpy(dtype=float) for c in cols]
    bp = ax.boxplot(data, patch_artist=True, widths=0.5, showfliers=False,
                    medianprops=dict(color=C_DEEP, lw=1.8),
                    boxprops=dict(lw=1.0, edgecolor=COOL_EDGE),
                    whiskerprops=dict(lw=0.9, color=C_GRAY),
                    capprops=dict(lw=0.9, color=C_GRAY))
    for patch, col in zip(bp['boxes'], CAT):
        patch.set_facecolor(col)
        patch.set_alpha(0.40)
    rng = np.random.default_rng(2026)
    for i, v in enumerate(data, start=1):
        ax.scatter(rng.normal(i, 0.055, len(v)), v, s=16, color=C_BLUE,
                   alpha=0.40, edgecolor='none', zorder=3)
    ax.axhline(0.0, color=COOL_GRID, linewidth=1.0)
    ax.set_xticks(range(1, len(cols) + 1))
    ax.set_xticklabels(labs, fontsize=9.5)
    ax.set_ylabel('Top-10 入选集合的 Jaccard 相似度', fontsize=10.5)
    ax.set_ylim(-0.03, 0.62)
    ax.tick_params(axis='y', labelsize=9.5)
    # 这行统计原来排成单行，9 pt 下宽 224.5 pt、右端到 291.1 pt，而右上图例从
    # 290.85 pt 起——两者直接贴上，读起来像 "n=50▭ 四分位箱"。拆成两行后第一行
    # 只有 139.9 pt，留出 84 pt 空档。
    ax.text(0.02, 0.97,
            f'三法平均：中位 {st["median"]:.3f}，IQR {st["iqr"]:.3f}\n'
            f'最低 {st["min"]:.3f}；n={int(st["n_targets"])}',
            transform=ax.transAxes, fontsize=9, va='top', color=C_DEEP,
            linespacing=1.5)
    handles = [Patch(facecolor=C_BLUE, alpha=0.40, edgecolor=COOL_EDGE, label='四分位箱'),
               Line2D([], [], color=C_DEEP, lw=1.8, label='中位数'),
               Line2D([], [], color=C_BLUE, marker='o', lw=0, ms=4, alpha=0.6,
                      label='单个感官维')]
    ax.legend(handles=handles, loc='upper right', fontsize=8.5, ncol=1)
    _style_ax(ax)
    return finalize_figure(fig, OUT / 'fig_q2_jaccard')


def fig_q2_oav():
    """OAV 棒棒糖图（仅香气化合物，理化指标已剔除）。

    Top-20 按 oav_p95 降序 + 其余 15 个的聚合行，行集合与三档配色判据全部由
    q2.py 落盘在 q2_oav_display.csv。对数轴因为跨 4 个数量级。
    """
    o = _read('q2_oav_display.csv')
    band_color = {'ge1': C_TEAL, 'mid': C_WARN, 'low': C_GRAY}
    band_label = {'ge1': 'OAV 中位 ≥ 1（确定贡献）',
                  'mid': 'OAV 中位 0.5–1（需化学论证）',
                  'low': 'OAV 中位 < 0.5（贡献可忽略）'}
    fig, ax = plt.subplots(figsize=(5.4, 6.0))
    y = np.arange(len(o))[::-1]
    vals = o.oav_median.clip(lower=1e-4).to_numpy(float)
    cols = [band_color[b] for b in o.band]
    ax.hlines(y, 1e-4, vals, color=cols, linewidth=1.8, zorder=2)
    for yi, v, b in zip(y, vals, o.band):
        marker = 'D' if b == 'ge1' else ('s' if b == 'mid' else 'o')
        ax.scatter(v, yi, s=42, color=band_color[b], marker=marker, zorder=3,
                   edgecolor='white', linewidth=0.6)
    ax.set_yticks(y)
    lbls = [t if len(t) <= 20 else t[:19] + '…' for t in o.feat.tolist()]
    ax.set_yticklabels(lbls, fontsize=7.6)
    for lbl, b in zip(ax.get_yticklabels(), o.band):
        lbl.set_color(band_color[b])
    ax.set_xscale('log')
    ax.set_xlim(1e-4, 60)
    ax.set_xlabel('OAV 中位数（对数轴）', fontsize=10.5)
    ax.tick_params(axis='x', labelsize=9.5)
    for xv, lab, col, ls in ((1.0, 'OAV = 1', C_DEEP, '--'),
                             (0.5, 'OAV = 0.5', C_GRAY, ':')):
        ax.axvline(xv, color=col, linestyle=ls, linewidth=1.2)
    handles = [Line2D([], [], color=band_color[k], marker=m, lw=1.8, ms=6,
                      label=band_label[k])
               for k, m in (('ge1', 'D'), ('mid', 's'), ('low', 'o'))]
    # 图例原来放 lower right，正好插在最后三行（ethyl.butyrate /
    # phenethyl_alcohol / 其余 15 个）中间：21 行铺满了整个绘图区，里面找不到
    # 任何一处空白放得下 156 pt 宽的图例，而且 OAV=0.5 与 OAV=1 两条竖参考线会
    # 直接从图例文字里穿过。改为把绘图区顶部让出 45 pt，图例横排到图上方，
    # 不遮任何数据、也不与参考线相交。
    fig.subplots_adjust(top=0.84)
    ax.legend(handles=handles, loc='lower left', bbox_to_anchor=(0.0, 1.005),
              fontsize=8.5, ncol=1, frameon=False, labelspacing=0.6,
              borderaxespad=0)
    _style_ax(ax, ygrid=False)
    ax.grid(axis='x', color=COOL_GRID, linewidth=0.7)
    ax.grid(axis='y', visible=False)
    return finalize_figure(fig, OUT / 'fig_q2_oav')


def fig_q2_convergence():
    """π 的 bootstrap 收敛曲线：200 次重采样是否够用。

    主曲线 = 50 个靶的 π 在香气特征池内的均值轨迹；阴影 = 跨靶的 p5–p95 带。
    数据全部来自 q2_pi_convergence.csv，拐点用"带半宽降到初值 20% 以内"判据，
    这个判据只依赖表内两列，属于显示层判读，不产生新的论文数值。
    """
    c = _read('q2_pi_convergence.csv')
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    ax.fill_between(c.n_boot, c.pi_mean_p5, c.pi_mean_p95,
                    color=C_BLUE2, alpha=0.20, linewidth=0, label='跨靶 5–95 分位')
    ax.plot(c.n_boot, c.pi_mean_across_sens, color=C_DEEP, linewidth=1.8,
            marker='o', markevery=max(1, len(c) // 10), markersize=3.4,
            label='50 靶均值')
    # 拐点：相对末次带宽的一半，找到首次进入该带宽的 n
    half_w = (c.pi_mean_p95 - c.pi_mean_p5) / 2.0
    target = half_w.iloc[-1] * 1.10
    idx = int(np.argmax(half_w.to_numpy() <= target))
    n_knee = int(c.n_boot.iloc[idx])
    ax.axvline(n_knee, color=C_WARN, linestyle='--', linewidth=1.2)
    ax.annotate(f'n = {n_knee} 后带宽\n基本不再收窄', (n_knee, c.pi_mean_across_sens.iloc[idx]),
                xytext=(n_knee + len(c) * 0.05, c.pi_mean_across_sens.max() * 0.93),
                fontsize=9, color=C_WARN,
                arrowprops=dict(arrowstyle='->', color=C_WARN, lw=0.9))
    ax.set_xlabel('bootstrap 重采样次数', fontsize=10.5)
    ax.set_ylabel('香气特征池内的平均入选率 $\\bar{\\pi}$', fontsize=10.5)
    ax.tick_params(labelsize=9.5)
    ax.set_xlim(1, len(c))
    # p5–p95 带铺满整个绘图区宽度，"跨靶 5–95 分位"这一行原本落在带的下边缘上：
    # 浅蓝色的带色块画在浅蓝底上等于看不见，文字还被带的下边界从中间切开。
    # 两条一起改——图例挪到带顶部以上的白边里（那里没有任何数据），
    # 再加白底和一圈浅灰细线，即使以后带宽变化也不会再糊在一起。
    ax.legend(loc='upper right', fontsize=9, frameon=True, facecolor='white',
              edgecolor=COOL_GRID, framealpha=1.0, borderpad=0.5,
              labelspacing=0.5)
    _style_ax(ax)
    return finalize_figure(fig, OUT / 'fig_q2_convergence')


# ─────────────────────────────────────────────────────────────
# Q3
# ─────────────────────────────────────────────────────────────

def fig_q3_front():
    """Pareto 前沿双投影：上 f1–f3（主权衡），下 f1–f2（软约束违反）。

    MILP 7 点 vs NSGA-II 189 点。删掉原第三栏 f3–f2：f1–f3 与 f1–f2 已张成三维
    关系，第三投影只重复信息、还把每栏压到 5 in 宽导致字号崩到 3 pt。
    """
    f = _read('q3_fronts.csv')
    milp = f[f.source == 'MILP']
    heur = f[f.source == 'NSGA-II']
    panels = [('f3', '$f_3$ 干预代价（越大越省事）', '(a)'),
              ('f2', '$f_2$ 软约束违反量', '(b)')]
    fig, axes = plt.subplots(2, 1, figsize=(5.4, 5.6), sharex=True)
    for ax, (ya, yl, tag) in zip(axes, panels):
        ax.scatter(heur.f1, heur[ya], s=18, color=C_GRAY, alpha=0.55,
                   edgecolor='none', label=f'NSGA-II（{len(heur)} 点）', zorder=2)
        ax.scatter(milp.f1, milp[ya], s=120, marker='*', color=C_WARN,
                   edgecolor=C_DEEP, linewidth=0.6,
                   label=f'Gurobi MILP（{len(milp)} 点）', zorder=4)
        ax.set_ylabel(yl, fontsize=10.5)
        ax.tick_params(labelsize=9.5)
        _style_ax(ax)
        add_panel_label(ax, tag, x=-0.13, y=1.02, fontsize=11)
    axes[-1].set_xlabel('$f_1$ 感官偏差（加权 L1，越小越好）', fontsize=10.5)
    # 基线 f1（不改动时的偏差）由 q3_waterfall.csv 的 baseline 行给出
    wf = _read('q3_waterfall.csv')
    base = wf[wf.group == '__baseline__']
    if len(base):
        f1_base = float(base.f1_after.iloc[0])
        for ax in axes:
            ax.axvline(f1_base, color=C_DEEP, linestyle=':', linewidth=1.2)
        axes[0].text(f1_base, axes[0].get_ylim()[1] * 0.98, f' 基线 $f_1$={f1_base:.2f}',
                     fontsize=9, color=C_DEEP, va='top', ha='left')
    handles = [Line2D([], [], color=C_GRAY, marker='o', lw=0, ms=5, alpha=0.7,
                      label=f'NSGA-II（{len(heur)} 点）'),
               Line2D([], [], color=C_WARN, marker='*', lw=0, ms=10,
                      markeredgecolor=C_DEEP, label=f'Gurobi MILP（{len(milp)} 点）')]
    # 图例原来在 upper right，而 NSGA-II 的 115 个点正好堆在那一角（f1 35–45、
    # f3 18–25），图标和文字直接压在点云上。面板 (a) 的左上角是空的（MILP 星
    # 最高只到 f3≈11、最左 f1≈20.8，点云从 f1≈34 才开始），挪过去即可。
    axes[0].legend(handles=handles, loc='upper left', fontsize=9)
    return finalize_figure(fig, OUT / 'fig_q3_front')


def fig_q3_deltas():
    """每个 Pareto 点相对风格参考谱的逐化合物改动量（log10 域的 Δ），数值直接印在格里。"""
    d = _read('q3_deltas.csv')
    p = _read('q3_pareto.csv')
    rows = sorted(d.point.unique(), key=lambda s: int(s[1:]))
    cols = list(dict.fromkeys(d.sort_values('feat').feat.tolist()))
    M = pd.DataFrame(0.0, index=rows, columns=cols)
    for _, r in d.iterrows():
        M.loc[r.point, r.feat] = float(r.delta)
    order = np.argsort(-M.abs().max(axis=0).to_numpy())
    M = M.iloc[:, order]
    f1map = dict(zip(p.point, p.f1))
    ylabels = [f'{pt}（$f_1$={f1map.get(pt, float("nan")):.1f}）' for pt in rows]
    lim = float(np.abs(M.to_numpy()).max())

    fig, ax = plt.subplots(figsize=(5.2, 4.0))
    # 格子只有 14.6 pt 宽，而两位小数在 7.5 pt 下要 18.3 pt——每格左右各溢出
    # 3.7 pt，相邻两格的数字连成一片（"-7.04" + "0.00" 读成 "7.040.00"）。
    # 实测一字宽预算 13.4 pt：改 1 位小数 + 6.5 pt 后 "-7.0" 只有 11.9 pt，
    # 格内还剩 2.7 pt 余量；再小就会低于 6 pt 下限。
    _pcolormesh(ax, M.to_numpy(), M.columns.tolist(), ylabels, CMAP_DIV,
                cbar_label='$\\Delta$（$\\log_{10}$ 域浓度调整量）',
                vmin=-lim, vmax=lim, annotate=True, fmt='{:.1f}', annot_fontsize=6.5)
    ax.tick_params(axis='x', labelsize=8.5, rotation=45)
    for lbl in ax.get_xticklabels():
        lbl.set_ha('right')
    ax.tick_params(axis='y', labelsize=8.5)
    ax.set_xlabel('化合物（按最大改动幅度排序）', fontsize=10.5)
    ax.set_ylabel('Pareto 点（按 $f_1$ 由小到大）', fontsize=10.5)
    return finalize_figure(fig, OUT / 'fig_q3_deltas')


def fig_q3_surrogate_cv():
    """线性代理（PLS）的逐维 5 折 CV R²，Top-15 按 |R²| 排序。"""
    s = _read('q3_surrogate.csv')
    s = s.reindex(s.cv_r2.abs().sort_values(ascending=False).index).head(15)
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    y = np.arange(len(s))[::-1]
    cols = [C_BLUE if v > 0 else C_WARN for v in s.cv_r2]
    ax.hlines(y, 0, s.cv_r2, color=cols, linewidth=1.8, zorder=2)
    for yi, v, c in zip(y, s.cv_r2, cols):
        ax.scatter(v, yi, s=44, color=c, marker='o', edgecolor='white',
                   linewidth=0.6, zorder=3)
    ax.axvline(0.0, color=C_DEEP, linewidth=1.2)
    ax.set_yticks(y)
    ax.set_yticklabels(s.sens.tolist(), fontsize=9)
    ax.set_xlabel('线性代理的 5 折 CV $R^2$', fontsize=10.5)
    ax.tick_params(axis='x', labelsize=9.5)
    handles = [Line2D([], [], color=C_BLUE, marker='o', lw=1.8, ms=6, label='$R^2>0$'),
               Line2D([], [], color=C_WARN, marker='o', lw=1.8, ms=6, label='$R^2\\leq0$')]
    ax.legend(handles=handles, loc='lower right', fontsize=9)
    _style_ax(ax, ygrid=False)
    ax.grid(axis='x', color=COOL_GRID, linewidth=0.7)
    ax.grid(axis='y', visible=False)
    return finalize_figure(fig, OUT / 'fig_q3_surrogate_cv')


def fig_q3_surrogate_err():
    """代理误差上界 / 该维标准差，Top-15。超过 1 倍标准差即"该维不可分"——
    这是"前沿细排序不可信"的直接证据（50/50 全部超）。"""
    s = _read('q3_surrogate.csv')
    s = s.sort_values('err_max_over_sd', ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    y = np.arange(len(s))[::-1]
    ax.hlines(y, 0, s.err_max_over_sd, color=C_WARN, linewidth=1.8, zorder=2, alpha=0.85)
    ax.scatter(s.err_max_over_sd, y, s=44, color=C_WARN, marker='s',
               edgecolor='white', linewidth=0.6, zorder=3)
    ax.axvline(1.0, color=C_DEEP, linestyle='--', linewidth=1.2)
    ax.text(1.05, len(s) - 0.6, '误差 = 1 倍标准差\n（超过即不可分）', fontsize=9,
            color=C_DEEP, va='top')
    ax.set_yticks(y)
    ax.set_yticklabels(s.sens.tolist(), fontsize=9)
    ax.set_xlabel('代理误差上界 / 该维标准差', fontsize=10.5)
    ax.tick_params(axis='x', labelsize=9.5)
    _style_ax(ax, ygrid=False)
    ax.grid(axis='x', color=COOL_GRID, linewidth=0.7)
    ax.grid(axis='y', visible=False)
    return finalize_figure(fig, OUT / 'fig_q3_surrogate_err')


DIM_ZH = {
    'A_malt_all': '麦芽香', 'A_hops_all': '酒花香', 'A_esters_all': '酯香',
    'F_malt_all': '麦芽风味', 'F_hops_all': '酒花风味', 'F_esters_all': '酯类风味',
    'bitternes': '苦度', 'sweetness': '甜度', 'acidity': '酸度', 'body': '醇厚度',
}


def fig_q3_radar():
    """三线画像：目标风格实测 / 对照风格实测 / 最优 Pareto 点的代理预测。

    版式照抄队友 figs.py:550-580（fill alpha=.10 + 轴外图例），但**去掉**他那条
    用 rng.normal 伪造的"迁移后画像"——那条线没有任何数据来源。本图三条线全部
    来自 q3_style_profile.csv，由 q3.py 从实测均值与代理预测落盘。
    """
    sp = _read('q3_style_profile.csv', encoding='utf-8-sig')
    dims = [d for d in DIM_ZH if d in set(sp.dim)]
    series = sp.series.unique().tolist()
    if len(series) != 3:
        raise SystemExit(f'q3_style_profile.csv 应有 3 条线，实际 {len(series)}')

    angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    angles += angles[:1]
    fig = plt.figure(figsize=(5.4, 5.0))
    ax = fig.add_subplot(111, polar=True)
    styles = [(C_BLUE, 'o', '-'), (C_WARN, '^', '--'), (C_TEAL, 's', '-.')]
    allv = []
    for (color, marker, ls), s in zip(styles, series):
        d = sp[sp.series == s].set_index('dim').reindex(dims)
        if d.value.isna().any():
            raise SystemExit(f'q3_style_profile.csv 缺少 {s} 的部分维度：'
                             f'{d.index[d.value.isna()].tolist()}')
        v = d.value.to_numpy(dtype=float)
        allv.extend(v.tolist())
        # 闭合多边形：必须用 np.r_ 拼接（v + v[:1] 是逐元素加法，不是拼接）
        closed = np.r_[v, v[:1]]
        ax.plot(angles, closed, color=color, linewidth=1.7, linestyle=ls,
                marker=marker, markersize=4, label=s)
        ax.fill(angles, closed, color=color, alpha=0.10)
    lo = float(np.floor(min(allv) * 10) / 10) - 0.1
    hi = float(np.ceil(max(allv) * 10) / 10) + 0.1
    ax.set_ylim(lo, hi)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([DIM_ZH[d] for d in dims], fontsize=10)
    ax.tick_params(axis='y', labelsize=7.5)
    ax.set_rlabel_position(72)
    ax.grid(color=COOL_GRID, linewidth=0.7)
    ax.spines['polar'].set_color(COOL_EDGE)
    ax.spines['polar'].set_linewidth(1.0)
    ax.legend(loc='upper right', bbox_to_anchor=(1.32, 1.14), fontsize=8.5)
    return finalize_figure(fig, OUT / 'fig_q3_radar')


def fig_q3_waterfall():
    """最优 Pareto 点（f1 最小）的 f1 逐组分解。

    版式照抄队友 figs.py:609-637 的浮动柱骨架，但数据换成 q3_waterfall.csv
    （队友那版的 delta 是硬编码假数），并保留 q3.py 里已校验的闭合关系：
    末柱 f1_after 必须等于该点的 f1。
    """
    wf = _read('q3_waterfall.csv')
    pts = sorted(wf.point.unique(), key=lambda s: int(s[1:]))
    best = pts[0]                                    # P1 = f1 最小
    d = wf[wf.point == best].sort_values('order').reset_index(drop=True)
    base = float(d[d.group == '__baseline__'].f1_after.iloc[0])
    steps = d[d.group != '__baseline__']
    labels = ['基线'] + [g for g in steps.group] + ['最优解']
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    x = np.arange(len(labels))
    # 首柱：基线绝对值
    ax.bar(x[0], base, width=0.62, color=C_GRAY, alpha=0.85, edgecolor='white')
    ax.text(x[0], base + 0.4, f'{base:.2f}', ha='center', va='bottom', fontsize=9, color=C_DEEP)
    # 中间：浮动柱
    for i, r in enumerate(steps.itertuples(), start=1):
        before = float(r.f1_after) - float(r.delta_f1)
        delta = float(r.delta_f1)
        bottom = min(before, float(r.f1_after))
        ax.bar(x[i], abs(delta), bottom=bottom, width=0.62,
               color=C_TEAL if delta < 0 else C_WARN, alpha=0.85, edgecolor='white')
        ax.text(x[i], float(r.f1_after) - abs(delta) / 2.0, f'{delta:+.2f}',
                ha='center', va='center', fontsize=8.5,
                color='white' if abs(delta) > 2.0 else C_DEEP)
    # 末柱：收敛后的绝对值
    final = float(steps.f1_after.iloc[-1]) if len(steps) else base
    ax.bar(x[-1], final, width=0.62, color=C_DEEP, alpha=0.9, edgecolor='white')
    ax.text(x[-1], final + 0.4, f'{final:.2f}', ha='center', va='bottom', fontsize=9, color=C_DEEP)
    # 连接线
    levels = [base] + steps.f1_after.tolist()
    for i in range(len(levels) - 1):
        ax.plot([x[i] + 0.31, x[i + 1] - 0.31], [levels[i], levels[i]],
                color=C_GRAY, linewidth=0.8, linestyle=':')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, rotation=18)
    ax.set_ylabel('$f_1$ 感官偏差（加权 L1）', fontsize=10.5)
    ax.set_ylim(0, base * 1.12)
    ax.tick_params(axis='y', labelsize=9.5)
    handles = [Patch(facecolor=C_TEAL, alpha=0.85, label='降低 $f_1$ 的改动'),
               Patch(facecolor=C_WARN, alpha=0.85, label='升高 $f_1$ 的改动'),
               Patch(facecolor=C_DEEP, alpha=0.9, label='分解终点')]
    ax.legend(handles=handles, loc='upper right', fontsize=8.5)
    _style_ax(ax)
    return finalize_figure(fig, OUT / 'fig_q3_waterfall')


# ─────────────────────────────────────────────────────────────
# 技术路线图（照抄队友 figs.py:127-178 的 box/arrow 骨架，内容换成本项目）
# ─────────────────────────────────────────────────────────────

def fig_flow():
    """技术路线：口径先行 → 正向映射 → 归因解释 → 逆用生成。

    骨架照抄队友 figs.py:127-178（FancyBboxPatch 圆角框 + 三行泳道 + 中部斜体
    提示 + 冷色盘），只改三处：①去掉图内总标题（论文 \\caption 负责）；
    ②斜向箭头换成行间正交总线，避免穿框与穿字；③文案换成本项目实测结论。
    """
    fig, ax = plt.subplots(figsize=(6.6, 3.48))
    ax.set_xlim(0, 11)
    ax.set_ylim(-0.42, 5.4)
    ax.axis('off')

    XC = (1.95, 5.50, 9.05)          # 三列中心
    W = 2.95                          # 统一框宽
    H = 0.82
    YR = (4.60, 3.20, 1.90, 0.62)     # 四行中心
    BUS = (3.86, 2.55, 1.26)          # 行间正交总线高度

    def box(x, y, text, fc, ec, fs=7.8, bold=False):
        ax.add_patch(FancyBboxPatch((x - W / 2, y - H / 2), W, H,
                                    boxstyle='round,pad=0.055,rounding_size=0.08',
                                    fc=fc, ec=ec, lw=1.1, zorder=2))
        ax.text(x, y, text, ha='center', va='center', fontsize=fs,
                fontweight='bold' if bold else 'normal', color='#12303F',
                zorder=3, linespacing=1.45)

    def hline(y, x1, x2):
        ax.annotate('', xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle='-|>', lw=1.3, color=C_GRAY,
                                    mutation_scale=12, shrinkA=0, shrinkB=0),
                    zorder=1)

    def bus(y_from, y_to, y_bus):
        """右列 → 左列的 L 形正交连接：下—左—下，箭头落在下一行框顶。"""
        x_r, x_l = XC[2], XC[0]
        y_top = y_from - H / 2
        y_bot = y_to + H / 2
        ax.plot([x_r, x_r], [y_top, y_bus], color=C_GRAY, lw=1.3, zorder=1,
                solid_capstyle='round')
        ax.plot([x_r, x_l], [y_bus, y_bus], color=C_GRAY, lw=1.3, zorder=1,
                solid_capstyle='round')
        ax.annotate('', xy=(x_l, y_bot), xytext=(x_l, y_bus),
                    arrowprops=dict(arrowstyle='-|>', lw=1.3, color=C_GRAY,
                                    mutation_scale=12, shrinkA=0, shrinkB=0),
                    zorder=1)

    # ── 第 0 行：数据体检 ──
    box(XC[0], YR[0], '附件 1–8\n化学 / 感官 / 阈值', C_PALE, C_BLUE2)
    box(XC[1], YR[0], '§5 数据体检\n6 处题面与实测矛盾', '#E8F1F5', C_BLUE, 7.6, True)
    box(XC[2], YR[0], '统一数据底座 D0\n250×231 / 250×50', C_PALE, C_BLUE2)
    hline(YR[0], XC[0] + W / 2, XC[1] - W / 2)
    hline(YR[0], XC[1] + W / 2, XC[2] - W / 2)

    # ── 第 1 行：Q1 ──
    box(XC[0], YR[1], 'Q1 标签口径\n连续强度（0–6 不可反解）', '#DDEFF2', C_TEAL, 7.6, True)
    box(XC[1], YR[1], '嵌套 CV 四模型竞速\nRidge / EN / LGBM / ET', '#DDEFF2', C_TEAL)
    box(XC[2], YR[1], '$R^2$ 中位 0.1469\nhurdle 9 维 · 自助区间', '#DDEFF2', C_TEAL)
    hline(YR[1], XC[0] + W / 2, XC[1] - W / 2)
    hline(YR[1], XC[1] + W / 2, XC[2] - W / 2)

    # ── 第 2 行：Q2 ──
    box(XC[0], YR[2], 'Q2 共表达图诊断\n社区结构弱 → 改化学族', '#E4E8F5', C_PURPLE, 7.6, True)
    box(XC[1], YR[2], '逐列置换 $\\pi$\n阈值 0.5022 · 10 条入选', '#E4E8F5', C_PURPLE)
    box(XC[2], YR[2], 'OAV 分级\nA19 / B8 / C40 / N83', '#E4E8F5', C_PURPLE)
    hline(YR[2], XC[0] + W / 2, XC[1] - W / 2)
    hline(YR[2], XC[1] + W / 2, XC[2] - W / 2)

    # ── 第 3 行：Q3 ──
    box(XC[0], YR[3], 'Q3 收缩高斯生成\nLedoit–Wolf $\\delta$=0.6844', '#E3F0EC', C_TEAL, 7.6, True)
    box(XC[1], YR[3], 'PLS(8) 线性代理\n$\\varepsilon$-约束 MILP', '#E3F0EC', C_TEAL)
    box(XC[2], YR[3], '7 点 Pareto\n支配 NSGA-II 92.17%', '#E3F0EC', C_TEAL)
    hline(YR[3], XC[0] + W / 2, XC[1] - W / 2)
    hline(YR[3], XC[1] + W / 2, XC[2] - W / 2)

    # ── 行间正交总线（右列 → 下一行左列）──
    bus(YR[0], YR[1], BUS[0])
    bus(YR[1], YR[2], BUS[1])
    bus(YR[2], YR[3], BUS[2])

    ax.text(5.50, -0.36,
            '三问共用：同一化学族分组 · 同一阈值表 · 同一 beer 对齐键',
            ha='center', va='center', fontsize=7.4, color=C_WARN, style='italic')
    return finalize_figure(fig, OUT / 'fig_flow')


def fig_q3_tornado():
    """Q3 灵敏度分析（龙卷风图）。

    版式照抄队友 figs.py:467-508 的 fig_tornado（barh 双向条 / 端点标数值 /
    零点竖线 / 右下图例 / clean_ax），但**数据来源不同**：队友那份的 f1 来自
    他手写的解析公式 f1_of(p)，属于模拟值；本图的每一根条都是
    robustness_q3.py 里真解一次 MILP 得到的 Δf1。
    """
    d = _read('q3_sensitivity.csv')
    s = _read_json('q3_sensitivity_summary.json')
    base_f1 = float(s['base_f1'])

    # 每个参数取扰动范围的两端（可行解里 f1 最小/最大的那次）
    rows = []
    for (param, label), g in d.groupby(['param', 'label']):
        g = g[np.isfinite(g.f1)]
        if g.empty:
            continue
        a, b = g.loc[g.f1.idxmin()], g.loc[g.f1.idxmax()]
        # 参数扰动范围取自实际取值集合，不用 f1 极值对应的那次（k_max 摆幅为 0 时
        # idxmin/idxmax 会取到同一条记录，把 [15,35] 显示成 [15,15]）
        v_lo, v_hi = float(g.value.min()), float(g.value.max())
        rows.append(dict(param=param, label=label,
                         lo_val=v_lo, hi_val=v_hi,
                         lo=float(a.f1) - base_f1, hi=float(b.f1) - base_f1,
                         lo_at=float(a.value), hi_at=float(b.value),
                         span=abs(float(b.f1) - float(a.f1)),
                         n_lo=int(a.n_changed), n_hi=int(b.n_changed)))
    df = pd.DataFrame(rows).sort_values('span').reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    y = np.arange(len(df))
    ax.barh(y, df.lo, color=C_BLUE, alpha=0.85, height=0.60, label='参数下界')
    ax.barh(y, df.hi, color=C_TEAL, alpha=0.85, height=0.60, label='参数上界')

    span_max = max(df.lo.abs().max(), df.hi.abs().max(), 1e-9)
    pad = span_max * 0.045
    for i, r in df.iterrows():
        # 两端都标（含 0），避免"某端无条"被误读为画漏
        for v in (r.lo, r.hi):
            ha = 'right' if v < -1e-6 else 'left'
            ax.text(v + (-pad if v < -1e-6 else pad), i, f'{v:+.2f}'
                    if abs(v) >= 1e-6 else '0.00',
                    ha=ha, va='center', fontsize=7.6, color=C_DEEP)
    ax.axvline(0, color='#333333', lw=1.1)
    ax.set_yticks(y)
    ax.set_yticklabels([f'{r.label}\n[{r.lo_val:.4g}, {r.hi_val:.4g}]'
                        for _, r in df.iterrows()], fontsize=7.8)
    ax.set_xlim(-span_max * 1.34, span_max * 1.34)
    ax.set_xlabel('最优感官偏差 $f_1$ 相对基准的变化量（27 次重解 MILP）',
                  fontsize=9.0)
    _style_ax(ax)
    ax.legend(frameon=False, fontsize=8.0, loc='lower right')
    return finalize_figure(fig, OUT / 'fig_q3_tornado')


# ─────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────

FIGURES = {
    'flow': fig_flow,
    'q0_box_before_after': fig_q0_box_before_after,
    'q0_missing': fig_q0_missing,
    'q1_r2_forest': fig_q1_r2_forest,
    'q1_floor_vs_r2': fig_q1_floor_vs_r2,
    'q1_external': fig_q1_external,
    'q1_r2_dist': fig_q1_r2_dist,
    'q1_reg_fit': fig_q1_reg_fit,
    'q1_residual': fig_q1_residual,
    'q2_pi_heatmap': fig_q2_pi_heatmap,
    'q2_graph': fig_q2_graph,
    'q2_jaccard': fig_q2_jaccard,
    'q2_oav': fig_q2_oav,
    'q2_convergence': fig_q2_convergence,
    'q3_front': fig_q3_front,
    'q3_deltas': fig_q3_deltas,
    'q3_surrogate_cv': fig_q3_surrogate_cv,
    'q3_surrogate_err': fig_q3_surrogate_err,
    'q3_radar': fig_q3_radar,
    'q3_waterfall': fig_q3_waterfall,
    'q3_tornado': fig_q3_tornado,
}


def main():
    # Windows 控制台默认 GBK，中文与 ✓ 会抛 UnicodeEncodeError；显式改 UTF-8 并容错
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description='只读 results/ 出论文插图（PNG 300dpi + SVG）')
    ap.add_argument('--only', nargs='*', default=None, help='只画指定图，如 --only q3_front')
    args = ap.parse_args()

    # 强制显式调用：不使用 matplotlib 默认样式
    apply_publication_style(font_size=12, axes_linewidth=2.0, language='zh', contest=True)
    # 冷色盘的版式底色（背景纯白 / 边框 #333333），与队友一致
    plt.rcParams['axes.edgecolor'] = COOL_EDGE
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['savefig.facecolor'] = 'white'
    OUT.mkdir(parents=True, exist_ok=True)

    todo = {k: v for k, v in FIGURES.items() if args.only is None or k in args.only}
    unknown = set(args.only or []) - set(FIGURES)
    if unknown:
        raise SystemExit(f'未知图名 {sorted(unknown)}，可选：{list(FIGURES)}')

    saved = []
    for name, fn in todo.items():
        paths = fn()
        saved.extend(paths)
        print(f'  ✓ {name:20s} → ' + ', '.join(os.path.basename(p) for p in paths))
    print(f'共 {len(todo)} 图 / {len(saved)} 个文件 → {OUT}')
    return saved


if __name__ == '__main__':
    main()
