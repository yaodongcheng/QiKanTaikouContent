# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""
光荣形象描述 → 太阁数据主源 CSV（Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv）。

2026-08-28 数据源裁定：主源 = Knowledge/.../csv/（用户让其他 agent 从 xlsx 导出的最新版），
xlsx 退役为归档（不再维护）。该 CSV 已有「外观描述_光荣」中文列（其他 agent 导出时保留了
xlsx 列名），本脚本按 ID 填充/刷新，幂等可重跑。XML 手术改 xlsx 的旧逻辑已删除（铁律 22：
主源是 CSV，直接编辑 + git diff 审计）。

用法：python update_appearance.py
"""
import csv, io, os

CSV = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
       'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv')
COL_XL = '外观描述_光荣'
COL_CSV = 'AppearanceKoei'  # 兼容旧 Debug/xlsx_dump 命名（已弃用，仅兜底）

# 试跑五人。描述 = 从太阁5（BUSTUP 立绘，E:/taikou5/TaikouImage 编号_姓名）视觉特征提炼定稿；
# 信长/幸村各有两形象（195/1154、361/1162），按本作年龄取盛年武者相。
DESCRIPTIONS = {
    'lord_1_oda': ('光荣版经典形象（太阁5）：俊朗冷峻的英主，黑甲配绯红大披风，'
                   '束发髻，蓄黑短须与唇髭，眼神锐利睥睨，枭雄气概'),
    'lord_1_kinoshita': ('光荣版经典形象（太阁5）：头戴白色钵卷，月代后髻扎小马尾，'
                         '尖瘦猴脸、二十岁上下的青年，眉目机灵带笑，眼色深藏精明；'
                         '茶褐色肩衣，精气神十足，容光焕发、无皱纹无老态'),
    'lord_1_sanada_9': ('光荣版经典形象（太阁5）：青年武者，赤红具足配鹿角形兜盔与红缨，'
                        '胸甲缀六文钱家纹，执长枪，浓眉重目、英气凛冽，意气风发'),
    # 女性（阿市/訚千代主源数据不全，参数见 run_trial FEMALE_OVERRIDES）
    'lord_1_azai_1': ('光荣版经典形象（太阁5）：黑长发披肩，面容白皙清丽，神态温婉沉静；'
                      '浅樱纹小袖与青绿丝带，端庄娴静的战国第一美人'),
    'lord_1_bekki_2': ('光荣版经典形象（太阁5）：额束白色钵卷，棕发束髻，'
                       '着青绿挂甲，眉目英气坚定、神情飒爽，巾帼风姿'),
}


def main():
    rows = list(csv.reader(io.open(CSV, encoding='utf-8-sig')))
    if not rows:
        raise SystemExit('CSV 为空：%s' % CSV)
    hdr = rows[0]
    col = hdr.index(COL_XL) if COL_XL in hdr else (hdr.index(COL_CSV) if COL_CSV in hdr else None)
    if col is None:
        hdr.append(COL_XL)
        col = len(hdr) - 1
    id_col = hdr.index('ID') if 'ID' in hdr else 0
    hit = 0
    for r in rows[1:]:
        if len(r) < id_col + 1 or not r[id_col]:
            continue
        if r[id_col] in DESCRIPTIONS:
            while len(r) <= col:
                r.append('')
            r[col] = DESCRIPTIONS[r[id_col]]
            hit += 1
    missing = [k for k in DESCRIPTIONS if k not in {x[id_col] for x in rows[1:] if len(x) > id_col}]
    if missing:
        raise SystemExit('主源 CSV 里找不到这些 ID：%s' % missing)
    with io.open(CSV, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows(rows)
    print('CSV 主源已更新：%s 列 = %s，填充 %d 行' % (COL_XL, col, hit))


if __name__ == '__main__':
    main()
