# -*- coding: utf-8 -*-
"""把 code/tools/*.py 的 ROOT 定位改成「向上找到含 results/ 的目录」，这样放在 code/ 或
code/tools/ 都能跑。同时同步到仓库暂存区。"""
import io
import os
import re
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'code', 'tools')
STAGE_TOOLS = r'E:\hermes\.hermes\cache\scratch\repo_push\competitions\2026-mathorcup\code\tools'

# 要替换的 ROOT 定义形式
PATTERNS = [
    (re.compile(r"^ROOT = os\.path\.dirname\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\)\)$", re.M),
     "_ROOT0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
     "ROOT = next((p for p in [_ROOT0, os.path.dirname(_ROOT0)]\n"
     "             if os.path.isdir(os.path.join(p, 'results'))), _ROOT0)  "
     "# 向上找含 results/ 的目录"),
    (re.compile(r"^PROJ = Path\(__file__\)\.resolve\(\)\.parent\.parent$", re.M),
     "_P0 = Path(__file__).resolve().parent\n"
     "PROJ = next((p for p in [_P0.parent, _P0.parent.parent]\n"
     "             if (p / 'results').is_dir()), _P0.parent)"),
]

changed = []
for d in (TOOLS, STAGE_TOOLS):
    if not os.path.isdir(d):
        continue
    for f in sorted(os.listdir(d)):
        if not f.endswith('.py'):
            continue
        p = os.path.join(d, f)
        s = io.open(p, encoding='utf-8', newline='').read()
        orig = s
        for pat, new in PATTERNS:
            s = pat.sub(new, s, count=1)
        if s != orig:
            io.open(p, 'w', encoding='utf-8', newline='').write(s)
            changed.append(os.path.join(os.path.basename(d), f))

print('已改 ROOT 定位：')
for c in sorted(set(changed)):
    print('  ' + c)

# 列出仍未适配的文件
print('\n检查 tools/ 里所有脚本的 ROOT 定义：')
for f in sorted(os.listdir(TOOLS)):
    if not f.endswith('.py'):
        continue
    s = io.open(os.path.join(TOOLS, f), encoding='utf-8').read()
    m = re.search(r'^(ROOT|PROJ)\s*=\s*.+$', s, re.M)
    print(f'  {f:28s} {m.group(0)[:72] if m else "（无 ROOT）"}')
