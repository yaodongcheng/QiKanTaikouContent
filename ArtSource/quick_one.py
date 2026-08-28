# -*- coding: utf-8 -*-
"""单张快速出图（跳过 matte/gate/账单冷却，~45s 出图）。
用法：python quick_one.py <sid> [sid...]          # 默认 lord_1_oda
      QUICK_SEED=2005 python quick_one.py ...      # 换 seed
      QUICK_BOOST=1 python quick_one.py ...        # 构图铁律强化（开头+结尾+REF对抗句）
      NOBU_MIRROR=1 / NOBU_REF=1154 ...            # 信长底稿覆盖（镜像/青春版）
有 TK5 底稿 → R 版(img2img，带 REF_HINT)；无底稿 → A 版(text2img，自动去掉 REF_HINT 段)。
"""
import base64, io, os, sys, time, urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import gen_portrait as G
import run_trial as RT


def _ref_override():
    """与 rerun_gates 同规则的底稿覆盖（信长专属；文件名 _朝左/右/正 = 实测脸朝向）。"""
    if os.environ.get('NOBU_REF') == '1154':
        return {'lord_1_oda': 'refs_koei/_tk5/1154_织田信长_朝左.png'}
    if os.environ.get('NOBU_MIRROR'):
        return {'lord_1_oda': 'refs_koei/_tk5/195_织田信长_朝右.png'}
    return {}


def main():
    sids = sys.argv[1:] or ['lord_1_oda']
    seed = int(os.environ.get('QUICK_SEED', '2002'))
    boost = os.environ.get('QUICK_BOOST', '0') in ('1', 'true', 'True')
    ref_ov = _ref_override()
    heroes = RT.load_heroes(set(RT.TRIAL_IDS) | set(RT.TRIAL_FEMALE) | set(sids))
    os.makedirs('raw', exist_ok=True)
    for sid in sids:
        h = heroes[sid]
        h.update(RT.OVERRIDES.get(sid, {}))
        ref = ref_ov.get(sid) or RT.TK5_REF.get(sid) \
            or (RT.refs_for(sid)[0] if RT.refs_for(sid) else None)
        if ref:
            prompt = G.build_prompt(h, has_ref=True,
                                    include_appearance=(sid in RT.PATCH_DESC),
                                    composition_boost=boost)
        else:
            prompt = G.build_prompt(h, has_ref=False,
                                    include_appearance=(sid in RT.PATCH_DESC),
                                    composition_boost=boost)
        print('=== %s %s  版本=%s  参考图=%s%s' % (sid, h['name'],
              'R' if ref else 'A', ref or '无', '  [构图boost ON]' if boost else ''))
        print('=== PROMPT ===')
        print(prompt)
        print('=== 生成中... ===')
        t0 = time.time()
        res = G.generate(prompt, ref=[G.data_uri(ref)] if ref else None, seed=seed)
        data = base64.b64decode(res['val']) if res['type'] == 'b64' \
            else urllib.request.urlopen(res['val'], timeout=180).read()
        out = os.path.join('raw', 'quick_%s_%s.jpg' % (sid, h['name']))
        with open(out, 'wb') as f:
            f.write(data)
        print('OK  %.1fs  %5.0f KB  ->  %s' % (time.time() - t0, len(data) / 1024.0, out))
        seed += 1


if __name__ == '__main__':
    main()
