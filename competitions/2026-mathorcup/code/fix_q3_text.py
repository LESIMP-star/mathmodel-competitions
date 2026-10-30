# -*- coding: utf-8 -*-
"""改 Q3 的公式与文字：式(15) f3 定义、目标函数说明、Pareto 点筛选说明。"""
import io
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

P = 'latex模板/sections/8_问题三.tex'
s = io.open(P, encoding='utf-8', newline='').read()
OK, FAIL = [], []


def rep(old, new, tag, count=1):
    global s
    n = s.count(old)
    if n != count:
        FAIL.append((tag, n, count))
        print(f'  ✗ {tag}（{n}/{count}）')
        return
    s = s.replace(old, new)
    OK.append(tag)
    print(f'  ✓ {tag}')


# ══════════ C2：式(15) f3 改为与代码一致
rep(r'''  f_3(x)&=\sum_{j\in\mathcal{J}}\left|x_j-x_j^0\right|,
\end{align}
$f_1$ 为按感官标准差加权的 $L_1$ 偏差，其中 $t_s$ 取目标风格内的中位感官值；$f_2$ 为缺陷物超阈值程度之和，$f_3$ 为干预代价。''',
    r'''  f_3(x)&=\gamma\sum_{j\in\mathcal{J}}z_j+\lambda\sum_{j\in\mathcal{J}}w_j\left|x_j-x_j^0\right|,
  \qquad w_j=\frac{1}{x_j^{\mathrm{ub}}-x_j^{\mathrm{lb}}},
\end{align}
$f_1$ 为按感官标准差加权的 $L_1$ 偏差，其中 $t_s$ 取目标风格内的中位感官值；$f_2$ 为缺陷物超阈值程度之和。

$f_3$ 是干预代价，由两部分组成：$z_j\in\{0,1\}$ 表示第 $j$ 个化合物是否被改动，$\gamma=1.0$ 使其按"改动个数"计；$w_j$ 把改动幅度折算成占可行域宽度的比例，$\lambda=0.1$。这样定义而不用朴素的和 $\sum|x_j-x_j^0|$，是因为决策列并不同域：\texttt{X2.methyltetrahydrofuran.3.one} 与双乙酰是线性浓度列，可行域宽 29.1 与 87.5；其余是 $\log_{10}$ 列，宽约 6.9。若直接相加，等于把浓度差与对数差混进同一个量纲，$f_3$ 会被前两列支配。因此 $f_3$ 的量纲是"改动个数 + 可行域比例"，不是浓度。''',
    'C2 式(15) f3 定义')

# ══════════ C4：目标函数说明（承认 f1 与 f3 同作代价、f2 作约束）
rep(r'''三目标不可加权求和，因为 $f_1$、$f_2$、$f_3$ 的物理含义完全不同。本文用 $\varepsilon$-约束法：先分别解三个单目标得到支付表，再在 $f_2$、$f_3$ 的取值区间内取 $20\times15=300$ 个网格点，逐点求
\begin{equation}
  \min\ f_1(x)\quad \text{s.t.}\quad f_2(x)\le\varepsilon_2,\ f_3(x)\le\varepsilon_3,
\end{equation}
并加增广项剔除弱 Pareto 点。300 个网格点中 280 个可行，且这 280 点全部非支配，说明前沿的形状完全由目标之间的权衡决定，不是被可行性边界截断。''',
    r'''三个目标不能简单合并成一个标量，但性质不同，处理方式也应不同。$f_2$ 是约束性质的量——缺陷物超标属于"不允许"，给它加权等于允许用感官收益换缺陷，物理上讲不通，因此严格作 $\varepsilon$-约束。$f_1$ 与 $f_3$ 都是代价——一个是感官偏离，一个是干预量，二者的权衡正是本问要回答的，因此按权重 1 的标量化和处理，再用 $\varepsilon$-约束扫描前沿。

具体做法：先分别解三个单目标得到支付表，再在 $f_2$、$f_3$ 的取值区间内取 $20\times15=300$ 个网格点，逐点求
\begin{equation}
  \min\ f_1(x)+\lambda f_3(x)\quad \text{s.t.}\quad f_2(x)\le\varepsilon_2,\ f_3(x)\le\varepsilon_3,
\end{equation}
并加增广项剔除弱 Pareto 点。300 个网格点全部可行且全部非支配，去重后保留 7 个互不支配的 Pareto 点。

\textbf{报告点的选取}\quad 280 个可行点（修复约束口径前）与 300 个可行点（修复后）都全部非支配，说明 $20\times15$ 的网格相对于真实前沿仍然偏粗，5--7 个点只是按 $f_3$ 分层取的代表点，不是前沿的全部。本文按 $f_3$ 从小到大等间隔取代表点，每个点标注其改动列数，读者可以据此判断"多改一个化合物换多少感官收益"。''',
    'C4 目标函数与筛选说明')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print(f'\n成功 {len(OK)}，失败 {len(FAIL)}')
for t, n, c in FAIL:
    print(f'  {t}（{n}/{c}）')
