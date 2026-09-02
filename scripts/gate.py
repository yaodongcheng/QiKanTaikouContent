# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""构图数字闸门（2026-08-28 定稿，T1a 修复）：脸 RIGHT≥0.030 + 肩轴(解剖右肩x−左肩x)≤−0.15。

🔴 2026-08-28 闸门修复：肩闸由剪影法（M.shoulder_ratio 像素比）切回解剖法——
同图实测两指标打架（信长 boost 版：解剖 -0.358 ✅ vs 剪影 0.149 ❌），用户肉眼+解剖
一致 = 躯干对、脸单偏。剪影法失准根因：①画布中轴≠躯干中轴（紧贴裁切+居中+头偏时错位）
②远侧胸甲硬件占像素多 ≈ 假「近大远小」。解剖法原文义见 verify_pose.py（用户「右肩近镜」）。
剪影比保留为参考输出（需 matte png），不作闸门。

用法：
  python gate.py check            # 对 matte_rembg/ 现有全部成品复算两闸并打印（含标定样本对照）
  python gate.py check 文件1 文件2   # 指定文件: 自动找同名前缀的 raw jpg 判脸闸（无则跳过脸闸）
"""
import os, sys
import numpy as np
from PIL import Image
import matte_rembg as M
import verify_pose as V

FACE_MIN = 0.030           # 鼻 x − 双眼中点 x → 脸清晰朝画面右
SH_DIFF_MAX = -0.15        # 解剖右肩x − 解剖左肩x ≤ −0.15 → 近景肩（右肩）在画面左侧

CALIBRATION = {  # 标定样本对照（用户 2026-08-28 手工标定 = 剪影比旧数，仅参考对照）
    'lord_1_azai_1_阿市_R': 1.10, 'lord_1_sanada_9_真田幸村_R': 1.49,
    'lord_1_oda_织田信长_R': 0.73, 'lord_1_bekki_2_訚千代_R': 0.95,
    'lord_1_kinoshita_丰臣秀吉_R': 1.93,
}


def face_gate(img_path):
    r = V.judge(img_path)
    return (r['face_rel'] is not None and r['face_rel'] >= FACE_MIN), r['face_rel']


def shoulder_gate(img_path):
    """解剖法肩闸：近景肩（解剖右肩）在画面左侧（用户「右肩近镜」语义）。
    漏检 None = FAIL（宁可重跑，不许盲过）。"""
    sh = V.judge(img_path)['shoulder_diff']
    return (sh is not None and sh <= SH_DIFF_MAX), sh


def classify(path):
    """初筛四元组分类 + 异常值标记（2026-08-28：初筛+人目复核纪律，25 张旧图教训）：
    ① PASS / ② 脸FAIL(身对) / ③ 身FAIL(脸对) / ④ 双FAIL / 测量失败。
    异常值（None / |肩轴|>0.9（-1.0 钉边）/ |脸−0.030|<0.01 / |肩轴+0.15|<0.05）→ ⚠️ NEED_EYES。
    闸门阈值为 raw 写实域标定；底稿域数值不适用本门（见 pipeline_params.md §7）。"""
    fok, fr = face_gate(path)
    sok, shd = shoulder_gate(path)
    if fok is None and sok is None:
        cls = '测量失败'
    elif fok is None:
        cls = '测量失败(脸)'
    elif sok is None:
        cls = '测量失败(肩)'
    elif fok and sok:
        cls = '① PASS'
    elif fok:
        cls = '③ 身FAIL(脸对)'
    elif sok:
        cls = '② 脸FAIL(身对)'
    else:
        cls = '④ 双FAIL'
    eyes = (fr is None or shd is None
            or (shd is not None and abs(shd) > 0.9)
            or (fr is not None and abs(fr - FACE_MIN) < 0.01)
            or (shd is not None and abs(shd - SH_DIFF_MAX) < 0.05))
    return {'file': path, 'class': cls, 'face_ok': fok, 'face_rel': fr,
            'shoulder_ok': sok, 'shoulder_diff': shd, 'need_eyes': eyes}


def check(png):
    base = os.path.basename(png)
    root = base[:-4]  # 去掉 .png
    raw_cand = None
    for p in ('raw', os.path.join(os.path.dirname(png), 'raw')):
        q = os.path.join(p, root + '.jpg')
        if os.path.exists(q):
            raw_cand = q
            break
    try:
        fok, fr = face_gate(raw_cand) if raw_cand else (None, None)
    except Exception as e:
        fok, fr = None, 'ERR ' + str(e)
    try:
        sok, shd = shoulder_gate(raw_cand if raw_cand else png)
    except Exception as e:
        sok, shd = None, 'ERR ' + str(e)
    sil = None
    try:
        sil = M.shoulder_ratio(Image.open(png).convert('RGBA'))
    except Exception:
        pass
    cal = CALIBRATION.get(root)
    tag = '标定=%s' % cal if cal else '--'
    print('%-42s 脸=%s(%.3f)  肩轴=%s(%.3f /≤-0.15)  剪影参考=%s  %s  闸门=%s'
          % (base, 'OK' if fok else ('FAIL' if fok is not None else 'SKIP'),
             fr if isinstance(fr, float) else 0,
             'OK' if sok else ('FAIL' if sok is not None else 'SKIP'),
             shd if isinstance(shd, float) else 0, sil, tag,
             'PASS' if ((fok is None or fok) and (sok is None or sok)) else 'FAIL'))
    return (fok, sok)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        files = sys.argv[2:] or sorted(
            os.path.join('matte_rembg', f) for f in os.listdir('matte_rembg') if f.endswith('.png'))
        for f in files:
            check(f)
