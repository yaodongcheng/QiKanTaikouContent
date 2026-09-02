# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""情绪态立绘生成（2026-08-30 用户定稿「emotion 版」规范，勿改）：
① 参考图 = selected/ 对应当前图（用户审定正式图，姿势/镜像一致，只改表情）
② 目录 = ProfileImage/emotion/ 专用子文件夹（normal 留根）
③ 命名 = emotion/{tkid}_{StringId}_bustup_{emo}.png / …_minihead_{emo}.png（第 4 段 = 情绪）
④ 名单 = 9 人 17 卡（plan §二「emotion 版」拍板）：信长(195,1154) 家康(506) 秀吉(517,1172,1173,1174)
   光秀(14,1152) 柴田胜家(379,1163) 上杉谦信(119) 石田三成(75,1153) 武田信玄(449) 真田幸村(361,1162)
⑤ 管线：情绪生成（gpt-image-2，底板 1024x1536）→ raw/ 存档 → matte plain + place（512x768 半透明贴底）
   → minihead（上部 512 切 256x256）→ 每卡 1x4 拼图 preview/emotion_review_{tkid}_{sid}.jpg

费用：68 张 × ¥0.40 ≈ ¥27.2（G.generate 实时计费）。
用法：
  python emotion_edit.py                    # 全量 17 卡 68 张
  python emotion_edit.py 195,506            # 指定卡（tkid 逗号分隔）
  python emotion_edit.py 195 happy,angry    # 指定情绪（第二参数）
