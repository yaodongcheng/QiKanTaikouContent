# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""台账迁移（2026-08-30 用户设计裁定）：审批记录 → 按底稿卡（tkid）新增 _review/picktkid.json。

新结构（键 = tkid，值 = 该卡的审批意见）：
  {"913": {"sid": "template_merchant_01", "cn": "无卡商人",
           "chosen": "tk913_无卡商人_R2.png", "mirror": 0,
           "dropped": false, "redraw": "", "legacyA": false}, ...}
  chosen  选定的成品文件名（空 = 未定）
  dropped 已作废
  redraw  待重生成注意点（非空 = redraw）
  legacyA 旧 A 版（无底稿时代）选定，仅留档不参与新审批

迁移三源：老 picks.json（行级）→ 每行选定/作废反查卡；redraw.json（复合键）→ 卡级 redraw；
A 版（无 tkid 映射）→ 挂行首卡 + legacyA 标记（用户「昨天审的不废弃」）。
新文件是之后窗口/跑批的唯一依据；picks.json/redraw.json 已迁移完毕、留档只读。
🔴 本脚本为一次性迁移工具（2026-08-30 已执行）；此后红标增删一律改 picktkid.json，不要再跑本脚本（会覆盖窗口新改动）。
用法：python build_picktkid.py [--dry]
"""
import csv, io, json, os, re, sys

CSV = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
       'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv')
OUT = '_review/picktkid.json'
LEGACY = '_review/legacy_a.json'
PICKS = '_review/picks.json'
REDRAW = '_review/redraw.json'
LOG = 'build_log.csv'


def main():
    dry = '--dry' in sys.argv
    # —— CSV：行 → TK5 首卡 / 卡 → 首栖身行 ——
    tk_of, hosp, cn_of = {}, {}, {}
    with io.open(CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            sid = r.get('ID', '')
            cn_of[sid] = r.get('CNName', '')
            first = ''
            for t in (r.get('TK5编号') or '').split('|'):
                t = t.strip()
                if t.isdigit():
                    if not first:
                        first = t
                    hosp.setdefault(t, sid)
            if first:
                tk_of[sid] = first
    # —— build_log：key → ref 卡（行级选定/阶段反查）——
    ref_tk = {}
    with io.open(LOG, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            k = r.get('key', '')
            m = re.match(r'^(\d+)_', (r.get('ref') or '').split('/')[-1])
            if m:
                ref_tk.setdefault(k, m.group(1))

    def tid_of_sid(sid, pref=None):
        """行级记录的卡：file 前缀 > build_log ref > CSV 首卡。"""
        if pref:
            return pref
        return ref_tk.get(sid) or tk_of.get(sid)

    rec = {}
    picks = json.load(open(PICKS, encoding='utf-8'))
    for sid, p in picks.items():
        f = p.get('file') or ''
        m = re.match(r'^tk(\d+)_', f)
        tid = m.group(1) if m else tid_of_sid(sid)
        if not tid:
            continue
        r = rec.setdefault(tid, {'sid': hosp.get(tid, sid), 'cn': cn_of.get(sid, ''), 'mirror': 0})
        if f:
            r['chosen'] = f
            r['mirror'] = int(bool(p.get('mirror')))
            r['legacyA'] = bool('_A' in f)          # A 版图（无底稿时代产物）= 仅留档，不参与卡级新审批
        if p.get('bad'):
            for b in p['bad']:
                mm = re.match(r'^tk(\d+)_', b)
                bt = mm.group(1) if mm else tid
                bt_sid = sid.split('#')[0]          # 阶段 key 剥 # 后查姓名/宿主（2026-08-30 修）
                rb = rec.setdefault(bt, {'sid': hosp.get(bt, bt_sid), 'cn': cn_of.get(bt_sid, ''), 'mirror': 0})
                rb['dropped'] = True
    # —— redraw（复合键）→ 卡级 ——（🔴 每分支显式命名 sid，防止借上段循环残留变量：2026-08-30）
    redraw = json.load(open(REDRAW, encoding='utf-8'))
    for ck, note in redraw.items():
        tids = []
        if '#' not in ck:
            r_side, tks = ck, []
            with io.open(CSV, encoding='utf-8-sig') as f:
                for r in csv.DictReader(f):
                    if r.get('ID') == r_side:
                        tks = [t for t in (r.get('TK5编号') or '').split('|') if t.isdigit()]
                        break
            tids = tks
            r_sid = r_side
        else:
            r_sid, sub = ck.split('#', 1)
            if sub.startswith('tk'):
                tids = [sub[2:]]
            else:
                t = ref_tk.get(ck) or ref_tk.get(r_sid)
                tids = [t] if t else []
        for t in tids:
            r = rec.setdefault(t, {'sid': hosp.get(t, r_sid), 'cn': cn_of.get(r_sid, ''), 'mirror': 0})
            r['redraw'] = note
    # 兜底补全缺名/宿主（hosp 反查，幂等；阶段/作废分支偶发遗漏时在此回填）
    for t, r in rec.items():
        if t in hosp:
            r['sid'] = r.get('sid') or hosp[t]
            if not r.get('cn'):
                r['cn'] = cn_of.get(hosp[t], '')
    legacy_a = [{'key': k, 'file': v.get('file')} for k, v in picks.items()
                if v.get('file') and '_A' in v.get('file', '')]
    legacy_a = [{'key': k, 'file': v.get('file')} for k, v in picks.items()
                if v.get('file') and '_A' in v.get('file', '')]
    if not dry:
        with io.open(OUT, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        with io.open(LEGACY, 'w', encoding='utf-8') as f:
            json.dump(legacy_a, f, ensure_ascii=False, indent=1)
    chosen = sum(1 for v in rec.values() if v.get('chosen'))
    dropped = sum(1 for v in rec.values() if v.get('dropped'))
    red_n = sum(1 for v in rec.values() if 'redraw' in v)
    legacy = sum(1 for v in rec.values() if v.get('legacyA'))
    print('picktkid: %d 个卡 | 已选定 %d | 作废 %d | redraw %d | legacyA %d'
          % (len(rec), chosen, dropped, red_n, legacy))
    print('A 版遗留存档: %d 条 -> %s' % (len(legacy_a), LEGACY))


if __name__ == '__main__':
    main()
