# -*- coding: utf-8 -*-
"""底图方向特征抽取（2026-08-29）：为分类器（核 SVM + LOO，见 pipeline_params.md §13）备料。

对 refs_koei/_tk5/*.png 全量抽取 6 维特征向量 + 真值标签列：
  features = [ratio(脸心-肩距比 dL/dR), shd(肩轴), dy(双肩垂直差),
              nose(鼻偏), sw(双肩宽比), dyNear(脸心-近肩垂直差)]
标签列 groundwork: label = R/F/L（0=无真值）— 真值源 = ref_verdicts.py + 用户口述清单。
输出：refs_koei/features.csv （每行: file, f1..f6, label）
用法：python extract_features.py   （~1.5-2h 全量，后台）
"""
import json, glob, os
import mediapipe as mp
import numpy as np
import cv2

MP_FACE, MP_POSE = mp.solutions.face_mesh, mp.solutions.pose


def imread_any(path):
    try:
        return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return cv2.imread(path)


def features_of(path, fm, pm):
    """每张只做推理，模型 session 由调用方共享（2026-08-29：原实现每图重建模型 = 2h，共享后 ~30min）。"""
    im = imread_any(path)
    fr = fm.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    pr = pm.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    if not fr.multi_face_landmarks or not pr.pose_landmarks:
        return None
    lm = fr.multi_face_landmarks[0].landmark
    fcx, fcy = (lm[33].x + lm[263].x) / 2, (lm[159].y + lm[23].y) / 2
    nose = lm[1].x
    plm = pr.pose_landmarks.landmark
    sL = plm[MP_POSE.PoseLandmark.LEFT_SHOULDER]
    sR = plm[MP_POSE.PoseLandmark.RIGHT_SHOULDER]
    dL, dR = abs(fcx - sL.x), abs(fcx - sR.x)
    return {
        'ratio': round(dL / dR, 4) if dR else None,
        'shd': round(sR.x - sL.x, 4),
        'dy': round(sL.y - sR.y, 4),
        'nose': round(nose - fcx, 4),
        'sw': round(abs(sL.x - sR.x), 4),
        'dyNear': round(fcy - (sL.y if dL >= dR else sR.y), 4),
    }


if __name__ == '__main__':
    rows = []
    with MP_FACE.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=False,
                          min_detection_confidence=0.3) as fm, \
         MP_POSE.Pose(static_image_mode=True, model_complexity=1,
                      min_detection_confidence=0.3) as pm:
        for f in sorted(glob.glob('refs_koei/_tk5/*.png')):
            feats = features_of(f, fm, pm)
            if feats is None:
                rows.append({'file': os.path.basename(f), 'ok': False})
                continue
            rows.append({'file': os.path.basename(f), 'ok': True, **feats})
    with open('refs_koei/features.csv', 'w', encoding='utf-8', newline='') as fp:
        keys = ['file', 'ok', 'ratio', 'shd', 'dy', 'nose', 'sw', 'dyNear']
        import csv as _csv
        w = _csv.DictWriter(fp, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print('done -> refs_koei/features.csv, %d 行' % len(rows))
