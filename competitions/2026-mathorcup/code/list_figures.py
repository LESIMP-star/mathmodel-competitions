# -*- coding: utf-8 -*-
"""列出论文里每个图的文件名、所在章节、图注首句，供写队友任务用。"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FIG = re.compile(r'includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}')
CAP = re.compile(r'\\caption\{([^}]{0,200})')

for f in sorted(os.listdir('latex模板/sections')):
    if not f.endswith('.tex') or f.startswith('_'):
        continue
    s = io.open(os.path.join('latex模板/sections', f),
                encoding='utf-8', errors='ignore').read()
    figs = FIG.findall(s)
    if not figs:
        continue
    print(f'\n=== {f} ===')
    for name in figs:
        # 找该图之后的第一个 caption
        i = s.find(name)
        m = CAP.search(s, i)
        cap = m.group(1)[:90] if m else '(无)'
        print(f'  {name:28s} {cap}')
