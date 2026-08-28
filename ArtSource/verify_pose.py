# -*- coding: utf-8 -*-
"""
方向裁判：用 face/pose 关键点坐标（mediapipe 0.10.14）对生成图判「脸方向 + 肩部转向」，
替代肉眼判读（2026-08-28：肉眼左右判读存在系统性镜像误读，改数字判向）。

判据（用户标定，锚定样本 = 阿市 / 訚千代；用户按解剖语言说「右肩近镜」）：
  face  : 鼻 x − 双眼中点 x ≥ 0.030 → 脸清晰朝画面右（RIGHT）
  sh    : 解剖右肩 x − 解剖左肩 x ≤ −0.15 → 近景肩在画面左侧（= 解剖右肩，用户说的"右肩近镜"）
  二者齐备才 PASS；任一漏检（None）= FAIL（宁可重跑，不许盲过）。

用法：python verify_pose.py file1.png [file2.png ...]
"""
import sys, os
import numpy as np
import mediapipe as mp
import cv2

mp_face = mp.solutions.face_mesh
mp_pose = mp.solutions.pose


def run_face(fm, im):
    r = fm.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    if not r.multi_face_landmarks:
        return None, None
    lm = r.multi_face_landmarks[0].landmark
    frx = lm[1].x - (lm[33].x + lm[263].x) / 2
    # 2026-08-28 收窄带 ±0.003（原 ±0.012 吞符号：1057 镜像实测 +0.007 微右被判成 FRONT，
    # 用户肉眼当众指正；弱不对称的镜像会翻转朝向，符号不得丢）
    d = 'RIGHT' if frx > 0.003 else ('LEFT' if frx < -0.003 else 'FRONT')
    return d, round(frx, 3)


def run_pose(pm, im):
    r = pm.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    if not r.pose_landmarks:
        return None
    plm = r.pose_landmarks.landmark
    return round(plm[mp_pose.PoseLandmark.RIGHT_SHOULDER].x -
                 plm[mp_pose.PoseLandmark.LEFT_SHOULDER].x, 3)


def imread_any(path):
    """cv2.imread 读不了中文路径（Windows），用 np.fromfile + imdecode。"""
    try:
        return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return cv2.imread(path)


def judge(path):
    im = imread_any(path)
    fd, fr, sh = None, None, None
    with mp_face.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True,
                          min_detection_confidence=0.3) as fm, \
         mp_pose.Pose(static_image_mode=True, model_complexity=2,
                      min_detection_confidence=0.3) as pm:
        fd, fr = run_face(fm, im)
        sh = run_pose(pm, im)
        # 漏检回退：上采样 1.6 再试（兜盔/半身遮挡场景）
        if fd is None or sh is None:
            big = cv2.resize(im, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
            if fd is None:
                fd, fr = run_face(fm, big)
            if sh is None:
                sh = run_pose(pm, big)
    ok = (fr is not None) and (fr >= 0.030) and (sh is not None) and (sh <= -0.15)
    return {'face_dir': fd, 'face_rel': fr, 'shoulder_diff': sh, 'pass': ok}


if __name__ == '__main__':
    for p in sys.argv[1:]:
        try:
            r = judge(p)
            print('%-52s  face=%s(%s)  肩轴(右-左x)=%s  => %s'
                  % (os.path.basename(p), r['face_dir'], r['face_rel'],
                     r['shoulder_diff'], 'PASS' if r['pass'] else 'FAIL'))
        except Exception as e:
            print('%-52s  ERR %s' % (os.path.basename(p), e))
