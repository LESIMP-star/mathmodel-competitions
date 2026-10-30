# -*- coding: utf-8 -*-
"""全链路口径一致性审计：代码 / 结果 / 图 / 论文 / 支撑材料 / 文档 六处对齐。

检查项分三类：
  A. 旧值残留（任何地方出现修复前的数字即为不一致）
  B. 三层代码一致（repo code / 支撑材料 code / 交付包 code 的 md5 相同）
  C. 结果 → 论文数字（关键指标在 results 与 tex 中同值）
"""
import hashlib
import io
import json
import os
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.getcwd()
SUP = os.path.join(ROOT, 'dist', 'MathorCup2026A_支撑材料')
PKG = os.path.join(ROOT, 'dist', '交付包_20261030')
BAD, WARN, OK = [], [], []


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ══════════════════════════════════════════════════
print('【A】旧值残留扫描')
# 修复前的数字 → 现在应该是多少
STALE = {
    '23.8519': 'P1 f1（旧）',
    '688.54': '超体积（旧）',
    '389.42': '超体积增益（旧）',
    '13.3438': 'γ 摆幅（旧）',
    '9.2310': 'PLS 摆幅（旧）',
    '5.9057': 'ε3 摆幅（旧）',
    '4.5471': 'λ 摆幅（旧）',
    '13.7852': '灵敏度基准（旧）',
    '91.30': '支配比例（旧）',
    '105 个': 'NSGA 被支配数（旧）',
    '0.1471': 'R² 中位（旧）',
    '0.2219': 'R² 均值（旧）',
    '0.3433': 'QWK（旧）',
    '62.4': '压 0 档（旧）',
    '未感知': '旧的标签口径',
    '分组置换': '旧的方法名',
    '250×226': '旧的维数写法',
    '226 化合物': '旧的化合物数',
}
TARGETS = []
for base, _, fs in os.walk(os.path.join(ROOT, 'latex模板')):
    if '_backup_tex' in base or 'sections.bak' in base:
        continue
    TARGETS += [os.path.join(base, f) for f in fs
                if f.endswith('.tex') or f.endswith('.md')]
TARGETS += [os.path.join(ROOT, 'docs', f) for f in os.listdir(os.path.join(ROOT, 'docs'))
            if f.endswith('.md') or f.endswith('.csv')]
for f in ('README.md', '整理说明.md', '交接文档.md'):
    p = os.path.join(ROOT, f)
    if os.path.exists(p):
        TARGETS.append(p)
for base, _, fs in os.walk(SUP):
    TARGETS += [os.path.join(base, f) for f in fs if f.endswith('.md')]
TARGETS += [os.path.join(ROOT, 'code', f) for f in os.listdir(os.path.join(ROOT, 'code'))
            if f.endswith('.py')]

hits = {}
for p in TARGETS:
    try:
        s = io.open(p, encoding='utf-8', errors='ignore').read()
    except OSError:
        continue
    rel = os.path.relpath(p, ROOT)
    for k, why in STALE.items():
        if k in s:
            hits.setdefault(k, []).append((rel, why))

# 允许的例外：明确记录"修复前"的对照文档
ALLOW = ('修复说明_问题三目标口径.md', '论文核对清单', '修复说明_问题一预处理.md',
         '六条意见判定.md', '问题核对_35条.md', '修订计划_第三轮.md',
         '问题诊断报告.md', 'diff_fix.py', 'make_checklist.py',
         'fix_', 'dump_q3_truth.py', 'audit_paper.py', 'selftest.py',
         'verify_delivery.py', 'rebuild_delivery.py', 'audit_consistency.py',
         'sync_q3_numbers.py', '整理说明.md', '问题一_内层交叉验证预处理核查.md',
         '_archive', '_bak_placeholder', 'push_repo.py', '赛题要求核对表.md')
for k, lst in hits.items():
    real = [(r, w) for r, w in lst if not any(a in r for a in ALLOW)]
    if real:
        BAD.append(f'旧值 {k}（{lst[0][1]}）出现在：' +
                   '、'.join(sorted({r for r, _ in real}))[:160])
    else:
        WARN.append(f'旧值 {k} 仅见于对照/工具文档（正常）')

print(f'  命中 {len(hits)} 个旧值模式，其中 {len(BAD)} 个是真残留')

# ══════════════════════════════════════════════════
print('\n【B】三层代码一致（repo / 支撑材料 / 交付包）')
CODEF = ['q0_relations.py', 'q1.py', 'q1_helpers.py', 'q1_grades.py',
         'q1_diagnostics.py', 'q1_ablation_231.py', 'q2.py', 'q2_graph.py',
         'q2_consensus.py', 'q2_confident.py', 'q3.py', 'q3_transfer.py',
         'robustness_q3.py', 'nsga2.py', 'selftest.py', 'figures.py']
