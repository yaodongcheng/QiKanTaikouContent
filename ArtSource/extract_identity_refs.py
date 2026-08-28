# -*- coding: utf-8 -*-
"""身份底稿抽取（2026-08-28 用户裁定：太阁5 本地 BUSTUP 为身份类 NPC 底稿真源）。

把「每身份一张代表」所需的全部候选项从 E:/taikou5/TaikouImage/BUSTUP 转 PNG 入
refs_koei/_tk5/identity/（gitignore 覆盖整目录），并生成带编号的预览拼图
preview/identity_contact_*.jpg，供人眼选代表（无卡X 组 55~62 张/组，只用看拼图挑）。
"""
import os
from PIL import Image

SRC = r'E:\taikou5\TaikouImage\BUSTUP'
OUT = 'refs_koei/_tk5/identity'

# 身份类候选（编号_姓名 目录）
GROUPS = {
    'merchant': list(range(913, 975)) + [1116],              # 无卡商人 62 + 商人 1
    'ninja':    list(range(860, 913)) + [1120, 1150],        # 无卡忍者 53 + 忍者 2
    'pirate':   list(range(975, 1030)) + [1140, 1151, 1148], # 无卡海贼 55 + 海贼 2 + 海贼头目
    'singles': [1085, 1107, 1108, 1109, 1110, 1111, 1112, 1113, 1114, 1115,
                1117, 1118, 1119, 1121, 1122, 1127, 1128, 1130, 1131, 1136,
                1137, 1138, 1139, 1141, 1142, 1143, 1144, 1145, 1146, 1147, 1149],
}

def find_dir(pid):
    for d in os.listdir(SRC):
        if d.startswith('%d_' % pid):
            return os.path.join(SRC, d)
    return None

def convert(pid):
    path = find_dir(pid)
    if not path:
        return None
    dds = os.path.join(path, '000.dds')
    if not os.path.exists(dds):
        return None
    out = os.path.join(OUT, os.path.basename(path) + '.png')
    if not os.path.exists(out):
        Image.open(dds).convert('RGBA').save(out)
    return out

def sheet(pngs, labels, out_path, cols=16, tile=128):
    import math
    rows = (len(pngs) + cols - 1) // cols
    H = tile + 24
    canvas = Image.new('RGB', (cols * tile, rows * H), (18, 18, 20))
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for i, (png, lab) in enumerate(zip(pngs, labels)):
        r, c = divmod(i, cols)
        x, y = c * tile, r * H + 20
        try:
            im = Image.open(png).convert('RGBA')
            im.thumbnail((tile - 4, tile - 4))
            canvas.paste(im, (x + 2, y + 2), im)
        except Exception:
            pass
        draw.text((x + 2, r * H + 2), str(lab), fill=(255, 200, 60), font=font)
    canvas.save(out_path, quality=88)
    print(out_path)

def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs('preview', exist_ok=True)
    # 先转换，再按组出拼图
    for key, ids in GROUPS.items():
        items = []
        good = []
        for pid in ids:
            p = convert(pid)
            if p:
                items.append((p, pid))
                good.append(pid)
        sheet([p for p, _ in items], good, 'preview/identity_contact_%s.jpg' % key)
        print('%s: 转换 %d/%d' % (key, len(items), len(ids)))

if __name__ == '__main__':
    main()
