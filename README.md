# 数学建模比赛工作区

队伍协作仓库，用于存放数学建模类竞赛的代码、论文源文件与资料。私有仓库，仅受邀队员可见。

## 目录结构

```
.
├── competitions/          各次比赛，一次一个目录
│   └── <year>-<比赛名>/    如 2026-mathorcup
│       ├── code/          求解脚本
│       ├── paper/         LaTeX 论文源文件
│       ├── results/       结果文件（CSV / JSON），论文数字的唯一来源
│       ├── figures/       插图
│       └── README.md      本次比赛的赛题、分工、进度
├── shared/                跨比赛复用的东西
│   ├── latex-template/    论文 LaTeX 模板
│   ├── plots/             通用绘图脚本与样式
│   └── utils/             数据清洗、检验等公共函数
├── docs/                  协作规范、赛题合集、经验总结
└── .gitignore
```

## 协作方式

分支模型很简单，够用就好：

- `main` 保持随时可编译、数字可核对
- 每人开自己的分支做，命名 `feat/姓名-内容` 或 `fix/姓名-内容`
- 完成后提 Pull Request 合回 `main`，至少一个人看过再合
- 不要直接往 `main` push

提交信息写清楚做了什么，例如：

```
q1: 改用嵌套交叉验证，R² 中位 0.1466 -> 0.1471
paper: 修正第 6 章残差诊断的表述
```

## 两条硬规矩

**结果文件是论文数字的唯一来源。** 论文里出现的每个数字，都要能在 `results/` 下找到对应的 CSV 或 JSON。不要手抄数字到正文里，改动结果就重跑脚本。

**赛题原始数据不进仓库。** 附件数据几百 MB，且属于赛事方，放本地或网盘。仓库里只放代码、结果、论文和文档。

## 环境

```bash
conda create -n mm python=3.11
conda activate mm
pip install numpy pandas scipy scikit-learn lightgbm matplotlib openpyxl
```

用 Gurobi 的话另装 `gurobipy` 并配好 license。LaTeX 用 TeX Live 2026，编译 `xelatex` 跑两遍。

## 队员

| GitHub | 角色 |
|---|---|
| @LESIMP-star | 建模 |
| 待邀请 | 编程 |
| 待邀请 | 论文 |
