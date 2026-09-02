# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""模板类型终表生成（2026-08-29 用户裁定规则）：
  ① 简繁异性之名 = 并；② 教头=师范（代分开）；③ 足轻/海贼船系等级不可并；
  ④ 町民（同性）可并；⑤ 未批的相似（店家×店/商人来源/公主系）= 保持独立；
  ⑥ 双性别职业 _male/_female 分开。
输出：_template_id_final.tsv（ScriptName → template_id 终映射，供用户终批 → 迁移执行）。
"""
import csv, io, sys
from collections import defaultdict, Counter

CSV = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
       'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv')
rows = list(csv.reader(io.open(CSV, encoding='utf-8-sig')))
hdr = rows[0]
iid, itp, isc, icn = hdr.index('ID'), hdr.index('模板NPC'), hdr.index('ScriptName'), hdr.index('CNName')
tpl = defaultdict(list)
for r in rows[1:]:
    if len(r) <= max(iid, itp, isc, icn):
        continue
    if r[itp].strip() == '1':
        tpl[r[isc]].append((r[iid], r[icn]))

# —— 人工映射：ScriptName → (type, gender) —— 逐字录入（88 条）
MAP = {
    '公家': ('kuge', 'm'), '农民女': ('noumin', 'f'), '農民女': ('noumin', 'f'),
    '农民男': ('noumin', 'm'), '農民男': ('noumin', 'm'),
    '町民男': ('choumin', 'm'), '通用町人男': ('choumin', 'm'), '町民女': ('choumin', 'f'),
    '忍者': ('ninja', 'm'), '无卡忍者': ('ninja', 'm'),
    '女忍者': ('kunoichi', 'f'), '泛用女忍者': ('kunoichi', 'f'),
    '足轻': ('ashigaru', 'm'), '足輕': ('ashigaru', 'm'),
    '足轻大将': ('ashigaru_daisho', 'm'), '足轻组头': ('ashigaru_kumi', 'm'),
    # 教头 = 师范
    '剑术的师范': ('swordshihan', 'm'), '劍術的師範': ('swordshihan', 'm'),
    '剑术教头': ('swordshihan', 'm'), '师范': ('swordshihan', 'm'),
    '剑术师范代': ('shihandai', 'm'), '劍術師範代': ('shihandai', 'm'),
    '代理教头': ('shihandai', 'm'), '师范代': ('shihandai', 'm'),
    '枪术的师范': ('yari_shihan', 'm'), '槍術的師範': ('yari_shihan', 'm'),
    '枪术教头': ('yari_shihan', 'm'),
    # 海贼/船上等级
    '海贼': ('kaizoku', 'm'), '海賊': ('kaizoku', 'm'), '无卡海贼': ('kaizoku', 'm'),
    '头领': ('kaizoku_tou', 'm'), '头目': ('kashira', 'm'),
    '船大将': ('funa_daisho', 'm'), '船头': ('sentou', 'm'),
    '水夫头': ('suifu_tou', 'm'), '水夫': ('suifu', 'm'),
    # 商人类（未批 → 保持独立）
    '商人': ('merchant', 'm'), '无卡商人': ('merchant', 'm'),
    '明朝商人': ('merchant_ming', 'm'), '朝鲜商人': ('merchant_choseon', 'm'),
    '琉球商人': ('merchant_ryukyu', 'm'), '行商人': ('merchant_gyo', 'm'),
    '座的掌柜': ('za_shihai', 'm'),
    # 店家（未批 → 每店独立；简繁并）
    '马屋老板': ('umaya_tenpo', 'm'), '馬屋的老闆': ('umaya_tenpo', 'm'), '马屋的老板': ('umaya_tenpo', 'm'),
    '米屋老板': ('komeya_tenpo', 'm'),
    '酒馆老板娘': ('sakaba_onna', 'f'), '酒场的老板娘': ('sakaba_onna', 'f'),
    '酒場的老闆娘': ('sakaba_onna', 'f'),
    '宿屋的老板娘': ('yadoya_onna', 'f'), '旅店老板娘': ('ryotei_onna', 'f'),
    '药屋老板': ('kusuriya_tenpo', 'm'), '药屋老板娘': ('kusuriya_onna', 'f'),
    '掌柜': ('tenpo', 'm'), '掌柜老板': ('tenpo_tenpo', 'm'),
    # 武家阶级（独立）
    '大名': ('daimyo', 'm'), '国主': ('kokushu', 'm'), '城主': ('joushu', 'm'),
    '当家': ('toudou', 'm'), '家老': ('karou', 'm'), '部将': ('bushou', 'm'),
    '侍大将': ('samurai_taisho', 'm'), '浪人': ('ronin', 'm'),
    '上忍': ('jounin', 'm'), '中忍': ('chunin', 'm'), '下忍': ('genin', 'm'),
    '见习': ('kenkyu', 'm'), '锻冶匠': ('kajishi', 'm'),
    '医师': ('ishi', 'm'), '醫者': ('ishi', 'm'),
    '僧侣': ('souryo', 'm'), '僧侶': ('souryo', 'm'), '茶人': ('chajin', 'm'),
    '小姓': ('koshou', 'm'), '番头': ('bantou', 'm'), '番頭': ('bantou', 'm'),
    '门卫': ('monban', 'm'),
    '門衛': ('monban', 'm'), '旅人': ('tabibito', 'm'),
    '天皇': ('tennou', 'm'), '备大将': ('shougun', 'm'), '備大將': ('shougun', 'm'),
    '保镖': ('hogo', 'm'), '保鏢': ('hogo', 'm'), '博古通今的老人': ('hakkoujin', 'm'),
    '宿屋的老板娘': ('yadoya_onna', 'f'), '宿屋的老闆娘': ('yadoya_onna', 'f'),
    '剣術的師範': ('swordshihan', 'm'),
    '喝醉的男人': ('yoi_otoko', 'm'), '喝醉的女人': ('yoi_onna', 'f'),
    '小孩': ('kodomo', 'm'), '女孩': ('kodomo_f', 'f'), '贼': ('yotto', 'm'),
    '通訳通奉行': ('tsuuyaku', 'm'), '通译通奉行': ('tsuuyaku', 'm'),
    '武家贵女': ('bukake', 'f') if False else ('kaji', 'm'),  # 占位，实际无此行
    # 女系（公主三类未批 → 独立；简繁并）
    '公主': ('hime', 'f'), '亡国公主(竹姬 樱姬 乙姬 万寿姬)': ('hime_hime', 'f'),
    '汎用姫様': ('hime_hanyou', 'f'), '泛用姫様': ('hime_hanyou', 'f'),
    '女城主': ('onna_joushu', 'f'), '女将': ('onna_shou', 'f'),
    # 家臣体系（各独立，简繁同）
    '武力家臣': ('buryoku_kashin', 'm'), '武力陪臣': ('buryoku_baishin', 'm'),
    '功勋家臣': ('koushin_kashin', 'm'), '功勳家臣': ('koushin_kashin', 'm'),
    '功勋陪臣': ('koushin_baishin', 'm'), '功勳陪臣': ('koushin_baishin', 'm'),
    '外交家臣': ('gaikou_kashin', 'm'), '外交陪臣': ('gaikou_baishin', 'm'),
    '伙计': ('detchi', 'm'),
}

GENDER_SEQ_TYPES = {'noumin', 'choumin'}
unmapped = []
cnt = defaultdict(list)
for sk, lst in tpl.items():
    v = MAP.get(sk)
    if v is None:
        unmapped.append(sk)
        continue
    tp, g = v
    cnt[(tp, g)].extend(lst)

with io.open('_template_id_final.tsv', 'w', encoding='utf-8') as f:
    f.write('type\tgender\tScriptName\trows\n')
    for (tp, g), lst in sorted(cnt.items()):
        f.write('%s\t%s\t%s\t%d\n' % (tp, ('m' if g == 'm' else 'f'), tp, len(lst)))
    if unmapped:
        f.write('# 未映射: %s\n' % '; '.join(unmapped))
print('最终类型数: %d | 未映射: %s' % (len(cnt), unmapped))

def apply_migration(mapping):
    """按映射执行迁移：旧 ID → template_{type}[_{gender}]_{seq}，写映射留痕 + 改主源 CSV ID。"""
    base_of = {}
    seq = {}
    for (tp, g), lst in mapping.items():
        if tp in ('noumin', 'choumin', 'ninja'):      # 双性别职业
            base = 'template_%s_%s' % (tp, 'male' if g == 'm' else 'female')
        elif tp == 'kunoichi':                        # 女忍者专属词，单性
            base = 'template_kunoichi'
        else:
            base = 'template_%s' % tp
        n = 0
        for sid, cn in lst:
            n += 1
            base_of[sid] = '%s_%02d' % (base, n)
    with io.open('_template_id_map.tsv', 'w', encoding='utf-8') as f:
        for sid, new in base_of.items():
            f.write('%s\t%s\n' % (sid, new))
    # 改主源 CSV
    rows = list(csv.reader(io.open(CSV, encoding='utf-8-sig')))
    hit = 0
    for r in rows[1:]:
        if len(r) > iid and r[iid] in base_of:
            r[iid] = base_of[r[iid]]
            hit += 1
    with io.open(CSV, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows(rows)
    print('迁移完成: %d 行 ID 替换 -> template_*（映射留痕 _template_id_map.tsv）' % hit)


if __name__ == '__main__':
    if '--apply' in sys.argv:
        apply_migration(cnt)
    else:
        print('生成草稿终表 -> _template_id_final.tsv')

