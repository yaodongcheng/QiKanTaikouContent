# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""ProfileImage 分发：ArtSource/ProfileImage/ → 补充包 ShokuhoTaikouExpansionPack/Portraits/

2026-08-30 用户定：图归补充包（世界观的肉 = 内容包资产）；CSV 暂留织丰目录
（Knowledge/骑砍2织丰角色ID对应/csv/ProfileImage.csv，功能稳定后再搬）。
数据来源 = ProfileImage.csv（唯一事实）——按 CSV 每行的 bustup/minihead 路径逐文件复制，
复制后校验尺寸（bustup 512x768 / minihead 256x256），缺失或尺寸错 = 报错清单。
用法：python deploy_portraits.py
"""
import csv, io, os, shutil
from PIL import Image

CSV_OUT = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
           'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/ProfileImage.csv')
DEST_ROOT = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
             'ShokuhoTaikouExpansionPack/Portraits')
SRC_ROOT = 'ProfileImage'


def main():
    rows = list(csv.reader(io.open(CSV_OUT, encoding='utf-8-sig')))
    header = rows[0]
    assert header == ['tkid', 'StringId', 'bustup', 'minihead'], 'CSV 表头不符：%s' % header
    ok = bad = skipline = 0
    bad_lines = []
    for r in rows[1:]:
        if len(r) != 4:
            skipline += 1
            bad_lines.append('行数异常 %s' % r)
            continue
        tkid, sid, bustup, minihead = r
        for col, size in ((bustup, (512, 768)), (minihead, (256, 256))):
            src = os.path.join(SRC_ROOT, col.split('/', 1)[-1])
            dst = os.path.join(DEST_ROOT, col.split('/', 1)[-1])
            if not os.path.exists(src):
                bad += 1
                bad_lines.append('源缺失 %s（CSV 行 tkid=%s）' % (col, tkid))
                continue
            if os.path.exists(dst) and Image.open(dst).size == size:
                ok += 1
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            if Image.open(dst).size != size:
                bad += 1
                bad_lines.append('尺寸异常 %s（%s）' % (dst, Image.open(dst).size))
            else:
                ok += 1
    print('分发完成：%d 个文件到 %s' % (ok, DEST_ROOT))
    if bad_lines:
        print('异常 %d 条：' % (bad + skipline))
        for x in bad_lines:
            print('  ' + x)
    else:
        print('全部通过（无缺失/无尺寸异常）')


if __name__ == '__main__':
    main()
