# -*- coding: utf-8 -*-
"""把「未感知」全部改成「左尾」口径，避免把 z-score 左尾误读为没尝到。"""
import io
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

C6 = 'latex模板/sections/6_问题一.tex'
MAIN = 'latex模板/main.tex'
OK, FAIL = [], []


def rep(path, old, new, tag):
    s = io.open(path, encoding='utf-8', newline='').read()
    n = s.count(old)
    if n != 1:
        FAIL.append((tag, n))
        print(f'  ✗ {tag}（{n}）')
        return
    io.open(path, 'w', encoding='utf-8', newline='').write(s.replace(old, new))
    OK.append(tag)
    print(f'  ✓ {tag}')


rep(C6, '$\\bar y_s^{\\text{floor}}$ 为未感知样本的强度均值。'
        '此处不用 $\\hat\\pi\\hat\\mu$ 的乘积形式，是因为乘积会把未感知样本的预测强行拉到 0，'
        '而实测中这类样本的强度并不为 0（只是集中在列最小值附近），相乘会系统性低估其强度；'
        '加权混合保留了“未感知时取地板均值”这一物理含义，也让 $\\hat\\pi$ 退化为 0/1 时'
        '连续过渡到单段回归。',
    '$\\bar y_s^{\\text{floor}}$ 为左尾样本（$y\\le y_s^{\\min}+0.15$）的强度均值。'
    '此处不用 $\\hat\\pi\\hat\\mu$ 的乘积形式，是因为乘积会把左尾样本的预测强行拉到 0，'
    '而实测中这类样本的强度并不为 0（只是集中在列最小值附近），相乘会系统性低估其强度；'
    '加权混合保留了“落在左尾时取左尾均值”这一含义，也让 $\\hat\\pi$ 退化为 0/1 时'
    '连续过渡到单段回归。需要说明的是，这里的 $\\hat\\pi$ 是“强度高于左尾窗”的概率，'
    '不是“是否感知到”的概率——附件4 的标签已按品评员做过 z-score，负值代表低于该品评员'
    '的平均，不代表没有尝到（见 5.3 节）。',
    '6.2 两段式公式说明')

rep(C6, '两段式模型只在 9 个未感知样本占比超过 0.30 的感官项上启用',
    '两段式模型只在 9 个左尾占比超过 0.30 的感官项上启用',
    '6.3 两段式启用条件')

rep(C6, '说明起作用的是单调关系而非线性关系：某项“未感知”样本占比越高，模型越难学。',
    '说明起作用的是单调关系而非线性关系：某项的左尾样本占比越高，模型越难学。',
    '6.6 左尾与R2')

rep(C6, '\\caption{地板效应占比与 $R^2$ 的单调关系：未感知样本占比越高，模型越难学}',
    '\\caption{左尾占比与 $R^2$ 的单调关系：左尾样本占比越高，模型越难学}',
    '图注 q1floor')

rep(MAIN, '未感知占比超过 30\\% 的 9 项另加“先判有无、再判强弱”的两段式结构',
    '左尾占比超过 30\\% 的 9 项另加两段式结构（先判断是否落在左尾，再回归强度）',
    '摘要 未感知→左尾')

# 摘要里「等频分位映射」的自相矛盾
rep(MAIN, '分级采用零膨胀先验的等频分位映射',
    '分级采用零膨胀先验的分位映射', '摘要 删「等频」')

print(f'\n成功 {len(OK)}，失败 {len(FAIL)}')
for t, n in FAIL:
    print(f'  {t}（{n}）')
