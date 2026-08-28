# -*- coding: utf-8 -*-
"""主路抠图：rembg isnet-general-use → 512x768 透明 PNG。

P5 已落地（2026-08-28）：不再做中轴平移，紧贴人物裁切、水平居中、贴底对齐，
512 宽全部给人物。「脸偏右」由画面内朝向实现，不由画布内平移实现。
"""
import os, json
import numpy as np
from PIL import Image
from rembg import remove, new_session

OUT_W, OUT_H = 512, 768
SESSION = new_session('isnet-general-use')


def matte(src):
    img = Image.open(src).convert('RGB')
    cut = remove(img, session=SESSION, alpha_matting=True,
                 alpha_matting_foreground_threshold=250,
                 alpha_matting_background_threshold=20,
                 alpha_matting_erode_size=6)
    return cut.convert('RGBA')


def place(rgba, out_path):
    """紧贴人物包围盒裁切 → 等比放到 512x768 内最大 → 水平居中 + 贴底。
    2026-08-28 追加头占比质检（用户裁定：头占比须统一）——用 OpenCV 人脸框高 ÷ 人物包围盒高。"""
    a = np.asarray(rgba)[..., 3]
    ys, xs = np.where(a > 25)
    if not len(xs):
        return None
    cut = rgba.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    cw, ch = cut.size
    # 等比缩放，短边顶格：优先撑满高度，撑不下（人物太宽）就改撑满宽度
    scale = min(OUT_W / cw, OUT_H / ch)
    tw, th = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    cut = cut.resize((tw, th), Image.LANCZOS)
    canvas = Image.new('RGBA', (OUT_W, OUT_H), (0, 0, 0, 0))
    canvas.alpha_composite(cut, ((OUT_W - tw) // 2, OUT_H - th))
    canvas.save(out_path)
    al = np.asarray(canvas)[..., 3]
    # 质检：不透明占比 / 是否有半透明破洞（人物内部 alpha 中间值过多 = 抠穿了）
    inner = al[al > 0]
    holes = float(((inner > 25) & (inner < 230)).mean()) if inner.size else 0.0
    # 头占比：人脸框高 / 人物包围盒高，约 0.18~0.30（半身立绘统一取景约定）
    head_ratio = None
    try:
        import cv2
        rgb = np.asarray(canvas.convert('RGB'))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) > 0:
            fh = max(f[3] for f in faces)
            head_ratio = round(fh / th, 3)   # 人脸高 ÷ 缩放后人物全高（th = 人物在 512x768 内的高）
    except Exception:
        pass
    return {'opaque': round(float((al > 25).mean()), 3),
            'holes': round(holes, 3),
            'fill_w': round(float(tw) / OUT_W, 3),
            'head_ratio': head_ratio,
            'head_ok': None if head_ratio is None else (0.14 <= head_ratio <= 0.34)}


def shoulder_ratio(rgba):
    """肩带比（剪影法，2026-08-28 用户标定 → T1a 正式落位）：
    上半身（人物包围盒顶 40% 高度带）内，画布中轴左半/右半的 alpha>25 像素比。
    通过区间 ∈ [1.05, 1.65] = 自然侧身（两面出界=拧巴，换 seed 重跑）。
    标定样本：阿市 1.10✅ 幸村 1.49✅ 信长 0.73❌ 訚千代 0.95❌ 秀吉 1.93❌。"""
    a = np.asarray(rgba)[..., 3]
    ys, xs = np.where(a > 25)
    if not len(xs):
        return None
    top = ys.min()
    H = int(ys.max() - top + 1)
    band = a[top: top + int(0.40 * H)]              # 上半身带：包围盒顶 40% 高
    h, w = band.shape
    left = int((band[:, :w // 2] > 25).sum())
    right = int((band[:, w // 2:] > 25).sum())
    if right == 0:
        return None
    return round(left / right, 3)


def qc_sheet(pngs, out_path, bg):
    """把成品贴到指定底色上拼成质检长图。"""
    cols = len(pngs)
    sheet = Image.new('RGB', (OUT_W * cols, OUT_H), bg)
    for i, p in enumerate(pngs):
        im = Image.open(p).convert('RGBA')
        tile = Image.new('RGB', (OUT_W, OUT_H), bg)
        tile.paste(im, (0, 0), im)
        sheet.paste(tile, (OUT_W * i, 0))
    sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS).save(out_path, quality=88)


if __name__ == '__main__':
    os.makedirs('matte_rembg', exist_ok=True)
    os.makedirs('preview', exist_ok=True)
    rows = []
    print('%-40s %-10s %-10s %-8s' % ('file', '不透明占比', '半透明破洞', '横向占比'))
    for f in sorted(os.listdir('raw')):
        if not f.endswith('.jpg'):
            continue
        out = os.path.join('matte_rembg', f[:-4] + '.png')
        r = place(matte(os.path.join('raw', f)), out)
        rows.append({'file': f, 'png': out, 'qc': r})
        print('%-28s %-10s %-10s %-8s' % (f, r and r['opaque'], r and r['holes'], r and r['fill_w']))
    json.dump(rows, open('matte_rembg_log.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    # 每人一张质检图：深底 + 浅底（组键 = 去掉末尾 _X.jpg 的版本后缀，版本约定为单字母）
    for sid in sorted({f[:-6] for f in (r['file'] for r in rows)}):
        ps = [r['png'] for r in rows if r['file'].startswith(sid + '_')]
        qc_sheet(ps, os.path.join('preview', sid + '_rembg_dark.jpg'), (28, 28, 34))
        qc_sheet(ps, os.path.join('preview', sid + '_rembg_light.jpg'), (232, 230, 224))
    print('done')
