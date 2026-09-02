# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""选图收尾（2026-08-29 用户 7 步流程第 3 步）：按 _review/picks.json 台账 →
  ① mirror=1 的镜像翻转 ② 全尺寸规范命名 normal 成品 ③ 台账文件 final_manifest.csv。
输入：_review/picks.json（pick_gui.py 产出）+ raw/ 尝试文件
输出：final/{sid}_{cn}.png（翻转后的正常向全尺寸图 = 情绪/头像/抠图/TPAC 的统一输入）
      _review/final_manifest.csv（sid, cn, src, mirror, final）
用法：python pick_finish.py
"""
import csv, io, json, os, sys, time

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
from PIL import Image

PICKS = '_review/picks.json'
OUT = 'final'
MAN = '_review/final_manifest.csv'


def main():
    picks = json.load(open(PICKS, encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    rows, missing, flipped = [], [], 0
    t0 = time.time()
    for i, (sid, p) in enumerate(sorted(picks.items())):
        src = os.path.join('raw', p['file'])
        if not os.path.exists(src):
            missing.append((sid, p['file']))
            continue
        im = Image.open(src).convert('RGB')
        if p.get('mirror'):
            im = im.transpose(Image.FLIP_LEFT_RIGHT)   # 🔴 几何镜像（非内容修改，铁律 22 合规）
            flipped += 1
        final = os.path.join(OUT, '%s_%s.png' % (sid, p.get('cn', '')))
        im.save(final)
        rows.append({'sid': sid, 'cn': p.get('cn', ''), 'src': p['file'],
                     'mirror': p.get('mirror', 0), 'final': os.path.basename(final)})
        if (i + 1) % 200 == 0:
            print('... %d/%d' % (i + 1, len(picks)))
    with io.open(MAN, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['sid', 'cn', 'src', 'mirror', 'final'])
        w.writeheader()
        w.writerows(rows)
    print('=== 完成 === 成品 %d 张（翻转 %d 张）| 源缺失 %d | 用时 %.0fs -> final/' % (
        len(rows), flipped, len(missing), time.time() - t0))
    if missing:
        print('!! 源缺失（需补）：%s' % missing[:20])
    # 镜像完整性抽查：验 10 张翻转产物的脸方向（应为 RIGHT）
    import verify_pose as V
    import random
    test = [r for r in rows if r['mirror']][:10]
    if test:
        ok = 0
        for r in test:
            res = V.judge(os.path.join(OUT, r['final']))
            if res['face_dir'] == 'RIGHT' and res['face_rel'] is not None:
                ok += 1
            else:
                print('?! 翻转后方向异常 %s: %s' % (r['final'], res['face_dir']))
        print('翻转抽查 %d/10 脸朝右' % ok)


if __name__ == '__main__':
    main()
