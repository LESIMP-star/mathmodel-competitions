# -*- coding: utf-8 -*-
"""构建论文：重建 A.4 核心实现 → 三遍 xelatex → 复制 PDF 到支撑材料"""
import io
import os
import re
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

_ROOT0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = next((p for p in [_ROOT0, os.path.dirname(_ROOT0)]
             if os.path.isdir(os.path.join(p, 'results'))), _ROOT0)  # 向上找含 results/ 的目录
LATEX = next((os.path.join(ROOT, d) for d in ('latex模板', 'paper')
              if os.path.isdir(os.path.join(ROOT, d, 'sections'))),
             os.path.join(ROOT, 'latex模板'))
SEC = os.path.join(LATEX, 'sections')
XEL = r'D:\textline\texlive\2026\bin\windows\xelatex.exe'

# ── 1. 重建 A.4（8 段核心实现）
# 公式编号按 tex 顺序实测：5 章(1)、6 章(2-6)、7 章(7-11)、8 章(12-17)
PIECES = [
    ('q1.py', ['nested_cv_one'], '嵌套交叉验证的单维流程', '式 (5)、第六章 6.3 节'),
    ('q1.py', ['_fit_predict_hurdle'], 'hurdle 两部模型的两层组合', '式 (4)'),
    ('q1_grades.py', ['quantile_to_grade', 'qwk'],
     '0--6 分位映射与加权 kappa', '式 (6)、表 5'),
    ('q2.py', ['permutation_importance'], '逐列置换重要性', '式 (7)--(8)'),
    ('q2.py', ['fdr_threshold'], '入选频率阈值的反解', '式 (9)'),
    ('q2_graph.py', ['spectral_embed'], '两种拉普拉斯下的谱嵌入', '第七章 7.1 节'),
    ('q3.py', ['build_arrays'], 'MILP 的矩阵装配', '式 (15)--(17)'),
    ('q3.py', ['fit_pls_surrogate'], '偏最小二乘代理', '式 (14)'),
]


def extract(path, names):
    src = io.open(path, encoding='utf-8', errors='replace',
                  newline='').read().replace('\r\n', '\n')
    lines = src.split('\n')
    starts = {}
    for i, ln in enumerate(lines):
        m = re.match(r'^def (\w+)\(', ln)
        if m:
            starts[m.group(1)] = i
    out, used = [], []
    for name in names:
        if name not in starts:
            print(f'   ! {os.path.basename(path)} 无 {name}')
            continue
        i = starts[name]
        j = i + 1
        while j < len(lines) and not re.match(
                r'^(def |# =====|class |if __name__)', lines[j]):
            j += 1
        seg = lines[i:j]
        while seg and not seg[-1].strip():
            seg.pop()
        out.append('\n'.join(seg))
        used.append((i + 1, i + len(seg)))
    return '\n\n'.join(out), used


out = ['%' + '=' * 78,
       '% 附录 A.4 核心实现（完整源码随支撑材料交付）',
       '%' + '=' * 78, '']
total = 0
for k, (f, names, desc, ref) in enumerate(PIECES, 1):
    body, used = extract(os.path.join(ROOT, 'code', f), names)
    if not body:
        continue
    total += body.count('\n') + 1
    rng = '、'.join(f'L{a}--L{b}' for a, b in used)
    ftex = f.replace('_', '\\_')
    out += ['\\subsubsection*{A.4.%d\\quad %s}' % (k, desc), '',
            f'对应{ref}；源码 \\texttt{{code/{ftex}}} 的 {rng}。', '',
            '\\begin{lstlisting}[language=Python]', body,
            '\\end{lstlisting}', '']
io.open(os.path.join(SEC, 'A_附录代码_src.tex'), 'w', encoding='utf-8',
        newline='').write('\n'.join(out))
print(f'✓ A.4 重建：8 段 {total} 行')

# ── 2. 编译
os.chdir(LATEX)
for f in os.listdir('.'):
    if f.startswith('main.') and f.rsplit('.', 1)[-1] in (
            'aux', 'toc', 'out', 'lof', 'lot', 'log'):
        os.remove(f)

env = dict(os.environ)
env['PATH'] = os.path.dirname(XEL) + os.pathsep + env.get('PATH', '')
log = ''
for i in (1, 2, 3):
    r = subprocess.run([XEL, '-interaction=nonstopmode', 'main.tex'],
                       capture_output=True, env=env)
    log = r.stdout.decode('utf-8', 'replace')
    print(f'pass {i}: errors={len(re.findall("^!", log, re.M))}  '
          f'overfull={log.count("Overfull")}')

errs = len(re.findall(r'^!', log, re.M))
m = re.search(r'Output written on main\.pdf \((\d+) pages', log)
print(f'\n最终：{m.group(1) if m else "?"} 页  errors={errs}  '
      f'overfull={log.count("Overfull")}')
if errs:
    for mm in list(re.finditer(r'^!(.*)$', log, re.M))[:8]:
        print('  !', mm.group(1).strip()[:66], '||',
              log[mm.end():mm.end() + 70].replace('\n', ' ').strip()[:70])
if log.count('Overfull'):
    print('--- Overfull ---')
    for mm in list(re.finditer(r'Overfull[^\n]*', log))[:8]:
        print('  ', mm.group(0)[:110])
for mm in list(re.finditer(r"Reference `[^']*' on page \d+ undefined", log))[:5]:
    print('  !', mm.group(0))

io.open(os.path.join(ROOT, 'code', 'build.log'), 'w',
        encoding='utf-8').write(log)

# ── 3. 复制
if os.path.exists('main.pdf'):
    dst = os.path.join(ROOT, '支撑材料', 'main.pdf')
    shutil.copy2('main.pdf', dst)
    print(f'\n✓ 支撑材料/main.pdf ({os.path.getsize(dst)} 字节)')
