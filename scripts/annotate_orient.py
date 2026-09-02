# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""底稿朝向标注器（2026-08-28）：全量测量 refs_koei/_tk5/**/*.png 的脸朝向 + 肩轴，
写 refs_koei/_tk5/orientation.json（机器台账，可重跑刷新）。
人工台账（meta.json / identity_refs.py 的 ORIENTATION）以此文件为测量源。
用法：python annotate_orient.py   （本地 mediapipe，~1 分钟，零 API 成本）

🔴 人名 = 感知仲裁（2026-08-28 用户裁定）：近正图 mediapipe 鼻偏不可靠（面罩/额带/眉毛
干扰鼻尖定位；实证：886 面罩判出 +0.007 假右，用户肉眼 = 正）。文件名朝向以用户肉眼为准，
PERCEPT_OVERRIDE = 最终标签（只在这些文件名上生效），数值仅存档参考；测量值只用于
"用户没看的图"兜底预判。
"""
import glob, json, os
import verify_pose as V

PERCEPT_OVERRIDE = {
    '517_丰臣秀吉_朝左.png': 'LEFT',   # 用户：微左（mediapipe +0.001 被钵卷/眉形干扰）
    '517_丰臣秀吉_朝右.png': 'RIGHT',  # 镜像翻转推得（原版=左 → 镜像=右，1057 先例）
    '1012_无卡海贼_朝左.png': 'LEFT',  # 用户：微左
    '952_无卡商人_朝右.png': 'RIGHT',  # 用户：微右
    '886_无卡忍者_朝正.png': 'FRONT',  # 用户：正（面罩遮鼻唇，mediapipe +0.007 假右）
}


def main():
    rows = []
    for f in sorted(glob.glob('refs_koei/_tk5/**/*.png', recursive=True)):
        rel = os.path.relpath(f, 'refs_koei/_tk5').replace(os.sep, '/')
        base = os.path.basename(rel)
        try:
            r = V.judge(f)
            meas, val = r['face_dir'], r['face_rel']
            shd = r['shoulder_diff']
        except Exception as e:
            meas, val, shd = None, None, None
            err = str(e)[:200]
        final = PERCEPT_OVERRIDE.get(base, meas)
        row = {'file': rel, 'face': final, 'face_measured': meas,
               'face_rel': val, 'shoulder_diff': shd,
               'percept': base in PERCEPT_OVERRIDE}
        if 'err' in locals() and err:
            row['err'] = err
        rows.append(row)
    with open('refs_koei/_tk5/orientation.json', 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    n_l = sum(1 for r in rows if r['face'] == 'LEFT')
    n_f = sum(1 for r in rows if r['face'] == 'FRONT')
    n_r = sum(1 for r in rows if r['face'] == 'RIGHT')
    print('ok %d 张 -> refs_koei/_tk5/orientation.json (LEFT=%d FRONT=%d RIGHT=%d, 感知校准 %d 张)'
          % (len(rows), n_l, n_f, n_r, sum(1 for r in rows if r['percept'])))


if __name__ == '__main__':
    main()
