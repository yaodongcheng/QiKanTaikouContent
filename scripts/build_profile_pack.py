# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""立绘 tpac 内容包生成器（2026-08-30）——产物全部为生成物，禁手改；改本脚本后重跑。

输入：
  ProfileImage/                     bustup 512x768 + minihead 256x256（终版图谱）
  ProfileImage/emotion/             17 卡 x 4 情绪（bustup + minihead）
  Knowledge/.../csv/ProfileImage.csv tkid,StringId,bustup,minihead（上游 build_profileassets.py 生成物）
  Knowledge/.../csv/TaikouHero.csv   ID(=StringId)/TK5编号/立绘阶段列（JSON: stage/tkid/emotion/ref）—— 阶段权威数据（零新增人工表）
输出（内容包 = ShokuhoTaikouExpansionPack）：
  ModuleData/AssetRegistry/ProfileStages.csv   StringId,stage,tkid,bustupSprite,miniheadSprite
  ModuleData/AssetRegistry/ProfileEmotion.csv  tkid,emotion,bustupSprite,miniheadSprite
  GUI/LWProfilesSpriteData.xml                 4 个 category（lwnprof_*）+ 每卡 SpritePart + GenericSprite
  ArtSource/profile_pack_manifest.json         供 tpaccli makepack；outDir = 内容包 AssetPackages/
