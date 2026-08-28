# -*- coding: utf-8 -*-
"""三人试跑（T3 光荣形象描述）：每人 2 版（A 基准 / E 带「外观描述_光荣」列的光荣形象描述）。
2026-08-28 用户裁定：维基古画参考图退役（画风不符现代审美），B/C/D 变体废弃。
用法：python run_trial.py [a|e]  —— 只跑指定的一个版本。"""
import csv, io, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import gen_portrait as G

CSV = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
       'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv')  # 2026-08-28 数据源裁定：主源
TRIAL_IDS = ['lord_1_oda', 'lord_1_kinoshita', 'lord_1_sanada_9']
ERAS = [1549, 1554, 1560, 1568, 1575, 1582, 1584, 1598]

# 女城主试跑（2026-08-28 新增）：主源表里这两位数据不全（生年/身份为空），参数人工给定；
# 试跑人工参数覆盖（形象还原优先：与 TK5 底稿对齐——秀吉对齐 517 的青年感）
TRIAL_FEMALE = ['lord_1_azai_1', 'lord_1_bekki_2']
OVERRIDES = {
    'lord_1_azai_1': {'age': 27, 'identity': '公主', 'gender': '女', 'weapon': ''},
    'lord_1_bekki_2': {'age': 25, 'identity': '女城主', 'gender': '女', 'weapon': '刀剑'},
    'lord_1_kinoshita': {'age': 21, 'gender': '男'},
}

# R 版 img2img 参考图（TK5 BUSTUP 解包 PNG，底稿只借长相/造型）
TK5_REF = {
    'lord_1_oda': 'refs_koei/_tk5/195_织田信长.png',
    'lord_1_kinoshita': 'refs_koei/_tk5/517_丰臣秀吉.png',
    'lord_1_sanada_9': 'refs_koei/_tk5/361_真田幸村.png',
    'lord_1_azai_1': 'refs_koei/_tk5/1049_阿市.png',
    'lord_1_bekki_2': 'refs_koei/_tk5/1057_訚千代.png',
}

def load_heroes(ids):
    rows = list(csv.reader(io.open(CSV, encoding='utf-8-sig')))  # 主源 CSV 带 BOM（utf-8-sig 兜底）
    idx = {h: i for i, h in enumerate(rows[0])}
    out = {}
    for r in rows[3:]:
        if len(r) < 2 or r[idx['ID']] not in ids:
            continue
        appeared = [y for y in ERAS if r[idx['Appear_%d' % y]] == '已登场']
        birth = int(r[idx['BirthYear']] or 0)
        # 年龄规则：首末登场年代的中点年龄，钳制 [18,55]；身份取最后登场年代（成熟形态）
        mid = (appeared[0] + appeared[-1]) // 2 if appeared else birth + 30
        age = max(18, min(55, mid - birth))
        last = appeared[-1] if appeared else 1560
        out[r[idx['ID']]] = {
            'id': r[idx['ID']], 'name': r[idx['CNName']], 'jp': r[idx['ScriptName']],
            'age': age, 'era_used': '%d~%d 中点 %d' % (appeared[0], appeared[-1], mid) if appeared else '-',
            'identity': r[idx['Identity_%d' % last]], 'identity_era': last,
            'temper': r[idx['Temper']], 'spirit': r[idx['Spirit']],
            'force': r[idx['ForceValue']] or '60', 'weapon': r[idx['WeaponDesire']],
            'clan': r[idx['ClanID']],
            # 光荣形象描述（主源 CSV「外观描述_光荣」列；兼容旧 AppearanceKoei 命名，见 update_appearance.py）
            'appearance': (r[idx['外观描述_光荣']]
                           if '外观描述_光荣' in idx and idx['外观描述_光荣'] < len(r) else
                           (r[idx['AppearanceKoei']]
                            if 'AppearanceKoei' in idx and idx['AppearanceKoei'] < len(r) else '')),
        }
    return out

def refs_for(sid):
    d = os.path.join('refs', sid)
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d))
            if f.startswith('ref_')]

# 描述列策略（2026-08-28 定稿）：细节补丁制——默认不注入（底稿自带形象、指标更稳），
# 仅"底稿缺失的记忆点"保留：实测只有秀吉（笑 + 茶褐色肩衣为 517 底稿弱项）。
PATCH_DESC = {'lord_1_kinoshita'}

