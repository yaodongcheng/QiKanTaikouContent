# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""身份 → TK5 通用底稿映射（2026-08-28：29 类身份各配一张身份型代表图）。

来源：E:/taikou5/TaikouImage/BUSTUP（本机真源，gitignore 不入库），转换件在
refs_koei/_tk5/identity/{编号}_{姓名}_{朝左/朝正}.png —— 用了哪张 = 本表唯一事实源；
2026-08-28 文件名带朝向（用户裁定：文件名即为第一视角，_朝左 = 实测脸朝画面左，生成构图需镜像）。
注意：TK5 通用立绘只有一批固定类型；表格里标注「借」的 = 就近借用到相邻身份，
「缺」的 = TK5 无该身份通用立绘（如大名/茶人），走纯描述版或借用实名人物底稿。
"""
import os

IDENTITY_REF = {
    # —— 武家 ——
    '大名':     None,      # 缺：TK5 无通用大名（全是实名；实名角色走各自底稿）
    '国主':     None,      # 缺：同上
    '城主':     None,      # 缺：同上（邻近 = 备大将 1121）
    '当家':     '1121_备大将_朝左.png',      # 借：武将当主 = 具足+太刀
    '家老':     '1121_备大将_朝左.png',      # 借
    '部将':     '1121_备大将_朝左.png',      # 同类型统一一张（2026-08-28 用户裁定：一个类型一张）
    '侍大将':   '1121_备大将_朝左.png',      # 借
    '足轻大将': '1121_备大将_朝左.png',      # 借
    '足轻组头': '1121_备大将_朝左.png',      # 借：TK5 无足轻通用立绘（士兵不占立绘槽）
    '浪人':     '1118_剑术教头_朝正.png',    # 借：无主剑客脸（TK5 无浪人槽；可换 1141 枪术教头）
    # —— 忍者（上中下忍统一一张）——
    '上忍':     '886_无卡忍者_朝正.png',
    '中忍':     '886_无卡忍者_朝正.png',
    '下忍':     '886_无卡忍者_朝正.png',
    # —— 剑术 ——
    '师范':     '1118_剑术教头_朝正.png',
    '师范代':   '1139_代理教头_朝左.png',
    '见习':     '1139_代理教头_朝左.png',    # 同类型统一一张
    # —— 海贼/山贼（船系统一一张）——
    '头领':     '1148_海贼头目_朝左.png',
    '头目':     '1147_山贼头目_朝左.png',
    '船大将':   '1012_无卡海贼_朝左.png',    # 借：海贼土着头目脸
    '船头':     '1012_无卡海贼_朝左.png',    # 借：同类型统一一张
    '水夫头':   '1012_无卡海贼_朝左.png',    # 借
    '水夫':     '1012_无卡海贼_朝左.png',    # 借
    # —— 町/商 ——
    '掌柜':     '1136_掌柜_朝左.png',
    '伙计':     '1143_男仆_朝左.png',        # 借：年轻帮手
    '商人':     '952_无卡商人_朝右.png',
    '锻冶匠':   '1137_锻冶匠_朝左.png',
    '医师':     '1138_医师_朝左.png',
    '僧侣':     '1117_僧侣_朝左.png',
    '茶人':     None,      # 缺：TK5 无茶人槽（茶人多实名）
    '公家':     '1119_公家_朝左.png',
    '无效':     '1112_农民男_朝左.png',      # 无身份平民
}

DIR = 'refs_koei/_tk5/identity'

# 底稿朝向标注（2026-08-28 全量实测 + 感知校准：近正图 mediapipe 鼻偏不可靠，以用户肉眼为准；
# 测量源 = refs_koei/_tk5/orientation.json，重测 = python annotate_orient.py）
ORIENTATION = {
    '1012_无卡海贼_朝左.png': 'LEFT', '1027_无卡海贼_朝左.png': 'LEFT',
    '1112_农民男_朝左.png': 'LEFT', '1117_僧侣_朝左.png': 'LEFT',
    '1118_剑术教头_朝正.png': 'FRONT', '1119_公家_朝左.png': 'LEFT',
    '1121_备大将_朝左.png': 'LEFT', '1136_掌柜_朝左.png': 'LEFT',
    '1137_锻冶匠_朝左.png': 'LEFT', '1138_医师_朝左.png': 'LEFT',
    '1139_代理教头_朝左.png': 'LEFT', '1143_男仆_朝左.png': 'LEFT',
    '1144_代理教头_朝左.png': 'LEFT', '1147_山贼头目_朝左.png': 'LEFT',
    '1148_海贼头目_朝左.png': 'LEFT', '1149_备大将_朝左.png': 'LEFT',
    '883_无卡忍者_朝左.png': 'LEFT', '886_无卡忍者_朝正.png': 'FRONT',
    '891_无卡忍者_朝左.png': 'LEFT', '952_无卡商人_朝右.png': 'RIGHT',
}


def ref_for(identity):
    """返回身份底稿绝对路径；无匹配返回 None（纯描述版）。"""
    fn = IDENTITY_REF.get(identity)
    if not fn:
        return None
    p = os.path.join(DIR, fn)
    return p if os.path.exists(p) else None
