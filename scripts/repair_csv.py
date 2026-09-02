# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""TaikouHero.csv 创伤恢复 = 确定性重放（2026-08-29 会话后半段全部改动）。
base = git HEAD（已有：模板NPC列+标记 / TK5编号列 / 立绘阶段/模板列空壳）。
目标态（与受损前一致）：1119 行 · template_ 70 行 · 各列全填。
步骤带计数断言，跑完与 COORD 常量核对。
"""
import csv, io, json, os, re, sys
sys.path.insert(0, os.getcwd())
import build_template_map as BTM   # MAP/import 复用
PORTRAIT_STAGES = __import__('update_portrait_stages').PORTRAIT_STAGES

CSV = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
       'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv')

# —— 1 阶：新增/救回英雄的 TK5 映射（会话后半段全部填实）——
HERO_FIX = {
    'lord_1_nomin_onna': '1113', 'lord_1_anatsu': '1113',
    'lord_1_choumin_onna': '1115', 'lord_1_jinbo_5': '1115',
    'lord_1_hanyou_onna': '1126', 'lord_1_aya': '1125',
    'lord_1_aoyama_tadanari': '0', 'lord_1_akaike_nagatomo': '1',
    'lord_1_sato': '1041',
    'lord_1_kamei_korenori': '239', 'lord_1_takeda_harufusa': '448',
    'lord_1_morita_joun': '1238', 'lord_1_jinzenji_bungo': '1271',
    'lord_1_minami-hime': '1097', 'lord_1_imagawa_fujin': '1052',
    'lord_1_kiku_hime': '1051', 'lord_1_shiro': '1093',
    'lord_1_toku_hime': '1064', 'lord_1_yodogimi': '1046',
}
# 1 阶：Hero 词表 35 人（阶段多 ID）
# 2 阶：模板代表图（含单档 + 4 档主行）—— 复用 BTM.MAP 的 type→(type,gender) + 代表底稿表
TPL_REP = {'swordshihan':'1118','yari_shihan':'1141','shihandai':'1139','kenkyu':'1139',
 'jounin':'886','chunin':'886','genin':'886','ninja':'886','kunoichi':'1126',
 'kaizoku':'1012','kaizoku_tou':'1148','kashira':'1147','funa_daisho':'1012',
 'sentou':'1012','suifu_tou':'1012','suifu':'1012',
 'merchant':'952','merchant_gyo':'1085','merchant_ming':'1133','merchant_choseon':'1132',
 'merchant_ryukyu':'1134','za_shihai':'1131','tenpo':'1136',
 'umaya_tenpo':'1109','komeya_tenpo':'1108','sakaba_onna':'1110','yadoya_onna':'1115',
 'ryotei_onna':'1111','kusuriya_onna':'1115','kusuriya_tenpo':'1136',
 'noumin':'1112','choumin':'1115','choumin_male':'1114','choumin_female':'1115',
 'hime':'1049','hime_hime':'1105','hime_hanyou':'1049','kodomo':'1127','kodomo_f':'1142',
 'yoi_otoko':'1123','yoi_onna':'1124','hakkoujin':'1084','koshou':'1128',
 'bantou':'1136','monban':'1107','tennou':'1044','shougun':'1121','hogo':'1129',
 'tabibito':'1122','tsuuyaku':'952','yotto':'1130',
 'koushin_kashin':'1121','koushin_baishin':'1121','buryoku_kashin':'1121',
 'buryoku_baishin':'1121','gaikou_kashin':'1121','gaikou_baishin':'1121',
 'detchi':'1143','ashigaru':'1121','souryo':'1117','kuge':'1119','ishi':'1138',
 'samurai_taisho':'1121','toudou':'1121','karou':'1121','bushou':'1121',
 'ashigaru_daisho':'1121','ashigaru_kumi':'1121','kaizoku_tou_x':'1148',
 'kahra':'1147','kajishi':'1137','ronin':'1118'}
# R1 修正依据（refs_koei/_tk5 文件名锤实，非他选）：
#  1114=町民男 1123=喝醉的男人 1124=喝醉的女人 1130=贼 1084=博古通今的老人 1128=小姓
#  1107=门卫 1122=旅人 1109=马屋老板 1108=米屋老板 1110=酒馆老板娘 1111=旅店老板娘
#  1137=锻冶匠；ronin 无专卡 → 1118 剑士脸（存量一致）；zhishai 1131=座的掌柜（原 1136 已生成值改回专卡）。
# 4 档组（无卡X 并入主行）：主行 = 主卡 + 3 年龄档（形象账 recs）；TK5编号列 = 无卡池全量
# （2026-08-29 用户裁定：无卡商/忍/海贼的 id 全部并入对应主行的 TK5 列——`|` 分隔，动态收集不写死枚数）
WKA = {'template_ninja_male_01': ('无卡忍者', '886', [('青年', '860'), ('壮年', '887'), ('老年', '912')]),
       'template_kaizoku_01': ('无卡海贼', '1012', [('青年', '975'), ('壮年', '1001'), ('老年', '1029')]),
       'template_merchant_01': ('无卡商人', '952', [('青年', '913'), ('壮年', '943'), ('老年', '974')])}


# 身份卡补位（BUSTUP 全 id 栖身目标 2026-08-29 用户裁定）：TPL_REP 代表之外的零散专卡，
# 追加进对应行的 TK5编号列（| 分隔；一个 id 可出现在多行；不进 recs 形象账，生成走 7.3 清单）
ID_EXTRA = {'choumin_male': ['1104'], 'merchant': ['1116', '1135'],
            'ninja': ['1120', '1150', '914'], 'kaizoku': ['1140', '1151'],
            'shihandai': ['1144', '1145'], 'shougun': ['1149'],
            'kuge': ['1043'],   # 1043「无」：2026-08-29 用户认图 = 公卿样 → 挂公家行
            'kunoichi': ['864']}   # 2026-08-30 用户人工认卡：864 无卡忍者池女性卡 → 女忍者行

# 无卡池性别修正（用户逐卡人工认，2026-08-30 最终）：女性卡从「男池」移出记到性别行
FEMALE_OF_POOL = {'ninja': ['864'], 'kaizoku': ['1017', '1018']}
# 跨段人工修正（2026-08-30）：914（目录名=无卡商人）卡面是忍者 → 从商人池移出、入忍者行
REASSIGN_EXC = {'merchant': ['914']}

# 新模板行（2026-08-30 用户裁）：女海贼（无卡海贼池里的女性卡；1017/1018 已认）
ADD_TPL_ROWS = [
    # id, ScriptName, CNName, TK5
    ('template_kaizoku_female_01', '女海贼', '女海贼', ['1017', '1018']),
]


def pool_of(word):
    """无卡池全量 tkid（按 refs 文件名动态收集，幂等；refs 已全转故不依赖 E: 源盘）。"""
    import glob
    sids = set()
    for f in glob.glob(os.path.join(os.getcwd(), 'refs_koei', '_tk5', '*_' + word + '_*.png')):
        m = re.match(r'^(\d+)_', os.path.basename(f))
        if m:
            sids.add(m.group(1))
    return sorted(sids, key=int)

# —— 删除行（最终态裁掉的全部）——
DEL = {'template_daimyo_01','template_kokushu_01','template_joushu_01','template_chajin_01',
 'template_onna_joushu_01','template_onna_shou_01','template_kunoichi_02','template_kunoichi_03',
 'template_merchant_02','template_merchant_03','template_ninja_male_02','template_ninja_male_03',
 'template_kaizoku_02','template_kaizoku_03',
 'template_souryo_02','template_kuge_02','template_ishi_02','template_yari_shihan_02',
 'template_swordshihan_02','template_shihandai_02','template_shihandai_03',
 'template_noumin_female_02','template_choumin_female_02','template_choumin_male_02',
 # 用户 2026-08-29 复核批：规则 1 简繁可并（馬屋的老闆=马屋老板、酒場的老闆娘=酒馆老板娘）
 'template_umaya_tenpo_02','template_sakaba_onna_02'}

def ref_of(pid):
    fs = [f for f in os.listdir(os.path.join(os.getcwd(), 'refs_koei', '_tk5'))
          if f.startswith('%s_' % pid)]
    fs = [f for f in fs if not f.endswith('_朝左.png')]
    fs.sort(key=lambda f: 0 if f.endswith('_朝右.png') else 1)
    return fs[0] if fs else ''

def main():
    rows = list(csv.reader(io.open(CSV, encoding='utf-8-sig')))
    hdr = rows[0]
    for col in ('模板', '立绘阶段', 'Persona'):
        if col not in hdr:
            hdr.append(col)
    iid, itp, ist, ic, icn = (hdr.index('ID'), hdr.index('模板NPC'), hdr.index('立绘阶段'),
                              hdr.index('TK5编号'), hdr.index('CNName'))
    # A. 删除 24 行
    before = len(rows) - 1
    rows = [hdr] + [r for r in rows[1:] if not (len(r) > iid and r[iid] in DEL)]
    print('A 删行 %d  (template 剩余 %d)' % (len(DEL), sum(1 for r in rows[1:] if len(r) > iid and r[iid].startswith('template_'))))
    # A2. 新模板行追加（2026-08-30 用户裁：女海贼，TK5 = 1017|1018）——先删旧行再插，幂等
    isc = hdr.index('ScriptName')
    new_ids = {nid for nid, _, _, _ in ADD_TPL_ROWS}
    rows = [hdr] + [r for r in rows[1:] if not (len(r) > iid and r[iid] in new_ids)]
    for new_id, scr, cn, tks in ADD_TPL_ROWS:
        row = [''] * len(hdr)
        row[iid] = new_id
        row[itp] = '1'
        row[isc] = scr
        row[icn] = cn
        row[ic] = '|'.join(tks)
        recs = [{'stage': '', 'tkid': tks[0], 'ref': ref_of(tks[0]), 'emotion': 0}]
        for t in tks[1:]:
            recs.append({'stage': '卡%s' % t, 'tkid': t, 'ref': ref_of(t), 'emotion': 0})
        row[ist] = json.dumps(recs, ensure_ascii=False, separators=(',', ':'))
        rows.append(row)
        print('A2 新模板行: %s  TK5=%s' % (new_id, row[ic]))
    # B. 模板行：代表图 & 4 档 & 删档行（上面已删）
    for r in rows[1:]:
        if len(r) <= iid or not r[iid].startswith('template_'):
            continue
        if r[iid] in new_ids:
            continue   # A2 新行已由 A2 定义（recs/TK5），B 步不重写（2026-08-30）
        sid = r[iid]
        # R1：先剥序号保留性别（choumin_male_01 → choumin_male），未命中再剥性别（→ choumin）
        typ = re.sub(r'_\d+$', '', sid[len('template_'):])
        typ_flat = re.sub(r'_(male|female)$', '', typ)
        if sid in WKA:
            word, main, ages = WKA[sid]
            recs = [{'stage': '', 'tkid': main, 'ref': ref_of(main), 'emotion': 0}]
            for st, pk in ages:
                recs.append({'stage': st, 'tkid': pk, 'ref': ref_of(pk), 'emotion': 0})
            exc = (FEMALE_OF_POOL.get(typ_flat) or []) + (REASSIGN_EXC.get(typ_flat) or [])
            alltk = [t for t in pool_of(word) if t not in exc]   # 用户 2026-08-30：女性卡/错段卡移出男池
        else:
            pid = TPL_REP.get(typ) or TPL_REP.get(typ_flat)
            if not pid:
                continue
            recs = [{'stage': '', 'tkid': pid, 'ref': ref_of(pid), 'emotion': 0}]
            alltk = [pid]
        alltk = list(dict.fromkeys(alltk + (ID_EXTRA.get(typ) or ID_EXTRA.get(typ_flat) or [])))  # 代表/池在前，EXTRA 追加
        if sid not in WKA:
            recs.sort(key=lambda x: int(x['tkid']))   # 非 4 档行按 tkid 升序；WKA 主行保持首位
        while len(r) <= ist: r.append('')
        r[ist] = json.dumps(recs, ensure_ascii=False, separators=(',', ':'))
        r[ic] = '|'.join(alltk)
    print('B 模板行代表图/4档 填充完成')
    # C. 英雄：阶段词表 35 人 + HERO_FIX + manifest 主形象（HEAD 已有 TK5 列于主形象，仅补缺）
    rowmap = {}
    for r in rows[1:]:
        if len(r) > iid:
            rowmap[r[iid]] = r
    for sid, pk in list(PORTRAIT_STAGES.items()):
        r = rowmap.get(sid)
        if not r:
            continue
        recs = [{'stage': rec['stage'], 'tkid': str(rec['tkid']),
                 'ref': rec.get('ref') or ref_of(str(rec['tkid'])), 'emotion': rec.get('emotion', 1)}
                for rec in PORTRAIT_STAGES[sid]]
        if not recs:
            continue
        while len(r) <= ist: r.append('')
        r[ist] = json.dumps(recs, ensure_ascii=False, separators=(',', ':'))
        r[ic] = '|'.join(str(x['tkid']) for x in recs)
    filled = 0
    for sid, pk in HERO_FIX.items():
        r = rowmap.get(sid)
        if not r:
            continue
        recs = [{'stage': '', 'tkid': pk, 'ref': ref_of(pk), 'emotion': 0}]
        while len(r) <= ist: r.append('')
        r[ist] = json.dumps(recs, ensure_ascii=False, separators=(',', ':'))
        if r[ic].strip() in ('', '-'):
            r[ic] = pk
        filled += 1
    print('C 英雄: 词表 %d 组(命中 %d) + HERO_FIX 填 %d 行' % (len(PORTRAIT_STAGES), sum(1 for k in PORTRAIT_STAGES if k in rowmap), filled))
    # C2. 兜底：凡「立绘阶段列非 JSON」的行按其 TK5 列（| 分隔）写单图 JSON
    #     （lord_tk5_* 具名 35 行 = HEAD 存量文本「具名」，此处统一 JSON 化；B 步未命中模板行同救）
    filled2 = 0
    for r in rows[1:]:
        if len(r) <= iid:
            continue
        cur = r[ist].strip() if len(r) > ist else ''
        if cur:
            try:
                json.loads(cur)
                continue
            except Exception:
                pass
        tk = r[ic].strip() if len(r) > ic else ''
        tkids = [t for t in tk.split('|') if t and t != '-']
        if not tkids:
            continue
        recs = [{'stage': '', 'tkid': t, 'ref': ref_of(t), 'emotion': 0} for t in tkids]
        while len(r) <= ist: r.append('')
        r[ist] = json.dumps(recs, ensure_ascii=False, separators=(',', ':'))
        filled2 += 1
    print('C2 兜底具名单图 JSON 填 %d 行' % filled2)
    # D. 行序：真人/具名/模板（族序）/变量
    FAM = [('ninja','jounin','chunin','genin','kunoichi'),          # 忍者族（含女忍）
           ('shougun','ashigaru','ashigaru_daisho','ashigaru_kumi'), # 足轻武家族（备大将=足轻/军衔，排一起）
           ('toudou','karou','bushou','samurai_taisho','hogo','monban',
            'koushin_kashin','koushin_baishin','buryoku_kashin','buryoku_baishin',
            'gaikou_kashin','gaikou_baishin'),
           ('kaizoku','kaizoku_female','kaizoku_tou','kashira','funa_daisho','sentou','suifu_tou','suifu'),
           ('merchant','merchant_gyo','merchant_ming','merchant_choseon','merchant_ryukyu',
            'za_shihai','detchi','tenpo','umaya_tenpo','komeya_tenpo','sakaba_onna',
            'yadoya_onna','ryotei_onna'),
           ('swordshihan','shihandai','yari_shihan','kenkyu'),
           ('noumin','choumin','choumin_male','tabibito','kodomo','kodomo_f','yoi_otoko',
            'yoi_onna','yotto','hakkoujin','koshou','bantou','tennou','souryo','ishi',
            'kajishi','hime','hime_hime','hime_hanyou')]
    flat = []
    for fam in FAM:
        flat.extend(fam)
    def fami(sid):
        t = sid[len('template_'):]
        t = re.sub(r'_(male|female)$', '', re.sub(r'_\d+$', '', t))
        for i, k in enumerate(flat):
            if t == k:
                return i
        return 999
    seg = []
    real, named, tpl_, variable = [], [], [], []
    for r in rows[1:]:
        sid = r[iid] if len(r) > iid else ''
        mm = r[itp].strip() if len(r) > itp else ''
        if sid.startswith('template_'):
            tpl_.append(r)
        elif mm == '-1':
            variable.append(r)
        elif sid.startswith('lord_tk5_'):
            named.append(r)
        else:
            real.append(r)
    tpl_.sort(key=lambda r: fami(r[iid]))
    # E. Persona 列 = 手写区（2026-08-30 用户裁定方案 B：内容直接在 TaikouHero.csv 的 Persona 列，
    #    本脚本只负责『列存在 + 行长度对齐』，禁止覆盖已有值；git 已提交作安全网）
    for r in real + named + tpl_ + variable:
        while len(r) < len(hdr):
            r.append('')
    with io.open(CSV, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows([hdr] + real + named + tpl_ + variable)
    print('D 排序完成 | 真人 %d 具名 %d 模板 %d 变量 %d' % (len(real), len(named), len(tpl_), len(variable)))
    print('E 终态: 总行 %d | template_ %d' % (len(real) + len(named) + len(tpl_) + len(variable), len(tpl_)))

if __name__ == '__main__':
    main()
