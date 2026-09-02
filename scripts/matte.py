# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""兜底抠图（纯色键控）+ 构图对齐 + 成品 512x768。rembg 装好后走主路，这里是零依赖兜底。"""
import numpy as np, os, sys
from PIL import Image, ImageFilter

OUT_W, OUT_H = 512, 768
AXIS_LO, AXIS_HI = 0.55, 0.62      # 人物中轴必须落在画布横向 55%~62%

def key_by_border(img, tol=42.0, soft=18.0):
    """用四边边框像素估幕布色（含渐变：分上下两段各估一次），做距离阈值 + 软边。"""
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    h, w, _ = a.shape
    b = max(6, w // 60)
    # 渐变兼容：按行分 8 段，每段用左右边条估该段的幕布色
    alpha = np.zeros((h, w), np.float32)
    seg = h // 8
    for s in range(8):
        y0, y1 = s * seg, (h if s == 7 else (s + 1) * seg)
        strip = np.concatenate([a[y0:y1, :b], a[y0:y1, w - b:]], axis=1)
        bg = np.median(strip.reshape(-1, 3), axis=0)
        d = np.linalg.norm(a[y0:y1] - bg, axis=2)
        alpha[y0:y1] = np.clip((d - tol) / soft, 0, 1)
    # 去孤立噪点 + 羽化
    m = Image.fromarray((alpha * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
    return m

def despill(img, mask):
    """擦掉边缘沾的幕布色：把半透明边缘的饱和度往中性拉。"""
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    m = np.asarray(mask).astype(np.float32) / 255.0
    edge = ((m > 0.05) & (m < 0.95))[..., None]
    gray = a.mean(axis=2, keepdims=True)
    a = np.where(edge, a * 0.45 + gray * 0.55, a)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def compose(src_path, out_path):
    img = Image.open(src_path).convert('RGB')
    mask = key_by_border(img)
    rgba = despill(img, mask).convert('RGBA')
    rgba.putalpha(mask)

    bbox = mask.point(lambda v: 255 if v > 40 else 0).getbbox()
    if not bbox:
        return None
    cut = rgba.crop(bbox)
    cw, ch = cut.size

    # 先按高度定档：人物高度 = 画布高度的 92%
    th = int(OUT_H * 0.92)
    tw = max(1, int(cw * th / ch))
    if tw > OUT_W * 0.95:                       # 太宽就按宽度定档
        tw = int(OUT_W * 0.95); th = max(1, int(ch * tw / cw))
    cut = cut.resize((tw, th), Image.LANCZOS)

    canvas = Image.new('RGBA', (OUT_W, OUT_H), (0, 0, 0, 0))
    axis = 0.585                                 # 强制人物中轴落在 58.5%
    x = int(OUT_W * axis - tw / 2)
    x = max(min(x, OUT_W - tw), -int(tw * 0.06)) # 允许左边缘轻微出血
    y = OUT_H - th                               # 贴底
    canvas.alpha_composite(cut, (x, y))
    canvas.save(out_path)

    al = np.asarray(canvas)[..., 3]
    ratio = float((al > 20).mean())
    cols = np.where(al.max(axis=0) > 20)[0]
    real_axis = float((cols.min() + cols.max()) / 2.0 / OUT_W) if len(cols) else 0
    return {'file': out_path, 'opaque_ratio': round(ratio, 3), 'axis': round(real_axis, 3)}

if __name__ == '__main__':
    os.makedirs('matte', exist_ok=True)
    print('%-26s %-8s %-8s %s' % ('file', '不透明占比', '中轴', '判定'))
    for f in sorted(os.listdir('raw')):
        if not f.endswith('.jpg'):
            continue
        r = compose(os.path.join('raw', f), os.path.join('matte', f[:-4] + '.png'))
        if not r:
            print(f, 'FAIL empty'); continue
        ok = (0.15 < r['opaque_ratio'] < 0.75) and (AXIS_LO <= r['axis'] <= AXIS_HI)
        print('%-26s %-8.3f %-8.3f %s' % (f, r['opaque_ratio'], r['axis'], 'OK' if ok else '需复查'))
