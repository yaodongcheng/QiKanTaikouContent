# -*- coding: utf-8 -*-
"""眼神方向粗筛（2026-08-29）：眼珠只看左/只看右/正——用户 1205 型裁定（脸正眼左 = 镜像）。

方法：FaceMesh 眼框四点 → 眼区灰度 → 虹膜（暗质心）vs 眼白（亮区）质心偏移：
  offx = 虹膜x - 眼区中心x；两眼的 offx 平均 < -0.01（眼宽归一）= 眼神左，> +0.01 = 右。
输出：refs_koei/eye_dirs.csv（file, offx, eye_dir）——eye_dir ∈ L/R/F/N（N=检测失败）。
用法：python eye_screen.py            # 全库 1015 张 ~5 分钟；可后处理只看 234 可疑
"""
import csv, glob, io, os
import mediapipe as mp
import numpy as np
import cv2

MP_FACE = mp.solutions.face_mesh


def imread_any(path):
    try:
        return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return cv2.imread(path)


def eye_offset(im, fm):
    rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    hole = rgb.shape[:2]
    r = fm.process(rgb)
    if not r.multi_face_landmarks:
        return None
    lm = r.multi_face_landmarks[0].landmark
    W, H = im.shape[1], im.shape[0]
    # 左右眼框（内侧角/外侧角/上下睑）：RIGHT_EYE=33,133,159,145 ; LEFT_EYE=362,263,386,374
    eyes = [(33, 133, 159, 145), (362, 263, 386, 374)]
    offs = []
    for a, b, up, lo in eyes:
        x0 = int(min(lm[a].x, lm[b].x) * W) - 2
        x1 = int(max(lm[a].x, lm[b].x) * W) + 2
        y0 = int(min(lm[up].y, lm[lo].y) * H) - 2
        y1 = int(max(lm[up].y, lm[lo].y) * H) + 2
        if x1 <= x0 or y1 <= y0:
            continue
        crop = cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        crop = cv2.resize(crop, (40, 20))
        # 虹膜 = 最暗 15% 区域质心；眼白 = 最亮 25% 质心
        flat = crop.flatten().astype(float)
        dark = np.percentile(flat, 15)
        bright = np.percentile(flat, 75)
        ys, xs = np.where(crop <= dark)
        if not len(xs):
            continue
        iris_x = xs.mean()
        wb = np.where(crop >= bright)
        if len(wb[0]) == 0:
            continue
        wb_x = wb[1].mean()
        offs.append((iris_x - wb_x) / 40.0)   # 眼宽归一
    if not offs:
        return None
    return round(float(np.mean(offs)), 4)


if __name__ == '__main__':
    rows = []
    with MP_FACE.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=False,
                          min_detection_confidence=0.3) as fm:
        for f in sorted(glob.glob('refs_koei/_tk5/*.png')):
            im = imread_any(f)
            off = eye_offset(im, fm) if im is not None else None
            if off is None:
                rows.append({'file': os.path.basename(f), 'offx': '', 'eye_dir': 'N'})
                continue
            d = 'L' if off < -0.01 else ('R' if off > 0.01 else 'F')
            rows.append({'file': os.path.basename(f), 'offx': off, 'eye_dir': d})
    with io.open('refs_koei/eye_dirs.csv', 'w', encoding='utf-8', newline='') as fp:
        w = csv.DictWriter(fp, fieldnames=['file', 'offx', 'eye_dir'])
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print('done -> refs_koei/eye_dirs.csv', Counter(r['eye_dir'] for r in rows))
