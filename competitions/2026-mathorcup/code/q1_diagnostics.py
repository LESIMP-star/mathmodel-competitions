# -*- coding: utf-8 -*-
"""q1_diagnostics.py — 由已冻结的折外预测与附件4 标签生成诊断表（不重训任何模型）

为什么单独一个脚本
  figures.py 的契约是"只读 results/，不重算任何进入论文的统计量"。而残差图需要
  (实测, 折外预测) 的逐样本配对，这份配对既不在 q1_predictions.csv 里（只有预测），
  也不该在绘图脚本里现算。故在此落地成 results/ 下的两个文件：
      results/q1_scatter_pairs.csv     250 行 × (beer + 2×50 列) 配对
      results/q1_residual_stats.csv    50 维的残差诊断（均值/标准差/偏度/峰度/正态性）
  之后 figures.py 只读这两个文件。

输入（全部只读）
  results/q1_predictions.csv   250 × 50 折外预测（q1.py 落盘）
  附件/4.csv                   250 × 50 感官标签

对齐键：beer（beer_id 只有 96 唯一值，禁用）。

用法：python code/q1_diagnostics.py
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
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'results')
DATA = os.path.join(ROOT, '附件')


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    pred = pd.read_csv(os.path.join(RES, 'q1_predictions.csv'))
    lab = pd.read_csv(os.path.join(DATA, '4.csv'))

    pred['beer'] = pred['beer'].astype(str).str.strip()
    lab['beer'] = lab['beer'].astype(str).str.strip()
    assert lab['beer'].is_unique, 'beer 在附件4 中不唯一'

    sens = [c for c in lab.columns[3:] if c in pred.columns]
    assert len(sens) == 50, f'感官列应为 50，实际 {len(sens)}'

    m = lab[['beer'] + sens].merge(pred[['beer'] + sens], on='beer',
                                   suffixes=('_true', '_pred'), how='inner')
    assert len(m) == 250, f'配对应为 250 行，实际 {len(m)}'

    # 配对表：y_true / y_pred 各 50 列
    pairs = {'beer': m['beer']}
    for s in sens:
        pairs[f'{s}_true'] = m[f'{s}_true'].to_numpy(float)
        pairs[f'{s}_pred'] = m[f'{s}_pred'].to_numpy(float)
    pd.DataFrame(pairs).to_csv(os.path.join(RES, 'q1_scatter_pairs.csv'),
                               index=False, encoding='utf-8-sig')

    # 残差诊断
    rows = []
    for s in sens:
        yt = m[f'{s}_true'].to_numpy(float)
        yp = m[f'{s}_pred'].to_numpy(float)
        ok = np.isfinite(yt) & np.isfinite(yp)
        r = yt[ok] - yp[ok]
        if len(r) < 8:
            continue
        z = (r - r.mean()) / (r.std(ddof=1) + 1e-12)
        try:
            W, p_sw = stats.shapiro(r)
        except Exception:
            W, p_sw = np.nan, np.nan
        rows.append(dict(
            sens=s, n=int(ok.sum()),
            res_mean=round(float(r.mean()), 6),
            res_sd=round(float(r.std(ddof=1)), 6),
            res_skew=round(float(stats.skew(r)), 4),
            res_kurt=round(float(stats.kurtosis(r)), 4),
            shapiro_W=round(float(W), 4),
            shapiro_p=round(float(p_sw), 6),
            max_abs_z=round(float(np.abs(z).max()), 4),
            n_abs_z_gt3=int((np.abs(z) > 3).sum()),
        ))
    st = pd.DataFrame(rows)
    st.to_csv(os.path.join(RES, 'q1_residual_stats.csv'), index=False,
              encoding='utf-8-sig')

    # 供正文引用的聚合结论
    summary = dict(
        n_samples=250, n_dims=len(st),
        median_abs_res_mean=round(float(st.res_mean.abs().median()), 6),
        median_res_sd=round(float(st.res_sd.median()), 6),
        n_shapiro_pass_05=int((st.shapiro_p > 0.05).sum()),
        n_abs_skew_gt_1=int((st.res_skew.abs() > 1).sum()),
        median_abs_skew=round(float(st.res_skew.abs().median()), 4),
        max_abs_z_overall=round(float(st.max_abs_z.max()), 4),
        total_abs_z_gt3=int(st.n_abs_z_gt3.sum()),
        alcohol=st[st.sens == 'alcohol'].iloc[0].to_dict() if (st.sens == 'alcohol').any() else None,
        note='残差 = 附件4 实测 − q1_predictions.csv 折外预测；不重训模型',
    )
    with open(os.path.join(RES, 'q1_residual_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f'写出 q1_scatter_pairs.csv（250 × {2*len(sens)+1}）')
    print(f'写出 q1_residual_stats.csv（{len(st)} 维）')
    print(f'写出 q1_residual_summary.json')
    print(f'  残差均值绝对值中位 {summary["median_abs_res_mean"]:.4f}，'
          f'残差标准差中位 {summary["median_res_sd"]:.4f}')
    print(f'  Shapiro 正态检验 p>0.05：{summary["n_shapiro_pass_05"]}/{len(st)} 维')
    print(f'  |偏度|>1：{summary["n_abs_skew_gt_1"]} 维；'
          f'|z|>3 的点共 {summary["total_abs_z_gt3"]} 个')
    return 0


if __name__ == '__main__':
    sys.exit(main())
