# MathorCup 大数据竞赛 LaTeX 论文模板

对齐官方 Word 模板 `2026年MathorCup数学应用挑战赛—大数据竞赛论文模板.docx`：
A4、上下 2.0cm / 左右 2.5cm、行网格 15.6 磅；首页各元素坐标经 PDF 实测校准，与 Word 渲染结果偏差 ≤0.1 磅。

## 编译

```bash
# 必须用 TeX Live 2026（MiKTeX 23.4 读 TL2026 生成的 .toc 会报 \UseHookWithArguments 未定义）
D:/textline/texlive/2026/bin/windows/xelatex.exe main.tex
D:/textline/texlive/2026/bin/windows/xelatex.exe main.tex
```

跑两遍的原因：第一遍写 `main.toc`（目录）与 `main.aux`（页码 / `LastPage`），第二遍才读回来。
若换了引擎或从别处拷来工程，先删掉 `main.aux main.toc main.out` 再编译。
最终输出 `main.pdf`。

## 目录结构

```
main.tex                  导言区 + 首页/目录页排版 + \input 各章
references.tex            参考文献（thebibliography）
figures/                  插图放这里，正文写 \includegraphics{figures/xxx}
sections/
  1_问题重述.tex          一、
  2_问题分析.tex          二、
  3_模型假设.tex          三、
  4_符号说明.tex          四、
  5_数据预处理.tex        五、  （含插图与三线表的注释示例）
  6_问题一.tex            六、
  7_问题二.tex            七、
  8_问题三.tex            八、  （含 \subsubsection 三级标题示例）
  9_模型评价.tex          九、
  A_附录代码.tex          附录正文（lstlisting 代码清单）
```

模板骨架只含占位符，**不含任何具体数据路径或数值**，按需替换即可。

## 版式约定

| 层级 | 写法 | 格式 |
|---|---|---|
| 一级 | `\section{...}` | 居中 黑体加粗 14pt，编号「一、」 |
| 二级 | `\subsection{...}` | 左对齐 黑体加粗 12pt，编号「1.1」 |
| 三级 | `\subsubsection{...}` | 左对齐 黑体加粗 12pt，编号「1.1.1」 |
| 正文 | — | 宋体 12pt / 行距 15.6pt / 首行缩进 2em / 两端对齐 |

- 目录收录到三级；一级显示为「一、问题重述」，二级「1.1 …」，三级「1.1.1 …」；参考文献与附录在目录里只有一条，不带子级。
- 页码：首页与目录页不编号；正文从第 1 页起，页脚居中「第 X 页 共 Y 页」（9pt Times New Roman）。
- 插图 / 表格标题由 `caption` 宏包生成，前缀分别为「图」「表」，字号 `\small`。
- 代码用 `lstlisting`，默认 Python 高亮、行号在左。

## 首页填写

首页由 `main.tex` 里的 `\frontpage` 宏生成，需要改的只有三处文本：

- 队伍编号 → `MCB260XXXX`（表格右上格）
- 赛道 → `（A/B）`（表格右下格）
- 论文题目 / 摘要正文 / 关键词 → 宏内对应位置

改动后若整体高度变化，`\frontpage` 末尾的 16 行空网格（`\count255` 循环）负责把「关键词」压到固定位置，一般无需调整。
