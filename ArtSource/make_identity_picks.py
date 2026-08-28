# -*- coding: utf-8 -*-
"""身份代表大图拼表：从 identity/ 转换库挑每身份一张，放大到可看清再人工确认。"""
import os
from PIL import Image, ImageDraw, ImageFont

DIR = 'refs_koei/_tk5/identity'

# 身份 → 底稿 ID（2026-08-28 用户裁定：一个 TK5 类型一张，与 identity_refs.py 一致）
PICKS = [
    ('商人', 952), ('忍者', 886), ('海贼(船系)', 1012), ('海贼头目', 1148),
    ('山贼头目', 1147), ('备大将(武家)', 1121), ('剑术教头(师范/浪人)', 1118),
    ('代理教头(师范代/见习)', 1139), ('僧侣', 1117), ('公家', 1119),
    ('医师', 1138), ('锻冶匠', 1137), ('掌柜', 1136), ('男仆(伙计)', 1143),
    ('农民男(无效)', 1112),
]

TILE_W, TILE_H = 200, 280
LBL_H = 16
COLS = 6

if __name__ == '__main__':
    rows = (len(PICKS) + COLS - 1) // COLS
    canvas = Image.new('RGB', (COLS * TILE_W, rows * (TILE_H + LBL_H)), (18, 18, 20))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 14)   # 微软雅黑，Label 带中文
    for i, (cls, pid) in enumerate(PICKS):
        r, c = divmod(i, COLS)
        x, y = c * TILE_W, r * (TILE_H + LBL_H) + LBL_H
        p = os.path.join(DIR, '%d_*.png' % pid)
        import glob
        ms = glob.glob(p)
        if not ms:
            draw.text((x + 4, y - LBL_H + 2), '%s %d MISSING' % (cls, pid), fill=(255, 80, 80), font=font)
            continue
        im = Image.open(ms[0]).convert('RGBA')
        im.thumbnail((TILE_W - 8, TILE_H - 8))
        canvas.paste(im, (x + 4, y + 4), im)
        draw.text((x + 4, y - LBL_H + 2), '%s  [%d]' % (cls, pid), fill=(255, 200, 60), font=font)
    canvas.save('preview/identity_picks.jpg', quality=92)
    print('preview/identity_picks.jpg  %dx%d' % canvas.size)
