# -*- coding: utf-8 -*-
"""figures.py 兼容两种论文目录名：latex模板/（本地）与 paper/（仓库）。"""
import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = [os.path.join(ROOT, 'code', 'figures.py'),
         r'E:\hermes\.hermes\cache\scratch\repo_push\competitions\2026-mathorcup\code\figures.py']

OLD = """PROJ = _HERE.parent
RES = PROJ / 'results'
OUT = PROJ / 'latex模板' / 'figures'"""

NEW = """_P0 = _HERE.parent
# 向上找含 results/ 的目录（本地在 code/ 下一级，仓库可能在 code/ 下一级）
PROJ = next((p for p in [_P0, _P0.parent] if (p / 'results').is_dir()), _P0)
RES = PROJ / 'results'
# 论文插图目录两种命名都认：本地 `latex模板/figures`，仓库 `paper/figures`
OUT = next((p for p in [PROJ / 'latex模板' / 'figures', PROJ / 'paper' / 'figures']
            if p.parent.is_dir()), PROJ / 'latex模板' / 'figures')"""

for f in FILES:
    if not os.path.exists(f):
        continue
    s = io.open(f, encoding='utf-8', newline='').read()
    if OLD not in s:
        print(f'  ✗ {f}: 未找到锚点')
        continue
    s = s.replace(OLD, NEW)
    io.open(f, 'w', encoding='utf-8', newline='').write(s)
    print(f'  ✓ {os.path.basename(os.path.dirname(f))}/figures.py')
