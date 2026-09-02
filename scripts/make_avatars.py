# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""头像派生（2026-08-29 用户裁定：从生成图自动定位头部裁切，不走人工）。

定位三层（从优到兜底）：
  1. mediapipe face bbox（verify_pose.judge['face_bbox']，顶部已外扩盖发髻/盔帽）
  2. OpenCV Haar 正脸 → 还原成正方形
  3. 构图比例兜底（提示词铁律：头占高 24~28% / 头顶留白 8% → 头带 y∈[0.10,0.36]）
裁切：以脸框为中心取正方形（max(W,H)×1.12 边），从**原图 raw** 裁（全分辨率，质量最高）→ 256×256。

输入：build_log.csv 的 final raw（PASS/PASS_EYES）+ rescue_log.csv 的 RESCUED（镜像版覆盖）。
输出：GUI/SpriteParts/taikou_avatar_{key}.png（key = StringId / tpl_{编号}）
      preview/avatars_{切片号}.jpg（审核拼图，深底）
用法：python make_avatars.py
"""
import csv, io, os, sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
from PIL import Image
import verify_pose as V

LOG_CSV = 'build_log.csv'
RESCUE = '_review/rescue_log.csv'
OUT_DIR = os.path.join('..', 'GUI', 'SpriteParts')  # 相对 ArtSource
AVATAR = 256

# ---------- 裁切几何（2026-08-29 用户裁定定稿，样本=信长 delta 0.18 档）----------
TOP_SKY = 0.03      # 顶部天空隙（相对脸框高）：以发髻/头盔与天空相切处为顶 + 3% 天空
CHIN = 0.18         # 下颚下方留量（相对脸框高）：完整下巴 + 领口起始，0.30 被否（太多）
LEFT_BIAS = 0.06    # 脸中心横移（相对边长）：左侧比右侧多留空间（0.12 偏多，否）
MIN_H = 1.20        # 框高下限（相对脸框高）：兜住宽发型/盔帽


def face_square(im_path, w, h):
    """返回 (px0, py0, px1, py1) 正方形裁切框（原图像素）。
    定位三层（从优到兜底）：mediapipe face bbox → Haar 正脸 → 构图比例。"""
    r = V.judge(im_path)
    bb = r.get('face_bbox')
    if bb is not None:
        x0, y0, x1, y1 = bb
    else:
        try:  # Haar 回退
            import cv2, numpy as np
            im = cv2.imdecode(np.fromfile(im_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            faces = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            ).detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            if len(faces) > 0:
                fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                x0, y0, x1, y1 = fx / w, fy / h, (fx + fw) / w, (fy + fh) / h
            else:
                raise ValueError('no_face')
        except Exception:
            # 构图兜底：头占高 24~28%、头顶留白 8%，头带约 y∈[0.10,0.36]
            x0, y0, x1, y1 = 0.30, 0.10, 0.70, 0.36
    hb = (y1 - y0) * h                       # 脸框高（bbox 顶部已外扩 0.75h 盖发髻/盔帽）
    y_top = y0 * h - TOP_SKY * hb
    y_bot = y1 * h + CHIN * hb
    span = y_bot - y_top
    side = max(MIN_H * hb, span)
    cx = (x0 + x1) / 2 * w - LEFT_BIAS * side   # 左多右少
    cy = (y_top + y_bot) / 2
    px0 = int(cx - side / 2); py0 = int(cy - side / 2)
    px0 = max(0, min(px0, w - int(side))); py0 = max(0, min(py0, h - int(side)))
    # 夹紧后仍不够方形时补回另一边
    if w - px0 < side:
        px0 = max(0, w - int(side))
    if h - py0 < side:
        py0 = max(0, h - int(side))
    return (px0, py0, px0 + int(side), py0 + int(side))


def final_map():
    """key → 最终 raw 路径：build_log PASS/PASS_EYES 优先，rescue_log RESCUED 覆盖。"""
    m = {}
    with io.open(LOG_CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r.get('status') in ('PASS', 'PASS_EYES') and r.get('raw'):
                m[r['key']] = r['raw']
    if os.path.exists(RESCUE):
        with io.open(RESCUE, encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                if r.get('status') == 'RESCUED' and r.get('mirrored'):
                    m[r['key']] = os.path.join('raw', r['mirrored'])
    return m


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs('preview', exist_ok=True)
    m = final_map()
    print('待派生头像: %d' % len(m))
    sheet = Image.new('RGB', (AVATAR * 8, AVATAR * 8), (28, 28, 34))
    i, ok, skip = 0, 0, 0
    for key, raw in sorted(m.items()):
        if not os.path.exists(raw):
            skip += 1
            continue
        try:
            im = Image.open(raw)
            w, h = im.size
            box = face_square(raw, w, h)
            # 🔴 从全分辨率原图直接裁（头像窄化方向 = 向下缩放，清晰；先缩再裁会糊，勿改）
            face = im.convert('RGB').crop(box).resize((AVATAR, AVATAR), Image.LANCZOS)
        except Exception as e:
            print('!! %s: %s' % (key, str(e)[:80]))
            skip += 1
            continue
        face.save(os.path.join(OUT_DIR, 'taikou_avatar_%s.png' % key))
        sheet.paste(face, (AVATAR * (i % 8), AVATAR * (i // 8 % 8)))
        i += 1
        if i % 64 == 0:
            sheet.save('preview/avatars_%03d.jpg' % (i // 64), quality=88)
            sheet = Image.new('RGB', (AVATAR * 8, AVATAR * 8), (28, 28, 34))
    if i % 64:
        sheet.save('preview/avatars_%03d.jpg' % (i // 64 + 1), quality=88)
    print('完成 %d / 跳过 %d | 成品 -> %s' % (i, skip, OUT_DIR))


if __name__ == '__main__':
    main()
