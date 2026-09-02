# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""阶段版流水线（2026-08-29 用户追加轮）：35 人词表的多形象 → 未生成的那些形象(
不在 manifest 主形象 = raw 已有) → 底稿转置 → R 版生成 + 双闸 → 追加 build_log.csv
(key = '{sid}#{stage}')，pick_gui 第二轮窗口按同机制审。
用法：python stage_pipeline.py [--refs-only]
"""
import base64, csv, glob, io, json, os, sys, time, urllib.request, urllib.error

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
from PIL import Image
import gen_portrait as G
import run_trial as RT
import verify_pose as V
from update_portrait_stages import PORTRAIT_STAGES

SRC = r'E:\taikou5\TaikouImage\BUSTUP'
OUT = 'refs_koei/_tk5'
REF_JSON = '_stage_refs.json'
MAX_ATT = 3


def ensure_ref(tkid, sid):
    """返回该编号的朝右底稿路径；没有就 dds→判向→镜像转一份。"""
    fs = sorted(glob.glob(os.path.join(OUT, '%d_*.png' % tkid)))
    keep = [f for f in fs if not f.endswith('_朝左.png')]
    keep.sort(key=lambda f: (0 if f.endswith('_朝右.png') else 1))
    if keep:
        return keep[0]
    cand = [d for d in os.listdir(SRC) if d.startswith('%d_' % tkid)
            and os.path.exists(os.path.join(SRC, d, '000.dds'))]
    if not cand:
        print('!! 底稿缺失 %d (%s)' % (tkid, sid))
        return None
    ddir = cand[0]
    im = Image.open(os.path.join(SRC, ddir, '000.dds')).convert('RGBA')
    tmp = os.path.join(OUT, '_tmp_stage.png')
    im.save(tmp)
    try:
        d = V.judge(tmp)['face_dir']
    except Exception:
        d = None
    if d == 'LEFT':
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        tag = '朝右'
    elif d == 'RIGHT':
        tag = '朝右'
    else:
        tag = '朝正'
    final = os.path.join(OUT, '%s_%s.png' % (ddir, tag))
    im.save(final)
    return final


def build_jobs():
    manifest = json.load(open('refs_koei/_tk5/hero_refs_manifest.json', encoding='utf-8'))
    heroes = RT.load_heroes(set(PORTRAIT_STAGES.keys()))
    genders = {}
    with io.open(RT.CSV, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r.get('ID') in heroes:
            genders[r['ID']] = '女' if (r.get('Gender') or '') == '0' else '男'
    jobs, refs = [], {}
    for sid, recs in PORTRAIT_STAGES.items():
        base = manifest.get(sid)
        base_id = str(base.get('base_id')) if isinstance(base, dict) and base.get('base_id') else None
        h = dict(heroes.get(sid, {}))
        h.update(RT.OVERRIDES.get(sid, {}))
        h['gender'] = genders.get(sid, '男')
        for rec in recs:
            tkid = str(rec['tkid'])
            if tkid == base_id:
                continue  # 主形象已在 raw（跑批）→ 跳过
            key = '%s#%s' % (sid, rec['stage'])
            refs[key] = ensure_ref(int(tkid), sid)
            hx = dict(h)
            hx['name'] = '%s·%s' % (h.get('name', sid), rec['stage'])  # 窗口显示带阶段
            jobs.append({'key': key, 'sid': sid, 'stage': rec['stage'],
                         'h': hx, 'ref': refs[key], 'tkid': tkid})
    return jobs, refs


def run_one(job):
    h, ref = job['h'], job['ref']
    if not ref:
        return {'key': job['key'], 'status': 'FAIL_REF'}
    prompt = G.build_prompt(h, has_ref=True, include_appearance=False,
                            composition_boost=False)
    tmps = []
    for att in range(1, MAX_ATT + 1):
        seed = 2001 + att
        for tryi in range(3):
            try:
                res = G.generate(prompt, ref=[G.data_uri(ref)], seed=seed)
                break
            except Exception as e:
                print('  [%s] 网络重试 %s' % (job['key'], str(e)[:80]))
                time.sleep(20)
        else:
            return {'key': job['key'], 'status': 'ERRNET'}
        data = base64.b64decode(res['val']) if res['type'] == 'b64' \
            else urllib.request.urlopen(res['val'], timeout=180).read()
        raw = 'raw/%s_%s_R%d.png' % (job['key'], h['name'], att)
        with open(raw, 'wb') as f:
            f.write(data)
        j = V.judge(raw)
        fr, shd = j['face_rel'], j['shoulder_diff']
        need_eyes = (fr is not None and 0.025 <= fr < 0.030) or \
                    (shd is not None and -0.20 < shd <= -0.15)
        if fr is not None and fr >= 0.025 and shd is not None and shd <= -0.15:
            return {'key': job['key'], 'status': 'PASS_EYES' if need_eyes else 'PASS',
                    'raw': raw, 'seed': seed, 'f': fr, 's': shd}
        print('  [%s] att%d seed%d 脸=%s 肩=%s 重抽' % (job['key'], att, seed, fr, shd))
    return {'key': job['key'], 'status': 'FAIL'}


def main():
    only_refs = '--refs-only' in sys.argv
    jobs, refs = build_jobs()
    json.dump(refs, open(REF_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('阶段形象任务 %d 个 （%d 需新转底稿）' % (len(jobs), len(refs)))
    if only_refs:
        return
    log_exists = os.path.exists('build_log.csv')
    results = []
    for j in jobs:
        r = run_one(j)
        results.append(r)
        row = {'key': r['key'], 'cn': j['h']['name'], 'ver': 'R',
               'ref': os.path.basename(j['ref']), 'age': j['h'].get('age', ''),
               'identity': j['h'].get('identity', ''),
               'seeds': str(r.get('seed', '')), 'final_seed': r.get('seed', ''),
               'face_rel': '%.3f' % r['f'] if r.get('f') is not None else '',
               'shoulder_diff': '%.3f' % r['s'] if r.get('s') is not None else '',
               'need_eyes': '', 'status': r['status'], 'raw': r.get('raw', ''),
               'sec': '0', 'cost_est_fen': '40'}
        with io.open('build_log.csv', 'a', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=[x for x in row])
            w.writerow(row)
        print('%s  %s' % (r['status'], r['key']))
    from collections import Counter
    print('=== 阶段版完成 %d === %s' % (len(results), dict(Counter(r['status'] for r in results))))


if __name__ == '__main__':
    main()
