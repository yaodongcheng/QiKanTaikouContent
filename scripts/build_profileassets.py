# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""最终资源分发（2026-08-30 用户定稿）：ProfileImage.csv + 规范化图标资源。

输入：_review/picktkid.json（chosen=用户认证的成品）+ selected/（= 用户选定+镜像，2026-08-30 末定：源头）；
      兜底 raw/（selected 缺时）。
产出：ArtSource/ProfileImage/{tkid}_{StringId}_bustup_normal.png   （半透明立绘 512x768，matte+place 贴底）
      ArtSource/ProfileImage/{tkid}_{StringId}_minihead_normal.png （方形小头像 256x256，上部 512 裁切）
      Knowledge/骑砍2织丰角色ID对应/csv/ProfileImage.csv（tkid, StringId, bustup路径, minihead路径）
命名规范（用户定）：{tkid}_{StringId}_bustup|minihead_{emotion}.png；emotion 当前全 normal。
CSV 路径 = Portraits/…（2026-08-30 用户定：图归补充包 ShokuhoTaikouExpansionPack/Portraits/，csv 暂留织丰目录；搬运后路径一致）。
用法：python build_profileassets.py [--limit N] [--tid 517,1048] [--force]
"""
import csv, io, json, os, re, sys
from PIL import Image

MATTE = __import__('matte_rembg')          # rembg isnet-general-use → 512x768 RGBA
OUT = 'ProfileImage'
CSV_OUT = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
           'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/ProfileImage.csv')
PICKTKID = '_review/picktkid.json'
CSV = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
       'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv')
MINI_W, MINI_H = 256, 256
CSV_PREFIX = 'ProfileImage/'   # CSV 行路径 = 产物目录相对路径（2026-08-30 晚用户定：图片终版 = ArtSource/ProfileImage/ 原位，不搬运）


def main():
    limit = 0
    only = set()
    force = '--force' in sys.argv          # --force = 全部重抠（2026-08-30 全量修版：alpha_matting 产雾，改 plain）
    mini_only = '--minihead-only' in sys.argv   # --minihead-only = 只重做 minihead（bustup 已合法；眼锚 v3 用）
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    if '--tid' in sys.argv:
        only = set(sys.argv[sys.argv.index('--tid') + 1].split(','))
    from PIL import Image
    st = json.load(open(PICKTKID, encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    rows = []
    qcs = []
    metas = []          # minihead 锚点元数据（复核闸：level>=1 = 降级锚，必审）
    done = 0
    for t, v in sorted(st.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0):
        if not isinstance(v, dict) or not v.get('chosen'):
            continue
        if only and t not in only:
            continue
        if limit and done >= limit:
            break
        sid = v.get('sid') or ''
        src = os.path.join('selected', '%s_%s.png' % (t, sid))
        if not os.path.exists(src):          # 兜底：selected 缺（未重收集）→ raw 选定图
            src = os.path.join('raw', v['chosen'])
        if not os.path.exists(src):
            print('!! 源缺失 %s' % src)
            continue
        bname = '%s_%s_bustup_normal.png' % (t, sid)
        mname = '%s_%s_minihead_normal.png' % (t, sid)
        bpath = os.path.join(OUT, bname)
        mpath = os.path.join(OUT, mname)
        qc = None
        if force or not os.path.exists(bpath) or Image.open(bpath).size != (512, 768):
            # alpha_matting=False：2026-08-30 全量发现 matting 在部分图产灰雾（797 实证），plain 视觉更干净
            rgba = MATTE.matte(src, alpha_matting=False)  # rembg 抠图（无尺寸约束）
            qc = MATTE.place(rgba, bpath)                 # 紧贴裁切 → 512x768 水平居中贴底（P5 布局）
        # 眼锚（v4 三级）：0=mediapipe 眼锚 / 1=cv2 / 2=alpha 顶带引导；元数据写 minihead_meta.csv
        if mini_only or force or not os.path.exists(mpath) or Image.open(mpath).size != (MINI_W, MINI_H):
            lvl, ed, mcx, mcy, mside = MATTE.build_minihead(src, mpath, alpha_path=bpath)
            metas.append([t, sid, 'normal', lvl, int(ed), int(mcx), int(mcy), int(mside)])
        rows.append([t, sid, CSV_PREFIX + bname, CSV_PREFIX + mname])
        if qc:
            qcs.append((t, sid, qc))
        done += 1
    if rows:
        with io.open(CSV_OUT, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['tkid', 'StringId', 'bustup', 'minihead'])
            w.writerows(rows)
    if qcs:
        # QC 汇总（计划 §三 待办 1 抽查项）：均值 + 异常清单（不透明过低/破洞过多/人物过窄/头占比超标）
        import statistics as _st
        print('--- 全量质检汇总（%d 张 bustup）---' % len(qcs))
        for key, idx in (('opaque', '不透明占比'), ('holes', '半透明破洞')):
            vals = [q[key] for _, _, q in qcs if q[key] is not None]
            if vals:
                print('%-12s 均值 %.3f（范围 %.3f~%.3f）' % (idx, _st.mean(vals), min(vals), max(vals)))
        # 判据说明（2026-08-30 plain 版定稿）：holes(内部半透明比) 对 plain 是 soft-alpha 固有分布
        # （797 实证：视觉干净但 0.67），不再作好坏判据；只留视觉类硬指标。
        bad = [(t, sid, q) for t, sid, q in qcs
               if q.get('opaque', 1) < 0.35 or q.get('fill_w', 1) < 0.35 or q.get('head_ok') is False]
        if bad:
            print('异常 %d 张（需人工复核）：' % len(bad))
            for t, sid, q in bad:
                print('  tkid=%s sid=%s %s' % (t, sid, q))
    if metas:
        meta_path = os.path.join(OUT, 'minihead_meta.csv')
        with io.open(meta_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['tkid', 'StringId', 'emotion', 'anchor_level', 'head_len', 'cx', 'cy', 'side'])
            w.writerows(metas)
        bad_lvl = [m for m in metas if int(m[3]) >= 1]
        print('minihead 锚层：level0=%d 降级锚=%d（level>=1 必审）' % (len(metas) - len(bad_lvl), len(bad_lvl)))
        for m in bad_lvl:
            print('  !! 降级锚 tkid=%s sid=%s level=%s' % (m[0], m[1], m[3]))
    print('ProfileImage 资源：%d 张（bustup 半透明 512x768 + minihead 256x256）'
          '，表 -> %s' % (done, CSV_OUT))


if __name__ == '__main__':
    main()
