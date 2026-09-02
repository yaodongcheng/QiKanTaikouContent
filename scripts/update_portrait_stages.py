# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""立绘阶段/情绪 → 主源 CSV（TaikouHero.csv）新列「立绘阶段」，2026-08-29 用户裁定。

列含义（一单元格 = 一个 JSON 数组，一条 = 一个形象阶段）：
  [{"stage":"若君","tkid":"1154","ref":"1154_织田信长_朝右.png","emotion":1}, ...]
  字段：stage   阶段词（TK5 时期名/身份词；普通单图人物 = ""）
        tkid    TK5 BUSTUP 编号（决定 refs_koei/_tk5 取图路径）
        ref     已转好的朝右底稿文件名（manifest 产物；A 版无底图 = ""）
        emotion 该阶段是否做 4 情绪态（1/0；前 50 热门裁定）
行规则：多阶段人物 = 多条；前 50 热门单图人物 = 1 条 stage=""；其余人该列留空。
用法：python update_portrait_stages.py [--dry]   # --dry 只打印不落盘
"""
import csv, io, json, sys

CSV = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
       'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv')
COL = '立绘阶段'


def dumps(records):
    """records: list[dict] 带中文 → JSON 字符串（保证 ensure_ascii=False，圆括号安全）。"""
    return json.dumps(records, ensure_ascii=False, separators=(',', ':'))


# 数据源：35 人多阶段词表 + 前 50 热门情绪标记。词表 = 读图核验产物（2026-08-29 用户全收）。
# ref = 阶段底稿转置产物文件名 {tkid}_{BUSTUP目录名}_朝右.png（阶段转置批次按此清单生成）。
def S(stage, tkid, ref='', emotion=1):
    return {'stage': stage, 'tkid': tkid, 'ref': ref, 'emotion': emotion}

PORTRAIT_STAGES = {
    'lord_1_oda': [S('若君', '1154', '1154_织田信长_朝右.png'), S('上洛', '195', '195_织田信长_朝右.png')],
    'lord_1_kinoshita': [S('藤吉郎', '1172'), S('羽柴', '517', '517_丰臣秀吉_朝右.png'),
                         S('秀吉', '1173'), S('太阁', '1174')],
    'lord_1_sanada_9': [S('出阵', '361'), S('朝', '1162')],
    'lord_1_akechi': [S('军', '14'), S('朝', '1152')],
    'lord_1_ishida_mitsunari': [S('奉行', '75'), S('关原', '1153')],
    'lord_1_katoo_kiyomasa': [S('文', '230'), S('藩', '1155')],
    'lord_1_gamou_2': [S('军', '240'), S('朝', '1156')],
    'lord_1_kuki': [S('海', '279'), S('将', '1157')],
    'lord_1_kuroda_iekata': [S('军师', '292'), S('隐', '1158')],
    'lord_1_konishi_yukinaga': [S('十字', '312'), S('奉行', '1159')],
    'lord_1_kobayakawa_takakage': [S('威', '314'), S('常', '1160')],
    'lord_1_sanada_6': [S('谋', '359'), S('老', '1161')],
    'lord_1_shibata': [S('鬼', '379'), S('越前', '1163')],
    'lord_1_shima_sakon': [S('清兴', '1164'), S('左近', '386')],
    'lord_1_shimazu': [S('藩', '394'), S('督', '1165')],
    'lord_1_shimazu_4': [S('侍', '395'), S('鬼', '1166')],
    'lord_1_takenaka_hanbee': [S('计', '455'), S('卿', '1167')],
    'lord_1_date_6': [S('奥州', '466'), S('阵', '1168')],
    'lord_1_todo_2': [S('文', '499'), S('武', '1169')],
    'lord_1_naoe_kanetsugu': [S('爱', '526'), S('书', '1175')],
    'lord_1_ruzon_sukezaemon': [S('商', '549'), S('绅', '1176')],
    'lord_1_hattori_hanzo': [S('侍', '587'), S('忍', '1177')],
    'lord_1_fukushima_masanori': [S('阵', '615'), S('素', '1178')],
    'lord_1_honda': [S('枪', '652'), S('斗', '1179')],
    'lord_1_maeda_keiji': [S('倾奇', '657'), S('若', '1180')],
    'lord_1_maeda': [S('枪', '659'), S('藩', '1181')],
    'lord_1_miyamotoo_musashi': [S('行', '700'), S('名', '1182')],
    'lord_1_murakami': [S('水', '714'), S('海', '1183')],
    'lord_1_mogami_2': [S('出羽', '723'), S('大', '1184')],
    'lord_1_yamanaka_shikanosuke': [S('志', '756'), S('战', '1185')],
    'lord_1_kawano_masashige': [S('通', '300'), S('直', '1234')],
    'lord_1_kawano_2': [S('通', '300'), S('直', '1234')],
    'lord_1_kinoshita_4': [S('文', '1170'), S('城', '1171'), S('老', '516')],  # 丰臣秀长 3 图
    'lord_1_kinoshita_1': [S('若', '1047'), S('政', '1186')],  # 宁宁
    'lord_1_anaka': [S('白', '1048'), S('贵', '1187')],  # 阿中
}


def main():
    dry = '--dry' in sys.argv
    rows = list(csv.reader(io.open(CSV, encoding='utf-8-sig')))
    if not rows:
        raise SystemExit('CSV 为空：%s' % CSV)
    hdr = rows[0]
    col = hdr.index(COL) if COL in hdr else len(hdr)
    if col == len(hdr):
        hdr.append(COL)
    id_col = hdr.index('ID') if 'ID' in hdr else 0
    hit, missing = 0, []
    for r in rows[1:]:
        if len(r) < id_col + 1 or not r[id_col]:
            continue
        recs = PORTRAIT_STAGES.get(r[id_col])
        if recs is None:
            continue
        while len(r) <= col:
            r.append('')
        r[col] = dumps(recs)
        hit += 1
    have = {x[id_col] for x in rows[1:] if len(x) > id_col}
    for k in PORTRAIT_STAGES:
        if k not in have:
            missing.append(k)
    if missing:
        raise SystemExit('主源 CSV 找不到这些 ID：%s' % missing)
    if dry:
        for r in rows[1:]:
            if len(r) > col and r[col]:
                print(r[id_col], '->', r[col][:120])
        print('DRY 完成 %d 行' % hit)
        return
    with io.open(CSV, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows(rows)
    print('CSV 主源已更新：%s 列（idx=%d），填充 %d 行' % (COL, col, hit))


if __name__ == '__main__':
    main()
