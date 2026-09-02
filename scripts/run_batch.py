# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""全量立绘跑批驱动（2026-08-29 用户裁定：跑全部织丰太阁人物）。

范围：TaikouHero.csv 全部 1047 名英雄 + 身份模板 19 张（15 有底稿 R 版 + 4 无底稿 A 版）。
分档：
  R 版（有 TK5 底图）= gpt-image-2 /images/edits + images[]（¥0.40/张，种子 2002 起）
  A 版（无底图）= gpt-image-2 /images/generations（2026-08-29 探测可用，￥0.33/张，种子 1001 起）
每张：出图 → 数字双闸（脸 RIGHT ≥0.030 / 肩轴 ≤ -0.15，任一 None=失败）→ 换 seed ≤3 →
      过闸存 raw + 写 build_log.csv 一行；3 次不过 = FAIL(- 上报)。
断点续跑：启动时读 build_log.csv，status 为 PASS / PASS_EYES 的 key 跳过。
用法：python run_batch.py [--limit N] [--only key1,key2]
"""
import argparse, base64, csv, io, json, os, re, sys, threading, time, urllib.error, urllib.request, glob
from concurrent.futures import ThreadPoolExecutor

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import gen_portrait as G
import run_trial as RT
import verify_pose as V
import identity_refs as IR

LOG_CSV = 'build_log.csv'
MAX_ATT = 2                 # 2026-08-29 用户裁定：重试 ≤2 次（不跑第 3 个 seed）
PATCH_FORCE = set()         # 2026-08-30：注意点注入的 key（rerun 侧 RB.PATCH_FORCE 写）→ build_prompt 带 appearance
NEAR_FACE = 0.025          # 贴线带：>=0.025 且 <0.030 过闸但标 need_eyes（人眼终审，§6）
NEAR_SH = 0.05             # 肩轴贴线带：与 -0.15 差 <0.05 过闸标 need_eyes
FIELDS = ['key', 'cn', 'ver', 'ref', 'age', 'identity', 'seeds', 'final_seed',
          'face_rel', 'shoulder_diff', 'need_eyes', 'status', 'raw', 'sec', 'cost_est_fen']
_lock = threading.Lock()
_prev_billing = [None, None]   # [n_jobs_at_check, usage] 每 50 张读一次


def load_gender():
    rows = list(csv.reader(io.open(RT.CSV, encoding='utf-8-sig')))
    idx = {h: i for i, h in enumerate(rows[0])}
    if 'Gender' not in idx:
        return {}
    return {r[idx['ID']]: ('女' if r[idx['Gender']] == '0' else '男')
            for r in rows[3:] if len(r) > idx['ID'] and r[idx['ID']]}


def build_hero_jobs(manifest):
    heroes = RT.load_heroes(set(manifest.keys()))
    genders = load_gender()
    jobs, skip = [], []
    for sid, m in manifest.items():
        if sid not in heroes:
            skip.append(sid)
            continue
        h = dict(heroes[sid])
        h.update(RT.OVERRIDES.get(sid, {}))
        h['gender'] = genders.get(sid, '男')
        if m is None:
            jobs.append((sid, h, None, 'A'))
            continue
        if m.get('identity_tpl'):
            continue  # 无卡模板 NPC 由身份模板图覆盖
        ref = os.path.join('refs_koei/_tk5', m['ref'])
        if not os.path.exists(ref):
            print('!! 底图缺失 %s -> %s 降 A 版' % (sid, m['ref']))
            jobs.append((sid, h, None, 'A'))
            continue
        jobs.append((sid, h, ref, 'R'))
    if skip:
        print('!! CSV 无此英雄跳过: %s' % skip[:10])
    return jobs


def build_ident_jobs():
    """身份模板：按现存文件匹配（identity_refs.py 表内 _朝左 旧名已过期为 _朝右/_朝正，
    走 编号_姓名 前缀匹配 + 朝右优先）。同名共享一张（2026-08-28 裁定：一个类型一张）。"""
    files = [os.path.basename(p) for p in glob.glob('refs_koei/_tk5/identity/*_朝*.png')]
    jobs, seen = [], set()
    for ident, fn in IR.IDENTITY_REF.items():
        if fn is None:
            # 大名/国主/城主/茶人：无通用底图 → A 版（身份装束在 prompt 里成型）
            jobs.append(('tpl_%s' % ident, {'id': 'tpl_%s' % ident, 'name': ident, 'jp': '',
                                            'age': 30, 'identity': ident, 'temper': '冷静',
                                            'spirit': '普通', 'force': '60', 'weapon': '',
                                            'gender': '男', 'appearance': ''}, None, 'A'))
            continue
        stem = re.sub(r'_[^_]*$', '', fn)
        cand = sorted([b for b in files if b.startswith(stem + '_')],
                      key=lambda b: 0 if '_朝右' in b else 1)
        if not cand:
            print('!! 身份底稿缺失 %s (%s)' % (ident, fn))
            continue
        if cand[0] not in seen:
            seen.add(cand[0])
            pid = re.match(r'(\d+)_', cand[0]).group(1)
            label = ident  # 首个共享类作代表
            jobs.append(('tpl_%s' % pid, {'id': 'tpl_%s' % pid, 'name': label, 'jp': '',
                                          'age': 30, 'identity': label, 'temper': '冷静',
                                          'spirit': '普通', 'force': '60', 'weapon': '',
                                          'gender': '男', 'appearance': ''},
                         os.path.join('refs_koei/_tk5/identity', cand[0]), 'R'))
    return jobs


def gen_R(prompt, ref_path, seed):
    res = G.generate(prompt, ref=[G.data_uri(ref_path)], seed=seed)
    if res['type'] == 'b64':
        return base64.b64decode(res['val'])
    return urllib.request.urlopen(res['val'], timeout=180).read()


def gen_A(prompt, seed):
    body = {'model': G.MODEL, 'prompt': prompt, 'size': '1024x1536',
            'output_format': 'png', 'quality': 'medium', 'seed': seed}
    req = urllib.request.Request(G.BASE.rstrip('/') + '/images/generations',
                                 data=json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': 'Bearer ' + G.KEY})
    d = json.load(urllib.request.urlopen(req, timeout=300))['data'][0]
    return base64.b64decode(d['b64_json'])


def gate(raw):
    r = V.judge(raw)
    fr, shd = r['face_rel'], r['shoulder_diff']
    if fr is None and shd is None:
        return None, None, ['测量失败(双漏检)']
    notes = []
    if fr is None:
        notes.append('测量失败(脸)')
    elif fr >= 0.030:
        pass
    elif fr >= NEAR_FACE:
        notes.append('贴线=%.3f' % fr)
    if shd is None:
        notes.append('测量失败(肩)')
    elif shd <= -0.15:
        pass
    elif shd <= -0.15 + NEAR_SH:
        notes.append('贴线=%.3f' % shd)
    fok = fr is not None and fr >= NEAR_FACE
    sok = shd is not None and shd <= -0.15 + NEAR_SH
    return (fok and sok), (fr, shd), notes


def pack_row(key, h, ver, ref_name, seeds, final_seed, fr, shd, notes, status, raw, sec, att_cost):
    return {k: '' for k in FIELDS} | {
        'key': key, 'cn': h.get('name', key), 'ver': ver, 'ref': ref_name or '',
        'age': h.get('age', ''), 'identity': h.get('identity', ''),
        'seeds': '/'.join(map(str, seeds)), 'final_seed': final_seed or '',
        'face_rel': fr if fr is None else '%.3f' % fr,
        'shoulder_diff': shd if shd is None else '%.3f' % shd,
        'need_eyes': '1' if (notes and any('贴线' in n or '测量失败' in n for n in notes)) else '',
        'status': status, 'raw': raw, 'sec': '%.1f' % sec,
        'cost_est_fen': str(int(att_cost * len(seeds))),
    }


def write_rows(rows):
    new = not os.path.exists(LOG_CSV)
    with _lock:
        with io.open(LOG_CSV, 'a', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            for r in rows:
                w.writerow(r)


def job_run(job):
    key, h, ref, ver = job
    ref_name = os.path.basename(ref) if ref else ''
    seeds, notes_all = [], []
    att_cost = 40 if ver == 'R' else 33
    frs, shds = [], []
    t0 = time.time()
    os.makedirs('raw', exist_ok=True)
    final_raw = ''
    for att in range(1, MAX_ATT + 1):
        seed = (2001 if ver == 'R' else 1000) + att
        seeds.append(seed)
        prompt = G.build_prompt(h, has_ref=(ver == 'R'),
                                include_appearance=(key in RT.PATCH_DESC or key in PATCH_FORCE),
                                composition_boost=False)
        data = None
        for tryi in range(3):
            try:
                data = gen_R(prompt, ref, seed) if ver == 'R' else gen_A(prompt, seed)
                break
            except Exception as e:
                msg = str(e)
                try:
                    msg = e.read().decode()[:150]
                except Exception:
                    pass
                print('  [%s] att%d seed%d 网络重试 %d/3: %s' % (key, att, seed, tryi + 1, msg[:120]))
                if tryi == 2:
                    notes_all.append('网络失败: ' + msg[:80])
                    break
                time.sleep(25)
        if data is None:
            continue
        raw = 'raw/%s_%s_%s%d.png' % (key, h['name'], ver, att)
        # 🔴 2026-08-30 用户建议：新批图「文件名自描述」——tkid 拼进文件名（看图知卡号）。
        #   历史旧 raw 保持原名不动（picks/台账引用旧名），此处仅新批生效；读端双轨兼容。
        if ref:
            m = re.match(r'^(\d+)_', os.path.basename(ref))
            if m:
                raw = 'raw/%s_%s_%s_%s%d.png' % (m.group(1), key, h['name'], ver, att)
        with open(raw, 'wb') as f:
            f.write(data)
        ok, frshd, ns = gate(raw)
        if frshd is not None:
            frs.append(frshd[0]); shds.append(frshd[1])
        notes_all += ns
        if ok:
            final_raw, seed_used = raw, seed
            if ns:
                status = 'PASS_EYES'
            else:
                status = 'PASS'
            write_rows([pack_row(key, h, ver, ref_name, seeds, seed_used,
                                 frshd[0], frshd[1], ns, status, raw, time.time() - t0, att_cost)])
            return {'key': key, 'status': status, 'seed': seed}
        else:
            print('  [%s] att%d seed%d => 脸=%s 肩=%s 重抽' % (key, att, seed,
                                                              frshd[0] if frshd else 'None',
                                                              frshd[1] if frshd else 'None'))
    write_rows([pack_row(key, h, ver, ref_name, seeds, None,
                         frs[-1] if frs else None, shds[-1] if shds else None,
                         notes_all, 'FAIL', final_raw, time.time() - t0, att_cost)])
    return {'key': key, 'status': 'FAIL', 'notes': notes_all}


def existing_done():
    if not os.path.exists(LOG_CSV):
        return set()
    done = set()
    with io.open(LOG_CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r.get('status') in ('PASS', 'PASS_EYES'):
                done.add(r['key'])
    return done


def report_billing(n_ok, total):
    with _lock:
        if _prev_billing[0] is None or n_ok - _prev_billing[0] >= 50:
            u = G.billing()
            if u is not None:
                d = '' if _prev_billing[1] is None else '  增量 %.2f' % (u - _prev_billing[1])
                print('[%5.1f%%] 完成 %d/%d | 账单 %s%s' % (
                    n_ok * 100.0 / total, n_ok, total, '%.2f' % u if u else 'N/A', d), flush=True)
                _prev_billing[0], _prev_billing[1] = n_ok, u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--only', default='')
    args = ap.parse_args()

    manifest = json.load(open('refs_koei/_tk5/hero_refs_manifest.json', encoding='utf-8'))
    all_jobs = build_hero_jobs(manifest) + build_ident_jobs()
    done = existing_done()
    skipped = sum(1 for j in all_jobs if j[0] in done)
    jobs = [j for j in all_jobs if j[0] not in done]
    if args.only:
        keep = set(args.only.split(','))
        jobs = [j for j in jobs if j[0] in keep]
    if args.limit:
        jobs = jobs[:args.limit]
    r_n = sum(1 for j in jobs if j[3] == 'R')
    print('任务: %d 张（R=%d / A=%d）  已 PASS 跳过: %d  总任务: %d 张'
          % (len(jobs), r_n, len(jobs) - r_n, skipped, len(all_jobs)))
    print('账单起点: %s' % G.billing())
    report_billing(0, max(len(jobs), 1))
    done_n = [0]
    with ThreadPoolExecutor(max_workers=3) as ex:
        for res in ex.map(job_run, jobs):
            done_n[0] += 1
            if res['status'] == 'FAIL':
                print('!! FAIL: %s  %s' % (res['key'], res.get('notes', '')))
            if done_n[0] % 50 == 0:
                report_billing(done_n[0], len(jobs))
    time.sleep(60)
    print('=== 完成 === 完成 %d/%d | 最终账单: %s' % (done_n[0], len(jobs), G.billing()))


if __name__ == '__main__':
    main()