mism = 0
for f in CODEF:
    a = os.path.join(ROOT, 'code', f)
    b = os.path.join(SUP, 'code', f) if f != 'figures.py' else \
        os.path.join(SUP, 'code', '绘图', f)
    c = os.path.join(PKG, '02_支撑材料', 'code', f) if f != 'figures.py' else \
        os.path.join(PKG, '02_支撑材料', 'code', '绘图', f)
    if not (os.path.exists(a) and os.path.exists(b)):
        BAD.append(f'{f} 在支撑材料中缺失')
        mism += 1
        continue
    if md5(a) != md5(b):
        BAD.append(f'{f} 与支撑材料不一致')
        mism += 1
    elif os.path.exists(c) and md5(a) != md5(c):
        BAD.append(f'{f} 与交付包内不一致')
        mism += 1
print(f'  {len(CODEF)} 个脚本，{mism} 个不一致')

# 结果文件
res_mism = 0
for f in os.listdir(os.path.join(ROOT, 'results')):
    p = os.path.join(ROOT, 'results', f)
    if not os.path.isfile(p):
        continue
    q = os.path.join(SUP, 'results', f)
    if not os.path.exists(q):
        BAD.append(f'results/{f} 未进支撑材料')
        res_mism += 1
    elif md5(p) != md5(q):
        BAD.append(f'results/{f} 内容不一致')
        res_mism += 1
print(f'  results/ {res_mism} 个不一致')

# 图
fig_mism = 0
fdir = os.path.join(ROOT, 'latex模板', 'figures')
for f in os.listdir(fdir):
    if not f.endswith(('.png', '.svg')):
        continue
    q = os.path.join(SUP, 'figures', f)
    if not os.path.exists(q):
        BAD.append(f'figures/{f} 未进支撑材料')
        fig_mism += 1
    elif md5(os.path.join(fdir, f)) != md5(q):
        BAD.append(f'figures/{f} 内容不一致')
        fig_mism += 1
print(f'  figures/ {fig_mism} 个不一致')

# ══════════════════════════════════════════════════
print('\n【C】results → 论文 数字对齐')


def tex_all():
    out = []
    for base, _, fs in os.walk(os.path.join(ROOT, 'latex模板')):
        if '_backup_tex' in base or 'sections.bak' in base:
            continue
        for f in fs:
            if f.endswith('.tex'):
                out.append(io.open(os.path.join(base, f), encoding='utf-8',
                                   errors='ignore').read())
    return '\n'.join(out)


T = tex_all()
par = pd.read_csv('results/q3_pareto.csv')
log = json.load(io.open('results/q3_run_log.json', encoding='utf-8'))
sm = json.load(io.open('results/q3_sensitivity_summary.json', encoding='utf-8'))
sp = pd.read_csv('results/q3_sensitivity_span.csv').set_index('param')
q1 = json.load(io.open('results/q1_run_log.json', encoding='utf-8'))

CHECKS = [
    ('Q3 P1 f1 20.2063', f'{par.f1.min():.4f}', '20.2063'),
    ('Q3 像素点数 7', '7 个 Pareto 点', '7 个 Pareto 点'),
    ('γ 摆幅 21.5730', f'{sp.loc["gamma","span"]:.4f}', '21.5730'),
    ('ε3 摆幅 8.8648', f'{sp.loc["eps3","span"]:.4f}', '8.8648'),
    ('PLS 摆幅 5.0949', f'{sp.loc["pls_k","span"]:.4f}', '5.0949'),
    ('λ 摆幅 2.3745', f'{sp.loc["lambda","span"]:.4f}', '2.3745'),
    ('灵敏度基准 20.2063', f'{sm["base_f1"]:.4f}', '20.2063'),
    ('超体积 757.78', f'{log["compare"]["hv_exact"]:.2f}', '757.78'),
    ('支配 92.17%', f'{100*log["compare"]["exact_dominates_heur"]:.2f}', '92.17'),
]
for name, src_val, tex_str in CHECKS:
    in_tex = tex_str in T
    agree = True
    try:
        agree = abs(float(src_val) - float(tex_str)) < 5e-4 or \
            f'{float(src_val):.4f}' == tex_str
    except ValueError:
        pass
    if not in_tex:
        BAD.append(f'{name}：{tex_str} 未出现在 tex')
    elif not agree:
        BAD.append(f'{name}：results={src_val} tex={tex_str}')
    else:
        OK.append(name)
print(f'  {len(OK)}/{len(CHECKS)} 项对齐')

# ══════════════════════════════════════════════════
print('\n' + '=' * 62)
print(f'通过 {len(OK)}   不一致 {len(BAD)}   提示 {len(WARN)}')
if BAD:
    print('\n--- 不一致 ---')
    for b in BAD:
        print(f'  ✗ {b}')
if WARN:
    print('\n--- 提示（不算错）---')
    for w in WARN[:6]:
        print(f'  · {w}')
sys.exit(0 if not BAD else 1)
