# -*- coding: utf-8 -*-
"""单张快速出图（跳过 matte/gate/账单冷却，~45s 出图）。
用法：
  python quick_one.py <sid> [sid...]        # 英雄：lord_1_oda 等
  python quick_one.py 1112                  # 身份底稿：数字 = identity/{编号}_*.png
  python quick_one.py --all                 # refs_koei 全部底稿各一张（27 张，~25 分钟）
  QUICK_SEED=2005 ...        # 换 seed
  QUICK_BOOST=1 ...          # 构图 boost（默认关：无净效果，仅 A/B）
  朝右选择规则（2026-08-28）：底稿名含 _朝左 → 优先同名 _朝右 兄弟文件；无兄弟 → PIL 运行时镜像；
  _朝右/_朝正 → 原样使用。身份底稿探针人物层：30 岁/冷静/普通/60 力（R 版裁身份服饰，仅兜底用）。
"""
import base64, glob, io, os, sys, time, urllib.request
from PIL import Image

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import gen_portrait as G
import run_trial as RT
import identity_refs as IR

# 主底稿 → 英雄 sid（唯一事实：仅有 10 个文件，直接映射；其余走身份探针）
FILE_HERO = {
    '195_织田信长_朝左.png': 'lord_1_oda', '195_织田信长_朝右.png': 'lord_1_oda',
    '1154_织田信长_朝左.png': 'lord_1_oda',
    '517_丰臣秀吉_朝左.png': 'lord_1_kinoshita', '517_丰臣秀吉_朝右.png': 'lord_1_kinoshita',
    '361_真田幸村_朝左.png': 'lord_1_sanada_9', '1162_真田幸村_朝右.png': 'lord_1_sanada_9',
    '1049_阿市_朝左.png': 'lord_1_azai_1',
    '1057_訚千代_朝左.png': 'lord_1_bekki_2', '1057_訚千代_朝右.png': 'lord_1_bekki_2',
}


def rightify(path):
    """朝右替身规则：_朝左 → 同名 _朝右 兄弟（twin）；无兄弟 → 运行时镜像（mirror）；其余原样。"""
    d, b = os.path.dirname(path), os.path.basename(path)
    if '_朝左' in b:
        twin = os.path.join(d, b.replace('_朝左', '_朝右'))
        if os.path.exists(twin):
            return twin, 'twin'
        return path, 'mirror'
    return path, 'as-is'


def data_uri_mirror(path):
    im = Image.open(path).convert('RGB').transpose(Image.FLIP_LEFT_RIGHT)
    buf = io.BytesIO()
    im.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def _ident_label(fn):
    """身份底稿 → 身份名（identity_refs 单源反查；查不到兜底 '无效'）。"""
    for ident in IR.IDENTITY_REF:
        if IR.IDENTITY_REF[ident] == fn:
            return ident
    return '无效'


def probe_h(path):
    b = os.path.basename(path)
    stem = b[:-4]  # 去 .png
    parts = stem.split('_')
    return {'id': 'probe_' + parts[0], 'name': parts[1].split('朝')[0],
            'age': 30, 'identity': _ident_label(b), 'temper': '冷静',
            'spirit': '普通', 'force': '60', 'gender': '男'}


def generate_one(tag, h, ref_path, seed, boost, outdir='raw'):
    ref_ok, mode = rightify(ref_path)
    # 输出名 = 实际参考图方向（不是源底稿名）：twin/镜像 → _朝右，_朝正 原样——
    # 2026-08-28 用户指正：raw 里标着"朝左"的文件名会谎报实际用的朝右参考。
    rname = os.path.basename(ref_ok)[:-4]
    if mode == 'mirror':
        rname = rname.replace('_朝左', '_朝右')
    out = os.path.join(outdir, 'probe_%s.jpg' % rname)
    if mode == 'mirror':
        ref_uri = data_uri_mirror(ref_ok)
    else:
        ref_uri = G.data_uri(ref_ok)
    prompt = G.build_prompt(h, has_ref=True,
                            include_appearance=False, composition_boost=boost)
    print('=== %s  人物=%s  底稿=%s[%s]  输出=%s' % (tag, h['name'], os.path.basename(ref_ok), mode,
                                                   os.path.basename(out)))
    t0 = time.time()
    res = G.generate(prompt, ref=[ref_uri], seed=seed)
    data = base64.b64decode(res['val']) if res['type'] == 'b64' \
        else urllib.request.urlopen(res['val'], timeout=180).read()
    with open(out, 'wb') as f:
        f.write(data)
    print('OK %.0fKB %.1fs' % (len(data) / 1024, time.time() - t0))
    return out


def main():
    seed = int(os.environ.get('QUICK_SEED', '2002'))
    boost = os.environ.get('QUICK_BOOST', '0') in ('1', 'true', 'True')
    os.makedirs('raw', exist_ok=True)
    sids = sys.argv[1:]
    heroes = RT.load_heroes(set(RT.TRIAL_IDS) | set(RT.TRIAL_FEMALE) | set(FILE_HERO.values()))
    jobs = []
    if sids and sids[0] == '--all':
        # 枚举全部底稿（主 10 + 身份 20）；_朝左 且存在 _朝右 兄弟 = 与兄弟重复 → 跳过（twin 已覆盖）
        for f in sorted(glob.glob('refs_koei/_tk5/*.png')):
            b = os.path.basename(f)
            r, mode = rightify(f)
            if mode == 'twin':
                continue
            h = heroes.get(FILE_HERO.get(b, ''))
            if h is None:
                h = probe_h(f)
            h = dict(h)
            if 'gender' not in h:
                h['gender'] = '男'
            jobs.append(('all', h, f))
        for f in sorted(glob.glob('refs_koei/_tk5/identity/*.png')):
            r, mode = rightify(f)
            jobs.append(('all', probe_h(f), f))
    else:
        for arg in sids:
            if arg in heroes:
                h = dict(heroes[arg])
                h.update(RT.OVERRIDES.get(arg, {}))
                ref_path = RT.TK5_REF.get(arg) or RT.refs_for(arg)[0] if RT.refs_for(arg) else None
                if not ref_path:
                    print('!! 无底稿 %s -> 跳过（走 A 版需 -no-ref 模式，未实现）' % arg)
                    continue
                jobs.append(('one', h, ref_path))
            else:
                ms = glob.glob('refs_koei/_tk5/identity/%s_*.png' % arg) if arg.isdigit() \
                    else glob.glob('refs_koei/_tk5/identity/*%s*.png' % arg)
                if not ms:
                    print('!! 找不到 %s（英雄 sid 或身份底稿编号/名字）' % arg)
                    continue
                jobs.append(('one', probe_h(ms[0]), ms[0]))
    print('共 %d 张' % len(jobs))
    for tag, h, ref in jobs:
        try:
            generate_one(tag, h, ref, seed, boost)
        except Exception as e:
            msg = str(e)[:200]
            print('ERR %s: %s' % (h['name'], msg))
        seed += 1


if __name__ == '__main__':
    main()
