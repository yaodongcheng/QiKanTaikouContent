# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""按用户裁决表落库 v2（2026-08-29）。

🔴 v2 修复：v1「对当前文件再镜像」非幂等——补 1279 时全表重跑，L 项二次镜像 = 翻回反面，
用户抓包（1288 被覆盖回朝左）。v2 一律 **从 E 盘源 dds 重新转换**（不论当前文件处于
多少次镜像态），L = 源→镜像一次落 _朝右；F = 源→原样落 _朝正。结果 = 唯一正确终态。
只动 VERDICT 列的角色，其余 0 改动。跑完 build_refs_full 重刷 manifest。
用法：python apply_verdicts.py
"""
import glob, os
from PIL import Image
from ref_verdicts import VERDICT

SRC = r'E:\taikou5\TaikouImage\BUSTUP'
OUT = 'refs_koei/_tk5'


def main():
    for key, v in VERDICT.items():
        pid, cn = key.split('_', 1)
        # 源目录：仅按编号找（名字对不上编号也不会同名）
        cand = None
        for d in sorted(os.listdir(SRC)):
            if d.startswith('%s_' % pid) and os.path.exists(os.path.join(SRC, d, '000.dds')):
                cand = os.path.join(SRC, d, '000.dds')
                break
        if not cand:
            print('跳过(源缺失) %s' % key)
            continue
        im = Image.open(cand).convert('RGBA')
        if v == 'L':
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
            tgt = os.path.join(OUT, '%s_朝右.png' % key)
        else:
            tgt = os.path.join(OUT, '%s_朝正.png' % key)
        im.save(tgt)
        # 清理同 key 的其他方向旧文件（含被覆盖错的朝右副本）
        for f in sorted(glob.glob(os.path.join(OUT, '%d_%s_朝*.png' % (int(pid), cn)))):
            if os.path.abspath(f) != os.path.abspath(tgt):
                os.remove(f)
        print('%s 源重建%s: %s' % (key, '镜像+' if v == 'L' else '', os.path.basename(tgt)))
    print('done')


if __name__ == '__main__':
    main()
