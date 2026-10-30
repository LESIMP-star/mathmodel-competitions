# -*- coding: utf-8 -*-
"""从修复包 zip 取回 修复说明_问题一预处理.md 与两份核对清单。"""
import io
import os
import shutil
import sys
import zipfile

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.getcwd()
Z = os.path.join(ROOT, 'dist', '修复包_问题一预处理_20261030.zip')
OUT = os.path.join(ROOT, 'docs')
os.makedirs(OUT, exist_ok=True)

z = zipfile.ZipFile(Z)
names = z.namelist()
print(f'zip 内 {len(names)} 项')

# zip 里的中文名可能被 UTF-8 误解码，按尾部特征匹配
def find(suffix):
    for n in names:
        if n.endswith(suffix):
            return n
    return None

got = []
for suffix, target in (('README.md', '修复说明_问题一预处理.md'),
                       ('_19_项.csv', '论文核对清单_审计19项.csv'),
                       ('R2.csv', '论文核对清单_逐维R2.csv')):
    n = find(suffix)
    if n is None:
        print(f'  ! 未找到 {suffix}')
        continue
    data = z.read(n)
    p = os.path.join(OUT, target)
    with open(p, 'wb') as f:
        f.write(data)
    got.append((target, len(data)))

for t, n in got:
    print(f'  ✓ {t}  {n} bytes')

# 从微信目录补两份核查原件
WX = ('E:/weixin contact/xwechat_files/wxid_345m6jh5u2f722_2f30/'
      'msg/file/2026-10')
for f in ('问题一_内层交叉验证预处理核查.md', '问题二_FDR统计解释核查.md',
          '论文第二轮_问题诊断报告.md'):
    p = os.path.join(WX, f)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(OUT, f))
        print(f'  ✓ 微信 → docs/{f}')
    else:
        print(f'  ! 缺 {f}')
