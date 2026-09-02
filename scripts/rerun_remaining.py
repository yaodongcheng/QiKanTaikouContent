# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""补跑缺口卡 → gpt-image-2（2026-08-29 用户裁定：全 BUSTUP 补齐 + 重试 ≤2 次）。

缺口（250）= 块1 旧83清单 + 块2 新缺口158（无卡池/零散）+ 块3 阶段版FAIL 9。
卡 → 身份 prompt：CSV 反查 tkid → StringId 行 → h（列抽取 + RT.OVERRIDES；模板/英雄统一）。
复用 run_batch 的 job_run/gate/pack_row/write_rows/existing_done（MAX_ATT=2）。
key：普通卡 = tk{tkid}；阶段版 = {sid}#{stage}（对齐 picks.json/pick_gui 协议）。
用法：python rerun_remaining.py [--limit N] [--only id1,id2] [--list]
"""
import argparse, csv, glob, io, json, os, re, sys
sys.path.insert(0, os.getcwd())
import run_batch as RB
import run_trial as RT

RB.MAX_ATT = 2   # 2026-08-29 用户裁定：重试 ≤2，不跑第 3 个 seed

SRC = r'E:\taikou5\TaikouImage\BUSTUP'
REFS = 'refs_koei/_tk5'
CSV = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
       'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv')


def ref_of_tk(tk):
    fs = [f for f in glob.glob(os.path.join(REFS, '%d_*.png' % tk))
          if not f.endswith('_朝左.png')]
    fs.sort(key=lambda f: (0 if f.endswith('_朝右.png') else 1))
    return fs[0] if fs else None


def build_h(sid, d):
    def g(*names, default=''):
        for n in names:
            v = d.get(n)
            if v is not None and str(v).strip():
                return str(v).strip()
        return default
    h = {'id': sid, 'name': g('CNName', 'ID', default=sid), 'jp': g('ScriptName'),
         'age': g('Age', 'BirthYear') or '30',
         'identity': g('Identity_1560', 'Identity_1554', 'Identity_1549', 'ScriptName', 'CNName'),
         'temper': g('Temper', default='冷静'), 'spirit': g('Spirit', default='普通'),
         'force': g('ForceValue', default='60'), 'weapon': g('WeaponDesire'),
         'gender': ('女' if g('Gender', default='') == '0' else '男'),
         'appearance': g('外观描述_光荣', 'AppearanceKoei')}
    h.update(RT.OVERRIDES.get(sid, {}))
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--only', default='')
    ap.add_argument('--list', action='store_true', help='只列出 jobs 和预算，不生成')
    ap.add_argument('--redraw-only', action='store_true',
                    help='只跑「待重生成」标记（_review/picktkid.json 的 redraw 字段）')
    args = ap.parse_args()

    # —— 缺口集 ——
    bustup = {}
    for d in os.listdir(SRC):
        if '_' in d:
            p, n = d.split('_', 1)
            if p.isdigit():
                bustup[int(p)] = n
    build = {}
    with io.open(RB.LOG_CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            ref = (r.get('ref') or '').split('/')[-1]
            m = re.match(r'^(\d+)_', ref)
            build[r.get('key', '')] = (int(m.group(1)) if m else None, r.get('status', ''))
    picks = set(json.load(open('_review/picks.json', encoding='utf-8')).keys())
    auth = {tk for k, (tk, st) in build.items() if k in picks and tk}
    passed = {tk for tk, st in build.values() if tk and st in ('PASS', 'PASS_EYES')}
    stage_fail = sorted([k for k, (tk, st) in build.items()
                         if '#' in k and st == 'FAIL' and k not in picks])

    # tsv 旧清单（块1）
    old83 = set()
    if os.path.exists('_rerun_plan.tsv'):
        with io.open('_rerun_plan.tsv', encoding='utf-8') as f:
            for line in f:
                t = line.strip()
                if t and t.split('\t')[0].isdigit():
                    old83.add(int(t.split('\t')[0]))
    gap_all = sorted((set(bustup) - passed - auth))
    gap_keys = [('tk%d' % t, t) for t in old83]
    gap_keys += [('tk%d' % t, t) for t in sorted(set(gap_all) - old83
                                               - {build[k][0] for k in stage_fail})]
    # 阶段版 FAIL：key 用 {sid}#{stage}（与 picks 协议一致）
    hmap = {}
    with io.open(CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            hmap[r['ID']] = r
    rows_h = hmap
    jobs = []
    job_sid = {}
    for key, tk in gap_keys:
        ref = ref_of_tk(tk)
        if not ref:
            print('!! 底稿缺失 tk%d -- skip' % tk)
            continue
        # StringId 行：TK5 列含该 tkid 的行（主行 = 第一个）
        sid = None
        for r in rows_h.values():
            if re.search(r'(^|[|,，;])%s([|,，;]|$)' % tk, r.get('TK5编号', '')):
                sid = r['ID']
                break
        if not sid:
            print('!! tk%d 未在 CSV 栖身 -- skip' % tk)
            continue
        job_sid['tk%d' % tk] = sid
        jobs.append((key, build_h(sid, rows_h[sid]), ref, 'R'))
    for k in stage_fail:
        sid, stage = k.split('#', 1)
        tk = build[k][0]
        ref = ref_of_tk(tk)
        if not ref:
            continue
        h = build_h(sid, rows_h.get(sid, {}))
        h['name'] = '%s·%s' % (h.get('name', sid), stage)
        job_sid[k] = sid
        jobs.append((k, h, ref, 'R'))
    if args.only:
        keep = set(args.only.split(','))
        jobs = [j for j in jobs if j[0] in keep or j[2].split('\\')[-1].split('_')[0] in keep]
    if args.limit:
        jobs = jobs[:args.limit]
    # 2026-08-30：重生成标记/意见唯一源 = _review/picktkid.json（键=tkid，值 redraw=意见）
    #   → 映射任务：阶段卡（build_log 有 sid#stage）用原 key；池/单卡用 tk{tid}
    notes = {}
    if os.path.exists('_review/picktkid.json'):
        _m = json.load(open('_review/picktkid.json', encoding='utf-8'))
        if isinstance(_m, dict):
            for t, v in _m.items():
                if isinstance(v, dict) and 'redraw' in v:
                    notes[str(t)] = (v.get('redraw') or '')
    inv_tk = {str(tk): k for k, (tk, st) in build.items() if tk}
    if notes:
        adj = {}
        for tid, note in notes.items():
            kk = inv_tk.get(tid)
            target = kk if (kk and '#' in kk) else ('tk' + tid)
            if target in job_sid or target in set(j[0] for j in jobs):
                adj[target] = note
        for j in jobs:
            if j[0] in adj and adj[j[0]]:
                h = j[1]
                h['appearance'] = ((h.get('appearance') or '') + '；' if h.get('appearance') else '') + adj[j[0]]
        RB.PATCH_FORCE = set(adj)
        print('注意点映射 %d 个任务: %s' % (len(adj), list(adj)[:10]))
    if args.redraw_only:
        # 🔴 2026-08-30 重写：以标记为准（无视缺口/已出图）——已出图的也能强制重跑（如阿中「更老」）
        if not notes:
            print('!! --redraw-only 但 picktkid.json 无 redraw 标记')
            return
        rjobs, seen = [], set()

        def add_job(key, tk):
            if key in seen or not tk:
                return
            ref = ref_of_tk(tk)
            if not ref:
                print('!! 底稿缺失 %s (tk%d) -- skip' % (key, tk))
                return
            sid = None
            for r in rows_h.values():
                if re.search(r'(^|[|,，;])%d([|,，;]|$)' % tk, r.get('TK5编号', '')):
                    sid = r['ID']
                    break
            if not sid:
                print('!! tk%d 未在 CSV 栖身 -- skip' % tk)
                return
            h = build_h(sid, rows_h[sid])
            if '#' in key and not key[2:].isdigit():
                pass
            rjobs.append((key, h, ref, 'R'))
            seen.add(key)

        for tid, note in notes.items():
            kk = inv_tk.get(tid)
            if kk and '#' in kk:
                add_job(kk, int(tid))
            else:
                add_job('tk' + tid, int(tid))
        jobs = rjobs
        print('--redraw-only: %d 张' % len(jobs))
    # 🔴 2026-08-30：重生成模式（--redraw-only）：以标记为准，全部强制重跑（忽略已有图/缺口）；
    #   普通补跑才跳过已 PASS。
    if not args.redraw_only:
        done = RB.existing_done()
        jobs = [j for j in jobs if j[0] not in done]
        print('扣除已 PASS: 实际 %d 张' % len(jobs))
    else:
        print('重生成模式：全部强制重跑（%d 张）' % len(jobs))
    print('补跑 jobs: %d 张（R 版 gpt-image-2，重试≤2，¥0.40/张）' % len(jobs))
    if args.list:
        for j in jobs:
            print(j[0], j[2].split('\\')[-1])
        return
    print('账单起点: %s' % RT.G.billing())
    n = 0
    with RB.ThreadPoolExecutor(max_workers=3) as ex:
        for res in ex.map(RB.job_run, jobs):
            n += 1
            if res['status'] == 'FAIL':
                print('!! FAIL: %s' % res['key'])
            if n % 25 == 0:
                print('[%d/%d] 账单 %s' % (n, len(jobs), RT.G.billing()), flush=True)
    print('=== 完成 %d/%d | 最终账单: %s' % (n, len(jobs), RT.G.billing()))


if __name__ == '__main__':
    main()
