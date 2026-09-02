# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""审批收口校验 + 选定成品收集（2026-08-30 用户指令）。

① 校验：picktkid 全部 tkid 状态分布（期望：仅 chosen/dropped，redraw=0，无「未定」）。
② 收集：按 chosen（+ mirror 翻转）把 raw/ 成品 → selected/{tkid}_{StringId}.png（后续处理源头）。
mirror=1 的做左右镜像翻转（选图窗口的镜像预览 = 成品方向）。
幂等：已有目标文件跳过；输出统计与缺失清单。
用法：python collect_selected.py [--limit N]
"""
import json, os, re, sys
from PIL import Image

PICKTKID = '_review/picktkid.json'
RAW = 'raw'
OUT = 'selected'


def main():
    st = json.load(open(PICKTKID, encoding='utf-8'))
    from collections import Counter
    dist = Counter()
    bad, missing = [], []
    os.makedirs(OUT, exist_ok=True)
    n_done = 0
    for t, v in sorted(st.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 999999):
        if not isinstance(v, dict):
            continue
        if v.get('chosen'):
            dist['chosen'] += 1
        elif v.get('dropped'):
            dist['dropped'] += 1
        elif 'redraw' in v:
            dist['redraw'] += 1
        else:
            dist['未定'] += 1
            missing.append(t)
        if not v.get('chosen'):
            continue
        src = os.path.join(RAW, v['chosen'])
        if not os.path.exists(src):
            bad.append((t, v['chosen']))
            continue
        sid = v.get('sid') or ''
        dst = os.path.join(OUT, '%s_%s.png' % (t, sid))
        if os.path.exists(dst):
            n_done += 1
            continue
        img = Image.open(src).convert('RGBA')
        if v.get('mirror'):
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        img.save(dst)
        n_done += 1
    print('== 审批校验 ==')
    print('状态分布:', dict(dist))
    if missing:
        print('⚠ 未定卡 %d 张:%s' % (len(missing), missing[:20]))
    if dist.get('redraw'):
        print('⚠ 仍红标 %d 张（请窗口确认）' % dist['redraw'])
    print('== 收集 ==')
    print('selected/ 产出: %d 张 | 源缺失: %d' % (n_done, len(bad)))
    for b in bad[:10]:
        print('  !! 源缺失', b)


if __name__ == '__main__':
    main()
