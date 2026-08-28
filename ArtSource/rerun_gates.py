# -*- coding: utf-8 -*-
"""T1b：重跑 3 张超限图（信长 0.73 / 訚千代 0.95 / 秀吉 1.93），换 seed ≤3 次进带子。

判定循环 = 生成 → matte → 脸闸(RIGHT≥0.030) + 肩带闸(∈[1.05,1.65]) → 任一不过换 seed。
与上一轮 R 版完全同参数（同底稿/同 prompt 语义），只改 seed；通过后留底并记 gate_rerun_log.json。
用法：python rerun_gates.py
"""
import io, os, json, sys, time, urllib.request, base64

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import gen_portrait as G
import matte_rembg as M
import gate as GT
import run_trial as RT

SIDS = [a for a in sys.argv[1:]] or ['lord_1_oda', 'lord_1_bekki_2', 'lord_1_kinoshita']
MAX_ATT = 3
# 底稿覆盖：NOBU_MIRROR=1 → 信长换镜像底稿；NOBU_REF='1154' → 换 1154 青春版底稿
if os.environ.get('NOBU_REF') == '1154':
    REF_OVERRIDE = {'lord_1_oda': 'refs_koei/_tk5/1154_织田信长_朝左.png'}
elif os.environ.get('NOBU_MIRROR'):
    REF_OVERRIDE = {'lord_1_oda': 'refs_koei/_tk5/195_织田信长_朝右.png'}
else:
    REF_OVERRIDE = {}

heroes = RT.load_heroes(set(SIDS) | set(RT.TRIAL_FEMALE) | set(RT.TRIAL_IDS))
# 与 run_trial.main 完全一致：OVERRIDES 先套（訚千代数据不全人工补参；秀吉对齐底稿青年感）
for sid in SIDS:
    heroes[sid].update(RT.OVERRIDES.get(sid, {}))

log = []
os.makedirs('raw', exist_ok=True)
os.makedirs('matte_rembg', exist_ok=True)
b0 = G.billing()
print('账单起点: %s' % b0)

for sid in SIDS:
    h = heroes[sid]
    ref = G.data_uri(REF_OVERRIDE.get(sid) or RT.TK5_REF[sid])  # 覆盖或默认底稿
    prompt = G.build_prompt(h, has_ref=True,
                            include_appearance=(sid in RT.PATCH_DESC))  # 细节补丁制：仅秀吉
    entry = {'sid': sid, 'name': h['name'], 'age': h['age'], 'identity': h['identity'],
             'attempts': []}
    print('\n%s %s  %d岁 %s  换 seed ≤%d 次'
          % (sid, h['name'], h['age'], h['identity'], MAX_ATT))
    for att in range(1, MAX_ATT + 1):
        seed = 2001 + att
        t0 = time.time()
        try:
            res = G.generate(prompt, ref=[ref], seed=seed)
        except Exception as e:
            msg = str(e)
            try:
                msg = e.read().decode()[:300]
            except Exception:
                pass
            entry['attempts'].append({'attempt': att, 'seed': seed, 'error': msg[:300]})
            print('  ERR att%d seed%d: %s' % (att, seed, msg))
            break
        data = base64.b64decode(res['val']) if res['type'] == 'b64' \
            else urllib.request.urlopen(res['val'], timeout=180).read()
        raw = 'raw/%s_%s_R%d.jpg' % (sid, h['name'], att)
        with open(raw, 'wb') as f:
            f.write(data)
        png = 'matte_rembg/%s_%s_R%d.png' % (sid, h['name'], att)
        try:
            M.place(M.matte(raw), png)
        except Exception as e:
            entry['attempts'].append({'attempt': att, 'seed': seed, 'raw': raw,
                                      'matte': 'ERR ' + str(e)})
            print('  att%d seed%d: matte ERR %s' % (att, seed, str(e)))
            continue
        fok, fr = GT.face_gate(raw)
        sok, shd = GT.shoulder_gate(raw)   # 2026-08-28 闸门修复：解剖法（近景肩在画面左）
        ok = fok and sok
        rec = {'attempt': att, 'seed': seed, 'raw': raw, 'matte': png,
               'face_rel': fr, 'shoulder': shd, 'pass': bool(ok),
               'sec': round(time.time() - t0, 1)}
        entry['attempts'].append(rec)
        print('  att%d seed%d  %4.1fs  脸=%s(%.3f) 肩轴=%s(%.3f)  => %s'
              % (att, seed, rec['sec'], 'OK' if fok else 'FAIL', fr,
                 shd, 'PASS' if ok else 'retry'))
        if ok:
            break
    entry['final'] = next((a for a in reversed(entry['attempts']) if a.get('pass')), None)
    entry['status'] = 'PASS' if entry['final'] else 'FAIL(>%d次, 停上报)' % MAX_ATT
    log.append(entry)
    print('--> %s  %s' % (sid, entry['status']))

time.sleep(60)
b1 = G.billing()
ok_n = sum(1 for e in log if e['status'] == 'PASS')
print('\n成功 %d/3   账单 %s -> %s' % (ok_n, b0, b1))
with io.open('gate_rerun_log.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps(log, ensure_ascii=False, indent=2))

# 质检拼图：每人全部尝试（深底/浅底各一张），最终版单独再拼一张大图
import PIL.Image as PILImage
for e in log:
    pngs = [a['matte'] for a in e['attempts'] if isinstance(a.get('matte'), str)]
    head = '%s_%s_rerun' % (e['sid'], e['name'])
    if pngs:
        M.qc_sheet(pngs, 'preview/%s_dark.jpg' % head, (28, 28, 34))
        M.qc_sheet(pngs, 'preview/%s_light.jpg' % head, (232, 230, 224))
finals = [e['final']['matte'] for e in log if e['final']]
if finals:
    M.qc_sheet(finals, 'preview/rerun_trio_dark.jpg', (28, 28, 34))
    M.qc_sheet(finals, 'preview/rerun_trio_light.jpg', (232, 230, 224))
print('done -> preview/*_rerun_*.jpg / rerun_trio_*.jpg')
