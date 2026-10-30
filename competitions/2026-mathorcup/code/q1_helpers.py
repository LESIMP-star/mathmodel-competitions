# -*- coding: utf-8 -*-
"""q1_helpers.py — Q3 需要的"树模型代理对照"小工具

为什么单独成文件
  Q3 的线性代理需要一个**非线性参照**来测误差上界。这个参照就用 Q1 的主模型族
  （LightGBM），但它只在 Q3 里用、不重复 Q1 的嵌套 CV 逻辑，所以抽成轻量模块，
  避免 `import q1` 时连带跑 Q1 的 50 维 × 5 折搜索。

本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：Hermes Agent（Nous Research），底层模型 deepseek-v4-flash，
# 开发机构：Nous Research（工具）/ 深度求索 DeepSeek（模型），使用日期：2026-10-26
"""
from __future__ import annotations

import numpy as np


def fit_tree_for_surrogate(X, Y, seed=2026):
    """逐感官维拟合 LightGBM（与 Q1 主模型同超参）。返回模型列表。"""
    from lightgbm import LGBMRegressor
    models = []
    for s in range(Y.shape[1]):
        y = Y[:, s]
        if not np.isfinite(y).all() or np.std(y) < 1e-12:
            models.append(None)
            continue
        m = LGBMRegressor(n_estimators=120, num_leaves=7, min_child_samples=10,
                          learning_rate=0.08, subsample=0.85, colsample_bytree=0.5,
                          reg_lambda=1.0, random_state=seed, n_jobs=2, verbose=-1)
        m.fit(X, y)
        models.append(m)
    return models


def predict_tree(models, T):
    """对 (m, p) 矩阵批量预测 → (m, n_s)。"""
    T = np.atleast_2d(np.asarray(T, dtype=float))
    out = np.zeros((T.shape[0], len(models)))
    for s, m in enumerate(models):
        out[:, s] = 0.0 if m is None else m.predict(T)
    return out
