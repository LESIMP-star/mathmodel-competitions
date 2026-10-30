# -*- coding: utf-8 -*-
"""_notitle.py — 屏蔽图内总标题（移植自队友 A2600001 `run_figs_notitle.py`）

来源：`A2600001附件/A2600001附件/07_源代码/run_figs_notitle.py`（29 行，只改了 import）。

为什么需要
  绘图包的 `make_forest_plot` / `make_heatmap` 等辅助函数会顺手设图内标题，
  而论文的 `\\caption` 已经负责题注，图内再加一遍会重复挤版面（skill 图规则第 6 条）。

策略（与队友一致）
  · `Axes.set_title`：标签以"图"开头才清空 —— 保留 `(a)` / `(b)` 面板标签与
    其他业务标题；
  · `Figure.suptitle`：一律清空 —— suptitle 是"图 N …"总标题的专用位置，
    论文模板里不应出现。

用法
  在 `figures.py` 顶部 `import _notitle`（必须早于任何 fig 创建），副作用生效。
"""
from __future__ import annotations

import matplotlib.axes as maxes
import matplotlib.figure as mfig

_orig_set_title = maxes.Axes.set_title
_orig_suptitle = mfig.Figure.suptitle


def _blank_title(self, label=None, *a, **k):
    """清空以"图"开头的标题；其余原样透传（保留 (a)(b) 面板标签）。"""
    txt = '' if (label is None or str(label).strip().startswith('图')) else label
    return _orig_set_title(self, txt, *a, **k)


def _blank_suptitle(self, *a, **k):
    """suptitle 一律置空。"""
    return _orig_suptitle(self, '', **k)


maxes.Axes.set_title = _blank_title
mfig.Figure.suptitle = _blank_suptitle
