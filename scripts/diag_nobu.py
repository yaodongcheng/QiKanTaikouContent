# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""信长诊断拼图：底稿 195/1154 vs 三张失败重跑 vs 原 R 版。"""
from PIL import Image, ImageDraw, ImageFont
import os

files = [
    ('底稿 195 信长', 'refs_koei/_tk5/195_织田信长_朝左.png'),
    ('底稿 1154 信长', 'refs_koei/_tk5/1154_织田信长_朝左.png'),
    ('原 R seed2001(0.73)', 'raw/lord_1_oda_织田信长_R.jpg'),
    ('R2 att1 seed2002(0.293)', 'raw/lord_1_oda_织田信长_R1.jpg'),
    ('R2 att2 seed2003(2.18)', 'raw/lord_1_oda_织田信长_R2.jpg'),
    ('R2 att3 seed2004(0.79)', 'raw/lord_1_oda_织田信长_R3.jpg'),
]
TILE_W, TILE_H = 330, 400
canvas = Image.new('RGB', (TILE_W * len(files), TILE_H), (18, 18, 20))
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 16)
for i, (lab, p) in enumerate(files):
    try:
        im = Image.open(p).convert('RGB')
        im.thumbnail((TILE_W - 10, TILE_H - 40))
        canvas.paste(im, (i * TILE_W + 5, 34))
    except Exception as e:
        print(p, e)
    draw.text((i * TILE_W + 5, 5), lab, fill=(255, 200, 60), font=font)
canvas.save('preview/nobu_fail_diag.jpg', quality=90)
print('preview/nobu_fail_diag.jpg %dx%d' % canvas.size)
