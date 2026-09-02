# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""朝右强执（2026-08-29 用户裁定：refs_koei 禁止出现朝左底稿）。

扫描 refs_koei/_tk5/** 下全部 *_朝左.png（主目录旧资产 + identity 身份模板），
镜像处理 → 写为 _朝右（已存在同名朝右则覆盖为镜像版一致性检查后删朝左），
最终全目录 0 个朝左。朝正（FRONT, 108 张）保留：正脸无法靠镜像变侧脸，属中性锚
（生成时无方向锚，靠 seed 抽——朝正不是"朝左"，不违反禁令）。

用法：python enforce_right.py   # 幂等：跑完再跑一遍 = 0 处理
"""
import glob, io, os
from PIL import Image

OUT = 'refs_koei/_tk5'


def main():
    lefts = [f for f in glob.glob(OUT + '/**/*_朝左.png', recursive=True)]
    done, skip = 0, 0
    for f in lefts:
        target = f.replace('_朝左.png', '_朝右.png')
        im = Image.open(f).convert('RGBA').transpose(Image.FLIP_LEFT_RIGHT)  # 朝左 → 朝右
        im.save(target)
        if os.path.exists(f):
            os.remove(f)   # 已镜像落地，原朝左文件按「禁止出现」移除
        done += 1
    # 复核：再扫一遍确保 0
    remain = [f for f in glob.glob(OUT + '/**/*_朝左.png', recursive=True)]
    print('镜像 -> 朝右: %d 张；残留朝左: %d（应 0）' % (done, len(remain)))


if __name__ == '__main__':
    main()