def variants(h, refs):
    refs_img = [G.data_uri(f) for f in refs] if refs else None
    return [
        ('A', G.build_prompt(h, include_appearance=False), None, 1001),  # 基准
        ('E', G.build_prompt(h, include_appearance=False), None, 1002),  # 无描述（旧 E 语义废弃）
        ('R', G.build_prompt(h, has_ref=True, include_appearance=False), refs_img, 2001),  # img2img 底稿重绘
    ]

def job(args):
    h, tag, prompt, ref, seed = args
    name = '%s_%s_%s' % (h['id'], h['name'], tag)   # 中间产物文件名带中文名，人好认；成品 png 仍为纯 StringId（见附录）
    t0 = time.time()
    try:
        res = G.generate(prompt, ref=ref, seed=seed)
        if res['type'] == 'b64':
            data = __import__('base64').b64decode(res['val'])
        else:
            data = urllib.request.urlopen(res['val'], timeout=180).read()
        out = os.path.join('raw', name + '.jpg')
        with open(out, 'wb') as f:
            f.write(data)
        print('  OK  %-40s %5.1fs  %6.0f KB' % (name, time.time() - t0, len(data) / 1024.0))
        return {'name': name, 'file': out, 'ok': True, 'prompt': prompt,
                'ref': (refs_used(ref) if ref else None), 'sec': round(time.time() - t0, 1)}
    except Exception as e:
        msg = str(e)
        try:
            msg = e.read().decode()[:300]
        except Exception:
            pass
        print('  ERR %-28s %s' % (name, msg))
        return {'name': name, 'ok': False, 'error': msg, 'prompt': prompt}

def refs_used(ref):
    return ['(base64 %d KB)' % (len(x) / 1024) for x in (ref if isinstance(ref, list) else [ref])]

def main():
    only = sys.argv[1].lower() if len(sys.argv) > 1 else ''
    female = only in ('f', 'w', 'fr', 'wr')
    r_mode = only in ('r', 'fr')
    os.makedirs('raw', exist_ok=True)
    heroes = load_heroes(set(TRIAL_FEMALE if female else TRIAL_IDS))
    b0 = G.billing()
    print('账单起点: %s' % b0)
    tasks = []
    ids = TRIAL_FEMALE if female else TRIAL_IDS
    for sid in ids:
        h = heroes[sid]
        if female:
            h.update(OVERRIDES.get(sid, {}))
        else:
            h.update(OVERRIDES.get(sid, {}))
        rf = [TK5_REF[sid]] if r_mode and sid in TK5_REF else refs_for(sid)
        print('%s %s  %d岁(%s)  身份=%s(%d年)  参考图%d张  %s'
              % (sid, h['name'], h['age'], h.get('era_used', '-'), h['identity'],
                 h['identity_era'] if not female else 0, len(rf), '女' if h.get('gender') == '女' else ''))
        for tag, p, ref, seed in variants(h, rf):
            # 版本过滤：f/w = 女性 E 版；r = 男性 R 版；fr = 女性 R 版；其余 = 字母直配
            allowed = {'f': {'E'}, 'w': {'E'}, 'r': {'R'}, 'fr': {'R'}, 'wr': {'R'}}.get(only)
            if allowed is None and only:
                allowed = {only.upper()}
            if allowed and tag not in allowed:
                continue
            # 细节补丁注入（仅 PATCH_DESC 内角色；其余无描述——底稿自带形象）
            if sid in PATCH_DESC and h.get('appearance'):
                p = G.build_prompt(h, has_ref=(tag == 'R'), include_appearance=True)
            tasks.append((h, tag, p, ref, seed))
    print('共 %d 张，3 路并发' % len(tasks))
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(job, tasks))
    time.sleep(60)
    b1 = G.billing()
    ok = sum(1 for r in results if r['ok'])
    print('成功 %d/%d   账单 %s -> %s' % (ok, len(results), b0, b1))
    if b0 is not None and b1 is not None and ok:
        print('单价 = %.4f / 张' % ((b1 - b0) / ok))
    with io.open('trial_log.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps({'heroes': heroes, 'results': results,
                            'billing_before': b0, 'billing_after': b1},
                           ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