命名规范（已定版）：sprite = lwnprof_bustup|minihead_{tkid} / lwnprof_emobustup|emomini_{tkid}_{emo}；
texture 名 = {Category}_{N}（1-based，引擎 SpriteCategory.Load 约定）。
用法：python build_profile_pack.py [--emo-only] [--limit N] [--dry]
"""
import csv
import json
import os
import sys
from pathlib import Path

ART = Path.cwd()  # chdir 契约后 = ArtSource
LWN_ROOT = Path('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/LivingWorldNpcs')
CSV_KN = LWN_ROOT / 'Knowledge' / '骑砍2织丰角色ID对应' / 'csv'
PKG = Path('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/ShokuhoTaikouExpansionPack')

EMO_ORDER = ['happy', 'angry', 'sad', 'surprised']
CATS = {
    'bustup': ('lwnprof_bustup', 512, 768),
    'minihead': ('lwnprof_mini', 256, 256),
    'emobustup': ('lwnprof_emobustup', 512, 768),
    'emomini': ('lwnprof_emomini', 256, 256),
}
KIND_TO_CAT = {'bustup': 'bustup', 'minihead': 'minihead',
               'emobustup': 'emobustup', 'emomini': 'emomini'}


def load_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def sprite_name(kind, tkid, emo=None):
    return f'lwnprof_{kind}_{tkid}' if emo is None else f'lwnprof_{kind}_{tkid}_{emo}'


def main():
    emo_only = '--emo-only' in sys.argv
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 0
    dry = '--dry' in sys.argv

    # ── 1. ProfileImage.csv（tkid → StringId / 路径；tkid 必须唯一）──
    prof = load_csv(CSV_KN / 'ProfileImage.csv')
    by_tkid = {r['tkid']: r for r in prof}
    assert len(by_tkid) == len(prof), 'ProfileImage.csv tkid 重复'

    # ── 2. TaikouHero 立绘阶段 JSON（StringId → [(stage, tkid, emotion)]）──
    hero = load_csv(CSV_KN / 'TaikouHero.csv')
    stages = {}
    for r in hero:
        j = (r.get('立绘阶段') or '').strip()
        if not j:
            continue
        try:
            arr = json.loads(j)
        except Exception as e:
            raise AssertionError(f"TaikouHero 立绘阶段 JSON 解析失败 {r['ID']}: {e}")
        stages[r['ID']] = [(x['stage'], x['tkid'], int(x.get('emotion', 0) or 0)) for x in arr]

    # tkid → (StringId, stage, emotion, kind) 元数据（无阶段人物兜底 stage="", emotion=0）
    # 注意：同 StringId 的多个 tkid 各自记 stage；TaikouHero 无行的 tkid（模板 NPC 等）按无阶段处理（CSV 兜底）
    TKID_KNOWN = set()
    for sid, arr in stages.items():
        for s, t, e in arr:
            TKID_KNOWN.add(t)
    tkid_meta = {}
    for r in prof:
        sid = r['StringId']
        stage, emo = '', 0
        for s, t, e in stages.get(sid, []):
            if t == r['tkid']:
                stage, emo = s, e
                break
        tkid_meta[r['tkid']] = {'sid': sid, 'stage': stage, 'emotion': emo}
    n_staged = sum(1 for r in prof if tkid_meta[r['tkid']]['stage'] != '')
    n_multi_sids = sum(1 for s, a in stages.items() if len(a) > 1)
    print(f'[阶段] 角色 {len(stages)} 有阶段数据（多阶段 {n_multi_sids}）；卡 {len(prof)}，其中带 stage {n_staged}')

    # ── 3. emotion 清单（17 卡 × 4；目录 = 用户验收真值；TaikouHero 标记仅告警对账）──
    emo_dir = ART / 'ProfileImage' / 'emotion'
    emo_tkids = sorted({f.split('_bustup_')[0].split('_', 1)[0]
                        for f in os.listdir(emo_dir) if '_bustup_' in f},
                       key=lambda t: int(t.split('_')[0]))
    for tkid in emo_tkids:
        assert tkid in tkid_meta, f'emotion 目录含 ProfileImage.csv 之外的卡 {tkid}'
        for emo in EMO_ORDER:
            for kind in ('bustup', 'minihead'):
                fname = f'{tkid}_{tkid_meta[tkid]["sid"]}_{kind}_{emo}.png'
                assert (emo_dir / fname).exists(), f'缺 emotion 文件 {fname}'
    marked = {t for arr in stages.values() for s, t, e in arr if e and t}
    diff = marked - set(emo_tkids)
    if diff:
        print(f'[emotion][告警] TaikouHero 标记 emotion=1 但目录无卡的 tkid: {sorted(diff, key=int)}（目录名单为验收真值，忽略）')
    emo_list = [(t, e) for t in emo_tkids for e in EMO_ORDER]
    print(f'[emotion] {len(emo_tkids)} 卡 × 4 = {len(emo_list)}（bustup+minihead 各 {len(emo_list)}）')

    # ── 4. 卡片池（--emo-only / --limit 只影响普通 2 包；emotion 包始终全量）──
    prof = [r for r in prof if not (emo_only and r['tkid'] not in set(emo_tkids))]
    if limit:
        prof = prof[:limit]
    prof_sorted = sorted(prof, key=lambda r: int(r['tkid']))

    # ── 5. 4 类条目 ────────────────
    def main_item(tkid, kind):
        r = by_tkid[tkid]
        return {'sprite': sprite_name(kind, tkid),
                'png': str(ART / (r['bustup'] if kind == 'bustup' else r['minihead']))}

    def emo_item(tkid, emo, kind):
        # kind ∈ {'bustup','mini'}（sprite 词）；文件名后缀 = 'bustup'/'minihead'（真实文件词）
        sid = tkid_meta[tkid]['sid']
        file_kind = 'bustup' if kind == 'bustup' else 'minihead'
        return {'sprite': sprite_name('emo' + kind, tkid, emo),
                'png': str(emo_dir / f'{tkid}_{sid}_{file_kind}_{emo}.png')}

    cat_items = [
        ('lwnprof_bustup', 512, 768, [main_item(r['tkid'], 'bustup') for r in prof_sorted]),
        ('lwnprof_mini', 256, 256, [main_item(r['tkid'], 'mini') for r in prof_sorted]),
        ('lwnprof_emobustup', 512, 768, [emo_item(t, e, 'bustup') for t, e in emo_list]),
        ('lwnprof_emomini', 256, 256, [emo_item(t, e, 'mini') for t, e in emo_list]),
    ]

    # ── 6. 断言 ──
    all_sprites = [i['sprite'] for cat, w, h, items in cat_items for i in items]
    assert len(all_sprites) == len(set(all_sprites)), 'Sprite 名重复！'
    for name in all_sprites:
        assert all(ch.isascii() for ch in name), f'非法 sprite 名（非 ASCII）: {name}'
    for cat, w, h, items in cat_items:
        for i in items:
            assert Path(i['png']).exists(), f'png 不存在 {i["png"]}'

    if dry:
        print('[dry] 不落盘。')
        return 0

    # ── 7. SpriteData XML（零注释！全子元素！格式规则 = custom-png-import-guide.md）──
    xml = ['<?xml version="1.0" encoding="utf-8"?>', '<SpriteData>', '  <SpriteCategories>']
    for cat, w, h, items in cat_items:
        xml.append('    <SpriteCategory>')
        xml.append(f'      <Name>{cat}</Name>')
        xml.append(f'      <SpriteSheetCount>{len(items)}</SpriteSheetCount>')
        for i in range(1, len(items) + 1):
            xml.append(f'      <SpriteSheetSize ID="{i}" Width="{w}" Height="{h}" />')
        xml.append('    </SpriteCategory>')
    xml.append('  </SpriteCategories>')
    xml.append('  <SpriteParts>')
    for cat, w, h, items in cat_items:
        for i, item in enumerate(items, start=1):
            xml.append(f'    <SpritePart>')
            xml.append(f'      <Name>{cat}_p{i}</Name>')
            xml.append(f'      <Width>{w}</Width>')
            xml.append(f'      <Height>{h}</Height>')
            xml.append(f'      <CategoryName>{cat}</CategoryName>')
            xml.append(f'      <SheetID>{i}</SheetID>')
            xml.append(f'      <SheetX>0</SheetX>')
            xml.append(f'      <SheetY>0</SheetY>')
            xml.append('    </SpritePart>')
    xml.append('  </SpriteParts>')
    xml.append('  <Sprites>')
    for cat, w, h, items in cat_items:
        for i, item in enumerate(items, start=1):
            xml.append('    <GenericSprite>')
            xml.append(f'      <Name>{item["sprite"]}</Name>')
            xml.append(f'      <SpritePartName>{cat}_p{i}</SpritePartName>')
            xml.append('    </GenericSprite>')
    xml.append('  </Sprites>')
    xml.append('</SpriteData>')

    out_xml = PKG / 'GUI' / 'LWProfilesSpriteData.xml'
    out_xml.parent.mkdir(parents=True, exist_ok=True)
    with open(out_xml, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(xml) + '\n')
    print(f'[XML] {out_xml}（sprites {len(all_sprites)}）')

    # ── 8. ProfileStages.csv（每 StringId×阶段 一行；无阶段=单行 stage 空）──
    stages_csv = []
    seen = set()
    sprint_key = lambda r: int(r['tkid'])
    for r in sorted(prof_sorted, key=sprint_key):
        m = tkid_meta[r['tkid']]
        key = (m['sid'], m['stage'], r['tkid'])
        assert key not in seen, f'阶段行重复 {key}'
        seen.add(key)
        stages_csv.append({'StringId': m['sid'], 'stage': m['stage'], 'tkid': r['tkid'],
                           'bustupSprite': sprite_name('bustup', r['tkid']),
                           'miniheadSprite': sprite_name('mini', r['tkid'])})
    out_st = PKG / 'ModuleData' / 'AssetRegistry' / 'ProfileStages.csv'
    out_st.parent.mkdir(parents=True, exist_ok=True)
    with open(out_st, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['StringId', 'stage', 'tkid', 'bustupSprite', 'miniheadSprite'])
        w.writeheader()
        w.writerows(stages_csv)
    print(f'[CSV] ProfileStages.csv {len(stages_csv)} 行（StringId 数 {len({x["StringId"] for x in stages_csv})}）')

    emo_csv = [{'tkid': t, 'emotion': e,
                'bustupSprite': sprite_name('emobustup', t, e),
                'miniheadSprite': sprite_name('emomini', t, e)} for t, e in emo_list]
    out_em = PKG / 'ModuleData' / 'AssetRegistry' / 'ProfileEmotion.csv'
    with open(out_em, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['tkid', 'emotion', 'bustupSprite', 'miniheadSprite'])
        w.writeheader()
        w.writerows(emo_csv)
    print(f'[CSV] ProfileEmotion.csv {len(emo_csv)} 行')

    # ── 9. manifest.json（makepack 输入）──
    manifest = {'outDir': str(PKG / 'AssetPackages'), 'packs': []}
    for cat, w, h, items in cat_items:
        manifest['packs'].append({
            'packName': cat,
            'textures': [{'name': f'{cat}_{i}', 'png': it['png'], 'width': w, 'height': h}
                         for i, it in enumerate(items, start=1)],
        })
    out_man = ART / 'profile_pack_manifest.json'
    with open(out_man, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f'[MANIFEST] {out_man}（4 包共 {sum(len(p["textures"]) for p in manifest["packs"])} 纹理）')
    print('[OK] 生成完成，下一步：tpaccli makepack --manifest profile_pack_manifest.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
