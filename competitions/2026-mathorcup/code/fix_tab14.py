# -*- coding: utf-8 -*-
"""B9：表 14 加「是否超阈值」列，并改写表下说明。"""
import io
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

P = 'latex模板/sections/8_问题三.tex'
s = io.open(P, encoding='utf-8', newline='').read()

OLD = r'''\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llccc@{}}
\toprule
\textbf{缺陷物} & \textbf{阈值来源} & \textbf{迁移前} & \textbf{迁移后} & \textbf{是否恶化} \\
\midrule
DMS & 附件8，17.25 $\mu$g/L & 1.1793 & 1.1793 & 否 \\
Diacetyl & 附件8，0.299 mg/L & 0.0570 & 0.0570 & 否 \\
4VG & 附件8，0.206 mg/L & $-2.0132$ & $-2.0132$ & 否 \\
trans-2-nonenal & 文献，0.11 $\mu$g/L & 0.002012 & 0.002012 & 否 \\
Stale hops & 代理预测（感官项） & 0.2528 & 0.0453 & 否（改善） \\
\bottomrule
\end{tabular*}'''

NEW = r'''\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llcccc@{}}
\toprule
\textbf{缺陷物} & \textbf{阈值来源} & \textbf{迁移前} & \textbf{迁移后} & \textbf{是否恶化} & \textbf{是否超阈值} \\
\midrule
DMS & 附件8，17.25 $\mu$g/L & 1.1793 & 1.1793 & 否 & 否 \\
Diacetyl & 附件8，0.299 mg/L & 0.0570 & 0.0570 & 否 & 否 \\
4VG & 附件8，0.206 mg/L & $-2.0132$ & $-2.0132$ & 否 & 否 \\
trans-2-nonenal & 文献，0.11 $\mu$g/L & 0.002012 & 0.002012 & 否 & \textbf{是} \\
Stale hops & 代理预测（感官项） & 0.2528 & 0.0453 & 否（改善） & 不适用 \\
\bottomrule
\end{tabular*}'''

OLD_NOTE = ('五类缺陷物全部满足不恶化：DMS、双乙酰、4VG 在迁移前就已低于或等于阈值，'
            'trans-2-壬烯醛保持不变，Stale hops 的代理预测从 0.2528 降到 0.0453，'
            '是唯一明显改善的一项。这里要指出一处数据本身的限制：按附件8 标注的 mg/L 单位换算，'
            '文献阈值 0.11 $\\mu$g/L 折合 $1.1\\times10^{-4}$ mg/L，'
            '低于该列在样本中的 1\\% 分位($1.61\\times10^{-4}$)，即数据集内没有任何样本满足该阈值。'
            '这种情况下“不超标”不可达，本文只保证“不恶化”，并如实记录这一单位上的存疑。')

NEW_NOTE = r'''五类缺陷物全部满足不恶化，但"不恶化"与"不超标"是两件事，表中分两列报告。DMS、双乙酰、4VG 在迁移前就已低于阈值，迁移后不变，因此既未恶化也未超标。Stale hops 是感官项的代理预测，从 0.2528 降到 0.0453，是唯一明显改善的一项，不适用阈值判断。

trans-2-壬烯醛是唯一的例外：迁移前后都是 0.002012，$\\Delta=0$ 说明未恶化，但该值远高于文献阈值 0.11 $\\mu$g/L（折合 $1.1\\times10^{-4}$ mg/L），因此\textbf{超标}。这不是优化失败，而是数据本身的限制——该阈值低于此列在样本中的 1\\% 分位（$1.61\\times10^{-4}$），即数据集内没有任何样本能满足它。这种情况下"不超标"不可达，本文只保证"不恶化"，并把这一事实在表中直接标出，而不是用"否"字掩盖。'''

ok = 0
for old, new, tag in ((OLD, NEW, '表14 加超阈值列'),
                      (OLD_NOTE, NEW_NOTE, '表14 说明改写')):
    n = s.count(old)
    if n == 1:
        s = s.replace(old, new)
        ok += 1
        print(f'  ✓ {tag}')
    else:
        print(f'  ✗ {tag}（{n} 次）')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print(f'\n成功 {ok}/2')