"""
import base64, csv, io, json, os, sys, time, urllib.request, urllib.error

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import gen_portrait as G
import matte_rembg as M

# 只改表情+适度姿态；铁律保持句（2026-08-30 用户裁定：允许姿态变化，服装特征不变）
KEEP = ('构图与背景氛围、光影、画风必须与参考图一致；'
        '人物的体型、面容特征（脸型、骨相、五官造型、胡须）、发型（含发髻/盔帽）必须与参考图完全一致；'
        '服饰与装备的特征（款式、纹饰、配色、材质、穿戴方式）必须与参考图完全一致，不允许任何变更或增减；'
        '身体姿态必须配合情绪发生适度变化（按表情描述中的具体姿态指令执行）：幅度自然、不夸张、'
        '不脱离立绘站姿；不得改变人物身份、场景氛围；禁止文字。')
EMO = {
    'happy':    '表情改为：展颜开怀欢笑，嘴角上扬微露牙齿，双眼微眯，眉梢舒展，神情畅快。'
                '姿态配合：头部侧倾微转，肩部微耸，身体略微向侧面小幅转动，整体舒展放松，'
                '仿佛正与人谈笑。',
    'angry':    '表情改为：勃然大怒，眉头紧锁，双眼圆睁怒视，嘴角下压紧抿，下颌紧绷。'
                '姿态配合：身体前倾，肩膀紧绷高抬，下巴微收，如临大敌气势逼人。',
    'sad':      '表情改为：神情哀伤，眉头微蹙低垂，眼神黯淡下垂，嘴角微微下压。'
                '姿态配合：肩膀微塌、重心略低，头部微微低垂侧转，沉郁消沉。',
    'surprised': '表情改为：神情惊愕，眉毛高挑抬起，双目圆睁，鼻翼微张嘴巴轻启。'
                 '姿态配合：身体微微后仰，双肩微抬，双手似有意外欲抬之势，定身一瞬。',
}
EMO_ORDER = ['happy', 'angry', 'sad', 'surprised']
DEFAULT_CARDS = '195,1154,506,517,1172,1173,1174,14,1152,379,1163,119,75,1153,449,361,1162'
SEED0 = 3001


def picktkid():
    return json.load(open('_review/picktkid.json', encoding='utf-8'))


def load_persona():
    """人物刻板印象（TaikouHero.csv Persona 列；知识库 csv 目录，生成物列由 repair_csv 注入）。"""
    m = {}
    try:
        with io.open(('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
                      'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv'),
                     encoding='utf-8-sig') as f:
            dr = csv.DictReader(f)
            if 'Persona' in (dr.fieldnames or []):
                for r in dr:
                    if r.get('Persona'):
                        m[r['ID'].strip()] = r['Persona'].strip()
    except FileNotFoundError:
        print('!! TaikouHero.csv 缺失，persona 为空')
    return m


def gen_one(sid, emo, base, seed, tkid, persona=''):
    """情绪原图生成：唯一花钱入口（¥0.40/张）+ raw 存档。persona = 人物刻板印象（TaikouHero Persona 列）。"""
    prompt = KEEP + '。'
    if persona:
        prompt += '人物气质人设（表情与姿态的力度和倾向参考）：' + persona + '。'
    prompt += EMO[emo]
    res = G.generate(prompt, ref=[G.data_uri(base)], seed=seed)
    data = base64.b64decode(res['val']) if res['type'] == 'b64' \
        else urllib.request.urlopen(res['val'], timeout=240).read()
    out = 'raw/%s_%s_%s.png' % (tkid, sid, emo)
    with open(out, 'wb') as f:
        f.write(data)
    print('OK %s %5.0fKB' % (os.path.basename(out), len(data) / 1024))
    return out


def finalize(emo_path, tkid, sid, emo, refinalize=False):
    """情绪原图 → 半透明 bustup（512x768 贴底）+ minihead（256x256）→ ProfileImage/emotion/。
    mtime 自愈：raw 新于 bustup（如改 prompt 重跑）→ 自动重贴底。
    refinalize（--refinalize）：模型换代（isnet→u2net / 眼锚 v1→v6）强制重做。
    返回 (bpath, anchor_level)。"""
    os.makedirs('ProfileImage/emotion', exist_ok=True)
    bname = '%s_%s_bustup_%s.png' % (tkid, sid, emo)
    mname = '%s_%s_minihead_%s.png' % (tkid, sid, emo)
    bpath = os.path.join('ProfileImage/emotion', bname)
    mpath = os.path.join('ProfileImage/emotion', mname)
    if (refinalize or not os.path.exists(bpath) or os.path.getsize(bpath) == 0
            or os.path.getmtime(bpath) < os.path.getmtime(emo_path)):
        rgba = M.matte(emo_path, alpha_matting=False)
        M.place(rgba, bpath)
    lvl = 0
    if (refinalize or not os.path.exists(mpath) or os.path.getsize(mpath) == 0
            or os.path.getmtime(mpath) < os.path.getmtime(bpath)):
        lvl = M.build_minihead(emo_path, mpath, alpha_path=bpath)[0]   # v7：眼锚+肤色兜底（2026-08-30 用户裁定）
    return bpath, lvl


def review_sheet(tkid, sid, bpaths):
    from PIL import Image
    ims = [Image.open(p).convert('RGB') for p in bpaths]
    w, h = ims[0].size
    sheet = Image.new('RGB', (w * len(ims), h), (28, 28, 34))
    for i, im in enumerate(ims):
        sheet.paste(im, (w * i, 0))
    os.makedirs('preview', exist_ok=True)
    name = 'preview/emotion_review_%s_%s.jpg' % (tkid, sid)
    sheet.resize((w * len(ims) // 2, h // 2), Image.LANCZOS).save(name, quality=88)
    return name


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--force' in sys.argv:                    # --force = 已存在的情结原图也重生成（2026-08-30 调 prompt 重试）
        force = True
    else:
        force = False
    if '--refinalize' in sys.argv:               # --refinalize = 不重生成（raw 不动），仅重做抠图/头图
        refinalize = True                         # （2026-08-30 模型换代 isnet→u2net / minihead v2）
    else:
        refinalize = False
    if args and (args[0].isdigit() or ',' in args[0]):
        cards = args[0].split(',')
    else:
        cards = DEFAULT_CARDS.split(',')
    if len(args) > 1:
        emos = args[1].split(',')
        assert set(emos) <= set(EMO), '情绪需 ∈ %s' % (list(EMO),)
    else:
        emos = EMO_ORDER
    st = picktkid()
    persona_map = load_persona()
    metas = []            # minihead 锚点元数据（复核闸：level>=1 = 降级锚，必审）
    print('情绪图：%d 卡 × %d 情绪 = %d 张 × ¥0.40 ≈ ¥%.1f' % (len(cards), len(emos),
                                                             len(cards) * len(emos),
                                                             len(cards) * len(emos) * 0.40))
    for ci, tkid in enumerate(cards):
        t = tkid
        v = st.get(t)
        if not isinstance(v, dict) or not v.get('chosen'):
            print('!! tkid=%s 无所选卡' % t)
            continue
        sid = v.get('sid') or ''
        base = os.path.join('selected', '%s_%s.png' % (t, sid))
        if not os.path.exists(base):
            print('!! 底板缺失 selected/%s_%s.png' % (t, sid))
            continue
        bpaths = []
        for i, emo in enumerate(emos):
            raw_path = 'raw/%s_%s_%s.png' % (t, sid, emo)
            if os.path.exists(raw_path) and os.path.getsize(raw_path) > 0 and not force:
                print('SKIP 已存在 %s' % os.path.basename(raw_path))
            else:
                try:
                    gen_one(sid, emo, base, SEED0 + ci * 10 + i, t, persona_map.get(sid, ''))
                except urllib.error.HTTPError as ex:
                    print('ERR %s/%s: HTTP %s' % (t, emo, ex))
                    continue
                except Exception as ex:
                    print('ERR %s/%s: %s' % (t, emo, str(ex)[:150]))
                    continue
            bp, lvl = finalize(raw_path, t, sid, emo, refinalize)
            bpaths.append(bp)
            metas.append([t, sid, emo, lvl])
        if bpaths:
            print('-> ' + review_sheet(t, sid, bpaths))
    if metas:
        with io.open('ProfileImage/emotion/minihead_meta.csv', 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['tkid', 'StringId', 'emotion', 'anchor_level'])
            w.writerows(metas)
        bad = [m for m in metas if int(m[3]) >= 1]
        print('emotion 锚层：level0=%d 降级锚=%d（level>=1 必审）' % (len(metas) - len(bad), len(bad)))
        for m in bad:
            print('  !! 降级锚 tkid=%s sid=%s emo=%s level=%s' % (m[0], m[1], m[2], m[3]))


if __name__ == '__main__':
    main()
