# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""收尾工具（2026-08-29）：①逐一审核清单 ②镜像救援（不走生成）。

用法（跑批完成后）：
  python rescue_mirror.py --review            # 重测全部 raw 尝试文件 → _review/review_manifest.csv
  python rescue_mirror.py --rescue            # FAIL/PASS_EYES 的 key 逐尝试文件镜像 → 双闸 → 第一个过=RESCUED
  python rescue_mirror.py --rescue --manual lord_1_xxx,lord_1_yyy   # 用户审完手动点名要镜像的 key
镜像规则：PIL FLIP_LEFT_RIGHT（与底稿镜像同一几何变换，非手 P 内容）；
近正图（|face_rel| < 0.003）镜像无意义 → 不救，标注 NOT_RESCUED(近正)。
镜像后如需继续救：RESCUED 的 final = {key}_{cn}_M.png，后处理以它为准。
"""
import argparse, csv, io, json, os, sys, glob

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
from PIL import Image
import verify_pose as V

LOG_CSV = 'build_log.csv'
REVIEW_DIR = '_review'


def gate_file(path):
    r = V.judge(path)
    fr, shd = r['face_rel'], r['shoulder_diff']
    fok = fr is not None and fr >= 0.030
    sok = shd is not None and shd <= -0.15
    near = fr is not None and 0.025 <= fr < 0.030, shd is not None and -0.20 < shd <= -0.15
    return {'face_rel': fr, 'shoulder_diff': shd,
            'fok': fok, 'sok': sok,
            'near': any(near) and (fok and sok)}


def parse_log():
    if not os.path.exists(LOG_CSV):
        return []
    with io.open(LOG_CSV, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def attempts_of(key, cn):
    pat = 'raw/%s_%s_[RA][0-9].png' % (key, cn)
    return sorted(glob.glob(pat))


def review():
    os.makedirs(REVIEW_DIR, exist_ok=True)
    rows = parse_log()
    out = [{'key': '', 'cn': '', 'attempt': '', 'face_rel': '', 'shoulder_diff': '',
            'final_status': '', 'note': ''}]
    for r in rows:
        for ap in attempts_of(r['key'], r['cn']):
            g = gate_file(ap)
            out.append({'key': r['key'], 'cn': r['cn'],
                        'attempt': os.path.basename(ap),
                        'face_rel': '%.3f' % g['face_rel'] if g['face_rel'] is not None else 'None',
                        'shoulder_diff': '%.3f' % g['shoulder_diff'] if g['shoulder_diff'] is not None else 'None',
                        'final_status': r['status'],
                        'note': '近正' if (g['face_rel'] is not None and abs(g['face_rel']) < 0.003) else
                                ('过闸' if g['fok'] and g['sok'] else ('贴线' if g['near'] else ''))})
    with io.open(os.path.join(REVIEW_DIR, 'review_manifest.csv'), 'w',
                 encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=out[0].keys())
        w.writeheader()
        w.writerows(out[1:])
    print('review_manifest.csv -> %s' % os.path.join(REVIEW_DIR, 'review_manifest.csv'))


def rescue(manual_keys=None):
    os.makedirs(REVIEW_DIR, exist_ok=True)
    rows = parse_log()
    targets = [r for r in rows if r['status'] in ('FAIL', 'PASS_EYES')]
    if manual_keys:
        keep = set(manual_keys.split(','))
        targets = [r for r in rows if r['key'] in keep]
    print('待镜像 key: %d' % len(targets))
    out = []
    for r in targets:
        near_note = []
        for ap in attempts_of(r['key'], r['cn']):
            srcg = gate_file(ap)
            if srcg['face_rel'] is not None and abs(srcg['face_rel']) < 0.003:
                near_note.append(os.path.basename(ap) + ' 近正(镜像无效)')
                continue  # 该尝试镜像无效，试下一个尝试文件
            im = Image.open(ap).convert('RGB')
            m_path = os.path.join('raw', r['key'] + '_' + r['cn'] + '_M.png')
            im.transpose(Image.FLIP_LEFT_RIGHT).save(m_path)
            g = gate_file(m_path)
            if g['fok'] and g['sok']:
                out.append({'key': r['key'], 'cn': r['cn'], 'src': os.path.basename(ap),
                            'mirrored': os.path.basename(m_path),
                            'face_rel': '%.3f' % g['face_rel'],
                            'shoulder_diff': '%.3f' % g['shoulder_diff'],
                            'status': 'RESCUED',
                            'note': '; '.join(near_note)})
                break
        else:
            out.append({'key': r['key'], 'cn': r['cn'], 'src': '(所有尝试)',
                        'mirrored': '', 'status': 'NOT_RESCUED',
                        'note': ('; '.join(near_note) + ' | ' if near_note else '')
                                + '镜像后仍不过闸 → 人工重画'})
    with io.open(os.path.join(REVIEW_DIR, 'rescue_log.csv'), 'w',
                 encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['key', 'cn', 'src', 'mirrored', 'face_rel',
                                          'shoulder_diff', 'status', 'note'])
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print('rescue_log.csv 完成:', dict(Counter(o['status'].split('(')[0] for o in out)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--review', action='store_true')
    ap.add_argument('--rescue', action='store_true')
    ap.add_argument('--manual', default='')
    a = ap.parse_args()
    if a.review:
        review()
    elif a.rescue:
        rescue(a.manual or None)
    else:
        ap.print_help()
