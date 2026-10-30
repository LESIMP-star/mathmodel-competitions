# -*- coding: utf-8 -*-
"""解压实测两个 zip：目录完整、selftest 通过、论文可编译。"""
import os
import shutil
import subprocess
import sys
import zipfile

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.getcwd()
DIST = os.path.join(ROOT, 'dist')
VER = os.path.join(DIST, '_verify2')
TEXBIN = '/d/textline/texlive/2026/bin/windows'
PY = sys.executable

if os.path.isdir(VER):
    def _f(func, path, exc):
        os.chmod(path, 0o666)
        func(path)
    shutil.rmtree(VER, onexc=_f)
os.makedirs(VER)

print('=' * 60)
for name in ('MathorCup2026A_支撑材料.zip', '交付包_20261030.zip'):
    p = os.path.join(DIST, name)
    with zipfile.ZipFile(p) as z:
        z.extractall(VER)
    print(f'解压 {name}  {os.path.getsize(p)/1e6:.1f} MB')

SUP = os.path.join(VER, 'MathorCup2026A_支撑材料')
PKG = os.path.join(VER, '交付包_20261030')

print('\n【1】目录结构')
for d, want in ((SUP, ['code', 'results', 'figures', '附件', '论文', 'README.md']),
                (PKG, ['00_先看这里.md', '01_论文源码', '02_支撑材料',
                       '03_修复说明', '04_核查回应', '05_工具'])):
    have = os.listdir(d)
    miss = [w for w in want if w not in have]
    print(f'  {os.path.basename(d)}: {"OK" if not miss else "缺 " + str(miss)}')

print('\n【2】支撑材料 selftest')
r = subprocess.run([PY, 'code/selftest.py'], cwd=SUP,
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace')
tail = (r.stdout or '').strip().split('\n')[-2:]
print(f'  exit={r.returncode}  {tail[-1] if tail else ""}')

print('\n【3】交付包内论文编译')
src = os.path.join(PKG, '01_论文源码')
# MSYS 路径对原生 xelatex 无效，必须转成 Windows 风格，否则会回退到 MiKTeX
# 而 MiKTeX 23.4 不认识 TeX Live 2026 写出的 .toc（\UseHookWithArguments 未定义）
env = dict(os.environ)
XEL = r'D:\textline\texlive\2026\bin\windows\xelatex.exe'
env['PATH'] = os.path.dirname(XEL) + os.pathsep + env.get('PATH', '')
for stale in ('main.aux', 'main.toc', 'main.out', 'main.log'):
    p = os.path.join(src, stale)
    if os.path.exists(p):
        os.remove(p)
for i in range(3):
    r = subprocess.run([XEL, '-interaction=nonstopmode', 'main.tex'],
                       cwd=src, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
    errs = (r.stdout or '').count('\n! ')
    print(f'  pass {i+1}: exit={r.returncode} errors={errs}')
pdf = os.path.join(src, 'main.pdf')
if os.path.exists(pdf):
    print(f'  main.pdf  {os.path.getsize(pdf)/1e6:.2f} MB')

print('\n【4】修复说明是否在包内')
for f in ('修复说明_问题三目标口径.md', '修复说明_问题一预处理.md',
          '修订计划_第三轮.md'):
    print(f'  {"OK " if os.path.exists(os.path.join(PKG,"03_修复说明",f)) else "缺 "} {f}')
for f in ('六条意见判定.md', '问题核对_35条.md'):
    print(f'  {"OK " if os.path.exists(os.path.join(PKG,"04_核查回应",f)) else "缺 "} {f}')

print('\n【5】文件计数')
for d in (SUP, PKG):
    print(f'  {os.path.basename(d)}: {sum(len(fs) for _, _, fs in os.walk(d))} 文件')
