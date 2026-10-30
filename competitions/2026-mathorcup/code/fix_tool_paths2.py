# -*- coding: utf-8 -*-
"""让 tools 脚本兼容两种论文目录命名：latex模板/（本地）与 paper/（仓库）。"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = [os.path.join(ROOT, 'code', 'tools'),
           r'E:\hermes\.hermes\cache\scratch\repo_push\competitions\2026-mathorcup\code\tools']

SECTIONS_HELPER = '''_ROOT0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = next((p for p in [_ROOT0, os.path.dirname(_ROOT0)]
             if os.path.isdir(os.path.join(p, 'results'))), _ROOT0)  # 向上找含 results/ 的目录
# 论文目录两种命名都认：本地 `latex模板/`，仓库 `paper/`
LATEX = next((os.path.join(ROOT, d) for d in ('latex模板', 'paper')
              if os.path.isdir(os.path.join(ROOT, d, 'sections'))),
             os.path.join(ROOT, 'latex模板'))
SEC = os.path.join(LATEX, 'sections')'''

PATCH = {
    'audit_paper.py': [
        # 把 SEC 定义换成带 LATEX 的版本
        (re.compile(r"^SEC = os\.path\.join\(ROOT, 'latex模板', 'sections'\)$", re.M),
         SECTIONS_HELPER),
        (re.compile(r"os\.path\.join\(ROOT, 'latex模板', 'references\.tex'\)"),
         "os.path.join(LATEX, 'references.tex')"),
    ],
    'build_paper.py': [
        (re.compile(r"^LATEX = os\.path\.join\(ROOT, 'latex模板'\)$", re.M),
         "LATEX = next((os.path.join(ROOT, d) for d in ('latex模板', 'paper')\n"
         "              if os.path.isdir(os.path.join(ROOT, d, 'sections'))),\n"
         "             os.path.join(ROOT, 'latex模板'))"),
    ],
    'make_indexes.py': [
        (re.compile(r"^PROJ = Path\(__file__\)\.resolve\(\)\.parent$", re.M),
         "_P0 = Path(__file__).resolve().parent\n"
         "PROJ = next((p for p in [_P0.parent, _P0.parent.parent]\n"
         "             if (p / 'results').is_dir()), _P0.parent)"),
        (re.compile(r"PROJ / 'latex模板' / 'figures'"),
         "FIGDIR"),
        (re.compile(r"'latex模板/figures/(fig_\{stem\}\.(?:png|svg))'"),
         "'paper/figures/\\\\1'"),
    ],
}

for d in TARGETS:
    if not os.path.isdir(d):
        continue
    for f, pats in PATCH.items():
        p = os.path.join(d, f)
        if not os.path.exists(p):
            continue
        s = io.open(p, encoding='utf-8', newline='').read()
        orig = s
        for pat, new in pats:
            s = pat.sub(new, s)
        if s != orig:
            io.open(p, 'w', encoding='utf-8', newline='').write(s)
            print(f'  ✓ {os.path.basename(d)}/{f}')

# make_indexes 的 FIGDIR 必须先定义
for d in TARGETS:
    p = os.path.join(d, 'make_indexes.py')
    if not os.path.exists(p):
        continue
    s = io.open(p, encoding='utf-8', newline='').read()
    if 'FIGDIR =' not in s and 'FIGDIR,' in s:
        print('  ! make_indexes.py 用了 FIGDIR 但没定义，需手工确认')
    m = re.search(r'^(PROJ = .+)$', s, re.M)
    print(f'  make_indexes PROJ: {m.group(0)[:60] if m else "?"}')
