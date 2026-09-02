# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""任务 1：全量 TaikouHero 底图提取 + 朝右化（2026-08-28 用户任务）。

CSV（1047 英雄）→ TK5 BUSTUP（E:/taikou5/TaikouImage/BUSTUP/{编号}_{简体名}）
匹配（CNName）→ 000.dds → PNG → verify_pose 判向 → 朝左镜像 / 朝右原样 / 朝正标注 →
存 refs_koei/_tk5/{编号}_{姓名}_{朝右|朝正}.png（现有 7 张同名覆盖为同规则生成物）
+ hero_refs_manifest.json：{sid: {cn, jp, base_id, ref, dir}} 或 null —— 任务 2 输入。

用法：python build_refs_full.py [--limit N]   # 本地零 API 成本；全量约 60-90 分钟
"""
import argparse, csv, glob, io, json, os, re, sys
from collections import defaultdict
from PIL import Image
import verify_pose as V

# 别名单一事实源 = 剧本工程的 gen_entity_maps.NAME_ALIAS（太阁写法→织丰写法），
# 此处反向使用（织丰显示名 → 太阁目录名候选）。2026-08-29 用户裁定：只填有把握同人的。
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..',
    'Modules', 'LivingWorldNpcs', 'plans', 'scenario-campaign-mode', 'tools')))
from gen_entity_maps import NAME_ALIAS  # noqa: E402

ALIAS_REV = defaultdict(list)
for tk, zf in NAME_ALIAS.items():
    ALIAS_REV[zf].append(tk)

# 借图表：2026-08-29 三洋人均有 TK5 专名（1038_弗洛伊斯/1039_阿尔梅达/1040_拉斐尔，用户两次抓包
# 音译差误判"无图"）→ 借图机制空置保留（结构不动，将来真有无专名的再启用）。
REF_BORROW = {}

SRC = r'E:\taikou5\TaikouImage\BUSTUP'
OUT = 'refs_koei/_tk5'
CSV = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
       'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv')
MANIFEST = os.path.join(OUT, 'hero_refs_manifest.json')
TMP = os.path.join(OUT, '_tmp_judge.png')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='只跑前 N 名（调试用）')
    ap.add_argument('--missing', action='store_true',
                    help='补丁模式：只处理现有 manifest 中 ref=None 的角色（别名表更新后救回用）')
    args = ap.parse_args()

    rows = list(csv.reader(io.open(CSV, encoding='utf-8-sig')))
    idx = {h: i for i, h in enumerate(rows[0])}
    heroes = [r for r in rows[3:] if len(r) > idx['ID'] and r[idx['ID']]]
    if args.limit:
        heroes = heroes[:args.limit]
    if args.missing:
        prev = {}
        if os.path.exists(MANIFEST):
            prev = json.load(open(MANIFEST, encoding='utf-8'))
        heroes = [r for r in heroes if prev.get(r[idx['ID']]) is None]
        print('补丁模式：%d 名待补' % len(heroes))
    else:
        prev = {}
        if os.path.exists(MANIFEST):
            prev = json.load(open(MANIFEST, encoding='utf-8'))  # 非补丁全量跑也不丢已有（幂等复用）
    print('英雄 %d 名' % len(heroes))

    # TK5 目录索引：{姓名: [(编号, 目录)]}；同名多版本取全部，人物建议取最小编号版本
    dirs = {}
    # 🔴 键 = 主名 + 括号别名 + 别名分项（TK5 目录命名 = "主名(别名)"，如 北畠具教(北田具教)；
    #   剥括号主名/括号分项全作键 —— 2026-08-29 修：原逐字匹配 45 人误判无底图）
    for d in sorted(os.listdir(SRC)):
        if '_' not in d:
            continue
        pid_str, name = d.split('_', 1)
        if not pid_str.isdigit():
            continue
        dirs.setdefault(name, []).append((int(pid_str), d))
        m = re.match(r'^(.*?)(?:[（(](.*?)[）)])?$', name)
        if m.group(1):
            dirs.setdefault(m.group(1), []).append((int(pid_str), d))
        if m.group(2):
            for sub in re.split(r'[、;,，]', m.group(2)):
                if sub:
                    dirs.setdefault(sub, []).append((int(pid_str), d))

    manifest, no_ref, bad, stat = {}, [], [], {'LEFT': 0, 'RIGHT': 0, 'FRONT': 0, 'identity_tpl': 0}
    pid_canon = {}  # 同编号共享逻辑：一图一文件，第二个 sid 直接指向（2026-08-29 防 CN 重复双文件）
    os.makedirs(OUT, exist_ok=True)
    ycols = [h for h in rows[0] if h.startswith('Name_')]
    for r in heroes:
        sid, cn, jp = r[idx['ID']], r[idx['CNName']], r[idx['ScriptName']]
        # 候选名集：显示名 + 日文原字 + 各年份当年名 + 别名表反向（太阁目录名；2026-08-29）
        cands = {cn, jp} | set(ALIAS_REV.get(cn, []))
        for c in ycols:
            i = idx.get(c)
            if i is not None and r[i]:
                cands.add(r[i])
        cands = [c for c in cands if c in dirs]
        if not cands:
            # 专用借图表（无专名但有身份模板可用）
            borrowed = REF_BORROW.get(cn)
            if borrowed and borrowed in dirs:
                pid, ddir = dirs[borrowed][0]
                im = Image.open(os.path.join(SRC, ddir, '000.dds')).convert('RGBA')
                im.save(TMP)
                face = None
                try:
                    face = V.judge(TMP)['face_dir']
                except Exception:
                    pass
                if face == 'LEFT':
                    im = im.transpose(Image.FLIP_LEFT_RIGHT)
                    tag = '朝右'
                    stat['LEFT'] += 1
                elif face == 'RIGHT':
                    tag = '朝右'
                    stat['RIGHT'] += 1
                else:
                    tag = '朝正'
                    stat['FRONT'] += 1
                final = os.path.join(OUT, '%d_%s_%s.png' % (pid, cn, tag))
                im.save(final)
                manifest[sid] = {'cn': cn, 'jp': jp, 'base_id': pid,
                                 'ref': os.path.basename(final), 'dir': tag, 'borrow': borrowed}
                continue
            no_ref.append(sid)
            manifest[sid] = None
            continue
        if cn.startswith('无卡'):
            # 身份模板 NPC：不走个人底图（identity/ 组已覆盖），记录待办由身份模板生成
            stat['identity_tpl'] += 1
            manifest[sid] = {'identity_tpl': True}
            continue
        pid, ddir = dirs[cands[0]][0]  # 多人同名共图 = 先到先得（最小编号）
        # 同编号共享（2026-08-29）：第二个 sid（如 河野通直/牛福丸、长坂钓闲/长阪长闲）
        # 不重建独立文件，manifest 指向第一个文件 —— 防"一编号双文件"回归
        if pid in pid_canon:
            manifest[sid] = dict(pid_canon[pid])
            manifest[sid].update({'cn': cn, 'jp': jp})
            continue
        # 已有底图文件 → 复用方向 tag（全量重跑直接秒级，不用再测 1047 张 mediapipe）
        # 🔴 2026-08-29 禁朝左：glob 必须排除 _朝左（'左'< '右' 排序，旧资产遗留坑），朝右优先
        ex = [e for e in glob.glob(os.path.join(OUT, '%d_%s_朝*.png' % (pid, cn)))
              if not e.endswith('_朝左.png')]
        ex.sort(key=lambda e: (0 if e.endswith('_朝右.png') else 1))
        if ex:
            tag = '朝右' if ex[0].endswith('_朝右.png') else '朝正'
            stat[tag == '朝右' and 'RIGHT' or 'FRONT'] += 1
            final = ex[0]
            manifest[sid] = {'cn': cn, 'jp': jp, 'base_id': pid,
                             'ref': os.path.basename(final), 'dir': tag}
            pid_canon.setdefault(pid, manifest[sid])
            continue
        out = os.path.join(OUT, '%d_%s.png' % (pid, cn))
        try:
            im = Image.open(os.path.join(SRC, ddir, '000.dds')).convert('RGBA')
        except Exception as e:
            bad.append((sid, str(e)[:60]))
            manifest[sid] = None
            continue
        im.save(TMP)
        try:
            face = V.judge(TMP)['face_dir']
        except Exception:
            face = None
        if face == 'LEFT':
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
            tag = '朝右'
            stat['LEFT'] += 1
        elif face == 'RIGHT':
            tag = '朝右'
            stat['RIGHT'] += 1
        elif face == 'FRONT':
            tag = '朝正'
            stat['FRONT'] += 1
        else:
            tag = '朝正'  # 判向失败 → 按中性存，生成走 seed 抽
            stat['FRONT'] += 1
        final = os.path.join(OUT, '%s_%s_%s.png' % (pid, cn, tag))
        im.save(final)  # 同名幂等覆盖；多人同名共图 = 先到先得
        manifest[sid] = {'cn': cn, 'jp': jp, 'base_id': pid,
                         'ref': os.path.basename(final), 'dir': tag}
        pid_canon[pid] = manifest[sid]
    if os.path.exists(TMP):
        os.remove(TMP)
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    n_ref = sum(1 for v in manifest.values() if v and not v.get('identity_tpl'))
    print('有底图(人物): %d  身份模板NPC: %d  无底图: %d  转换失败: %d'
          % (n_ref, stat['identity_tpl'], len(no_ref), len(bad)))
    print('判向统计: %s' % stat)
    if bad:
        print('转换失败: %s' % bad[:10])
    print('manifest -> %s' % MANIFEST)


if __name__ == '__main__':
    main()
