# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""选图决策器 v3（2026-08-30 用户设计裁定）—— 按底稿卡（tkid）审批。

记录单位 = 一张底稿卡（tkid）：每卡 = 一个审批位（chosen 选定 / dropped 作废 / redraw 待重生成+意见）。
唯一台账 = _review/picktkid.json（键 = tkid；picks.json/redraw.json 已是旧档只读）。
无底稿的图（A 版）不进入审批队列（避免「没有底稿还出图被审」）。
筛选三态：全部 / 只看未审 / 只看待重生成（待重生成的卡显示标记时留的意见）。
窗口 = 左：底稿参考 ｜ 右：候选大图 ｜ 下：候选缩略条（7 张/页）＋按钮行。
用法：python pick_gui.py
"""
import csv, glob, io, json, os, re, tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk

PICKTKID = '_review/picktkid.json'
CSV = ('h:/SteamLibrary/steamapps/common/Mount & Blade II Bannerlord/Modules/'
       'LivingWorldNpcs/Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv')
W, H = 1120, 860
KW__, KH__ = 250, 340
CW, CH = 700, 560
TH, TW = 150, 120


def load_state():
    return (json.load(open(PICKTKID, encoding='utf-8'))
            if os.path.exists(PICKTKID) else {})


def save_state(st):
    os.makedirs('_review', exist_ok=True)
    with io.open(PICKTKID, 'w', encoding='utf-8') as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def load_cards():
    """按卡条目：每张底稿卡（tkid / 阶段 sid#stage 归一到 tid）→ 候选（该卡生成的所有 raw 图）。
    A 版行（无 ref tkid）不进队列。红标卡即使暂无候选也建条目（显示「待重跑」，供筛选可见）。"""
    st = load_state()
    # CSV：tkid → 宿主行 / 行 → CNName
    hosp, sid_cn = {}, {}
    with io.open(CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            sid = r.get('ID', '')
            sid_cn[sid] = r.get('CNName', '')
            for t in (r.get('TK5编号') or '').split('|'):
                if t.strip().isdigit():
                    hosp.setdefault(t.strip(), sid)
    cards = {}
    log_rows = {}
    with io.open('build_log.csv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            log_rows[r.get('key', '')] = r
    for key, r in log_rows.items():
        ref = (r.get('ref') or '').split('/')[-1]
        m = re.match(r'^(\d+)_(.+?)_(朝右|朝正|朝左)\.png$', ref)
        if not m:
            continue                          # A 版 / 无底稿行 → 不入审批
        tid, refname = m.group(1), m.group(2)
        cn = r.get('cn') or refname
        cands = sorted(glob.glob('raw/%s_%s_[RA][0-9].png' % (key, cn)))
        cands += sorted(glob.glob('raw/*_%s_%s_[RA][0-9].png' % (key, cn)))   # 🔴 2026-08-30 新命名（tkid_前缀）双轨
        cands += [s for s in glob.glob('raw/%s_%s*.png' % (key, cn))
                  if '_R' not in s and '_A' not in s and '_M' not in s
                  and os.path.basename(s) != '%s_%s.png' % (key, cn)]
        if not cands:
            continue
        c = cards.get(tid)
        if c is None:
            # cn 取名链（2026-08-30 用户追问）：CSV 现行 CNName（跟改名实时同步）> 账本 cn > 底稿卡名
            scol = hosp.get(tid, '')
            cn = sid_cn.get(scol) or r.get('cn') or refname
            c = cards[tid] = {'tid': tid, 'cn': cn, 'refname': refname,
                              'sid': scol, 'stage': '', 'cands': [], 'ref': None}
        for x in cands:
            if x not in c['cands']:
                c['cands'].append(x)
        if '#' in key:
            c['stage'] = key.split('#', 1)[1]
        rl = (r.get('ref') or '').split('/')[-1]
        if rl and os.path.exists(os.path.join('refs_koei/_tk5', rl)):
            c['ref'] = os.path.join('refs_koei/_tk5', rl)
        elif c.get('ref') is None:
            # 🔴 2026-08-30：账本记录路径可能缺该朝向版本（根=朝正/identity=朝右 备案歧义）→ 按 tkid 兜底
            fs = [f for f in glob.glob(os.path.join('refs_koei/_tk5', '%s_*.png' % tid))
                  if not f.endswith('_朝左.png')]
            fs.sort(key=lambda f: (0 if f.endswith('_朝右.png') else 1))
            if fs:
                c['ref'] = fs[0]
    # 红标但暂无候选的卡（等待重跑）也建条目；无底稿/无宿主不建（不该审）
    for t, v in st.items():
        if t not in cards and 'redraw' in v and hosp.get(t):
            cards[t] = {'tid': t, 'cn': v.get('cn') or sid_cn.get(hosp[t], ''), 'sid': hosp[t],
                        'stage': '', 'cands': [], 'ref': None}
    out = list(cards.values())
    out.sort(key=lambda c: int(c['tid']))
    return out


def fit(path, w, h, mirror=False):
    im = Image.open(path).convert('RGB')
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    r = min(w / im.width, h / im.height)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)


class App:
    def __init__(self, root, items, state, start=0):
        self.root = root
        self.items = items
        self.state = state
        # 🔴 2026-08-30 用户裁定：筛选 = 工作视图快照（冻结）；处理完的卡留在快照里，上一卡/任何操作照常
        self.view_items = list(items)
        self.idx = max(0, min(start, len(self.view_items) - 1)) if self.view_items else 0
        self.cid = 0
        self.mirror = False
        self.view_mode = 0            # 0 全部 / 1 只看未审 / 2 只看待重生成
        self.ref_im = None
        self.thumbs = []
        root.title('选图决策器 v3（按卡审批） — 立绘')
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        ww, wh = min(W, sw - 40), min(H, sh - 60)
        root.geometry('%dx%d+%d+%d' % (ww, wh, max(0, (sw - ww) // 2),
                                       max(0, (sh - wh) // 2)))
        ch = min(CH, wh - 290)
        root.configure(bg='#16181d')
        self.top = tk.Label(root, text='', fg='#e8e5df', bg='#16181d',
                            font=('Segoe UI', 14, 'bold'))
        self.top.pack(pady=(8, 4))
        body = tk.Frame(root, bg='#16181d')
        body.pack(fill='both', expand=True)
        self.ref_cv = tk.Canvas(body, bg='#101216', width=KW__, height=ch,
                                highlightthickness=0)
        self.ref_cv.pack(side='left', padx=(12, 4), pady=6)
        self.cand_cv = tk.Canvas(body, bg='#101216', width=CW, height=ch,
                                 highlightthickness=0)
        self.cand_cv.pack(side='left', padx=4, pady=6)
        self.cand_cv.bind('<Button-1>', lambda e: self.select(self.cid))
        self.th_cv = tk.Canvas(root, bg='#101216', height=TH + 6, highlightthickness=0)
        self.th_cv.pack(fill='x', padx=12, pady=(2, 0))
        self.th_cv.bind('<Button-1>', self.thumb_click)
        btns = tk.Frame(root, bg='#16181d')
        btns.pack(pady=6)

        def B(txt, cmd, w=14):
            b = tk.Button(btns, text=txt, command=cmd, bg='#252a33', fg='#dfe4ea',
                          activebackground='#3a4150', relief='flat',
                          font=('Segoe UI', 11), padx=14, pady=8, width=w, cursor='hand2')
            b.pack(side='left', padx=5)
            return b
        self.ch = ch
        self.mirror_btn = B('镜像: 开', self.toggle_mirror)
        self.only_btn = B('筛选: 全部', self.toggle_view, w=14)
        B('⏭ 跳过&下一卡', self.skip_next, w=16)
        B('上一卡', self.prev)
        B('✓ 选定并下一卡', self.confirm, w=18)
        B('✗ 作废本卡', self.abandon, w=14)
        B('⚠标记重生成', self.toggle_redraw, w=14)
        B('重置本卡', self.reset)
        B('退出', self.save_exit)
        self.state_lb = tk.Label(root, text='', fg='#9aa3ad', bg='#16181d',
                                 font=('Consolas', 10))
        self.state_lb.pack(pady=(0, 6))
        root.bind_all('<Key>', self.key)
        self.refresh()

    # ---------- 数据 ----------
    def rec_of(self, it):
        return self.state.get(it['tid'], {})

    def rec_set(self, it, patch, drop_empty=None):
        r = self.state.setdefault(it['tid'], {'sid': it['sid'], 'cn': it['cn']})
        r.update(patch)
        if drop_empty:
            for k in drop_empty:
                if not r.get(k):
                    r.pop(k, None)
        save_state(self.state)

    def ok(self, it):
        """卡是否符合当前筛选（view_mode 1 未审 / 2 待重生成；0=全部）。"""
        if self.view_mode == 0:
            return True
        r = self.rec_of(it)
        done = bool(r.get('chosen'))
        red = 'redraw' in r
        if self.view_mode == 1:
            return not done and not r.get('dropped') and not red
        return red

    def cur(self):
        v = self.view_items
        return v[min(max(0, self.idx), len(v) - 1)] if v else None

    def restore_state(self):
        p = self.rec_of(self.cur())
        self.cid = 0
        self.mirror = bool(p.get('mirror'))
        if p.get('chosen'):
            for i, c in enumerate(self.cur()['cands']):
                if os.path.basename(c) == p['chosen']:
                    self.cid = i
                    break

    def _view_info(self):
        n = len(self.view_items)
        return (self.idx + 1, n)

    # ---------- 视图 ----------
    def refresh(self):
        it = self.cur()
        if it is None:
            self.top.config(text='（当前筛选无条目——点「筛选」切换或退出）')
            return
        r = self.rec_of(it)
        st = '✓ 已选定' if r.get('chosen') else ('✗ 已作废' if r.get('dropped') else
                                                ('⚠ 待重生成' if 'redraw' in r else '○ 未审'))
        note = r.get('redraw') or ''
        note_txt = ('  意见:%s' % note) if note else ''
        sname = it.get('sid') or ''
        extra = ('·%s' % it['stage']) if it.get('stage') else ''
        k, n = self._view_info()
        self.top.config(text='卡 %(tid)s%(stage)s ｜ %(cn)s ｜ %(host)s ｜ %(st)s%(note)s ｜ 第 %(i)d / %(n)d 张卡' % {
            'tid': it['tid'], 'stage': extra, 'cn': it['cn'], 'host': sname,
            'st': st, 'note': note_txt, 'i': k, 'n': n})
        self.ref_cv.delete('all')
        if it.get('ref'):
            im = fit(it['ref'], KW__ - 8, self.ch - 8)
            self.ref_im = ImageTk.PhotoImage(im)
            self.ref_cv.create_image(KW__ // 2, self.ch // 2, image=self.ref_im)
            self.ref_cv.create_text(8, 8, anchor='nw', text='底稿参考', fill='#8fd0a0',
                                    font=('Segoe UI', 9))
        else:
            self.ref_cv.create_text(KW__ // 2, self.ch // 2, text='无底稿显示（待重跑）',
                                    fill='#5a6270', justify='center')
        self.cid = self.cid % max(len(it['cands']), 1)
        path = it['cands'][self.cid] if it['cands'] else None
        if path:
            self.cand_im = ImageTk.PhotoImage(fit(path, CW - 8, self.ch - 8, self.mirror))
            self.cand_cv.delete('all')
            self.cand_cv.create_image(CW // 2, self.ch // 2, image=self.cand_im)
            self.cand_cv.create_text(12, 8, anchor='nw', text=os.path.basename(path),
                                     fill='#9fd8ff', font=('Consolas', 12))
            self.cand_cv.create_text(12, 30, anchor='nw',
                                     text='第 %d / %d 张备选%s' % (
                                         self.cid + 1, len(it['cands']),
                                         '  ← 镜像预览' if self.mirror else ''),
                                     fill='#ffd97f', font=('Segoe UI', 13, 'bold'))
        else:
            self.cand_cv.delete('all')
            self.cand_cv.create_text(CW // 2, self.ch // 2, text='暂无候选（重跑中/待重跑）',
                                     fill='#ffb84d', font=('Segoe UI', 16))
        PAGE = 7
        self.th_cv.delete('all')
        self.thumbs = []
        pg = self.cid // PAGE
        start = pg * PAGE
        x = 4
        for i, c in enumerate(it['cands']):
            if i < start or i >= start + PAGE:
                continue
            im = fit(c, TW - 6, TH - 6, False)
            photo = ImageTk.PhotoImage(im)
            if i == self.cid:
                self.th_cv.create_rectangle(x, 2, x + TW, TH + 4, outline='#7fd7ff', width=2)
            else:
                self.th_cv.create_rectangle(x, 2, x + TW, TH + 4, outline='#2c313a', width=1)
            if i == self.cid and self.mirror:
                photo = ImageTk.PhotoImage(fit(c, TW - 6, TH - 6, True))
            self.th_cv.create_image(x + 4, 4, anchor='nw', image=photo)
            self.th_cv.create_text(x + TW // 2, TH + 2 - 14, text='R%d' % (i + 1),
                                   fill='#c8d0da', font=('Consolas', 9))
            self.thumbs.append((x, photo))
            x += TW + 6
        self.mirror_btn.config(text='镜像: %s' % ('开' if self.mirror else '关'))
        done = sum(1 for i2 in self.items if self.rec_of(i2).get('chosen'))
        red_n = sum(1 for i2 in self.items if 'redraw' in self.rec_of(i2))
        self.state_lb.config(text='卡 %d | 已选定 %d | 未审 %d | 待重生成 %d | 键: 1/2/3选 T镜像 B作废 R标重生成 O筛选 S跳过 Enter选定下一卡 P上一卡 A/D换 Esc退出'
                             % (len(self.items), done, len(self.items) - done - red_n, red_n))

    def thumb_click(self, e):
        x = e.x
        for i, (tx, _) in enumerate(self.thumbs):
            if tx <= x <= tx + TW:
                self.cid = (self.cid // 7) * 7 + i
                self.refresh()
                return

    def page_prev(self):
        self.cid = max(0, (self.cid // 7 - 1) * 7)
        self.refresh()

    def page_next(self):
        self.cid = min(len(self.cur()['cands']) - 1, (self.cid // 7 + 1) * 7)
        self.refresh()

    def skip_next(self):
        """不选定、不改状态，直接看下一张卡（2026-08-30 用户反馈）。"""
        self.cid = 0
        if self.idx < len(self.view_items) - 1:
            self.idx += 1
            self.restore_state()
        self.refresh()

    # ---------- 动作 ----------
    def select(self, cid):
        self.cid = cid
        self.refresh()

    def toggle_mirror(self):
        self.mirror = not self.mirror
        self.refresh()

    def toggle_view(self):
        self.view_mode = (self.view_mode + 1) % 3
        names = {0: '全部', 1: '只看未审', 2: '只看待重生成'}
        self.only_btn.config(text='筛选: %s' % names[self.view_mode])
        # 🔴 用户裁定：筛选 = 冻结快照（处理完的卡留在视图内，操作全正常）；切换时重建
        if self.view_mode == 0:
            self.view_items = list(self.items)
        else:
            self.view_items = [it for it in self.items if self.ok(it)]
        self.idx = 0
        self.top.config(text='「%s」工作视图：%d 张卡（处理完的卡仍留在视图里）'
                             % (names[self.view_mode], len(self.view_items)))
        self.refresh()

    def toggle_redraw(self):
        it = self.cur()
        if not it:
            return
        r = self.rec_of(it)
        has = 'redraw' in r
        old = r.get('redraw', '')
        tip = '「卡%s」重生成注意点：\n（回车上滑；留空回车=%s）' % (
            it['tid'], ('清除标记' if has else '无意见'))
        try:
            note = simpledialog.askstring('待重生成', tip, parent=self.root,
                                          initialvalue=old)
        except Exception as e:
            self.top.config(text='弹窗失败: %s' % e)     # 🔴 2026-08-30：不再静默吞异常
            return
        if note is None:                                # Esc/取消
            return
        note = note.strip()
        r2 = self.rec_of(it)
        if note == '' and has:
            self.rec_set(it, {'redraw': ''}, drop_empty=['redraw'])   # 留空=清除标记
            msg = '已清除重生成标记: 卡%s' % it['tid']
        else:
            patch = {'redraw': note}
            if r2.get('chosen'):
                r2.pop('chosen', None)                  # 互斥：标红=撤销选定
                save_state(self.state)
            self.rec_set(it, patch)
            msg = '已标记重生成: 卡%s%s' % (it['tid'], '（意见已存）' if note else '')
            self.top.config(text=msg)
        self.refresh()

    def confirm(self):
        it = self.cur()
        if not it or not it['cands']:
            self.top.config(text='该卡暂无候选')
            return
        f = os.path.basename(it['cands'][self.cid])
        self.rec_set(it, {'chosen': f, 'mirror': int(bool(self.mirror))})
        # 🔴 2026-08-30：选定 = 认可此卡 → 无条件清除重生成意见/作废标记（互斥，含带意见的）
        r = self.rec_of(it)
        r.pop('redraw', None)
        r.pop('dropped', None)
        save_state(self.state)
        if self.idx < len(self.view_items) - 1:
            self.idx += 1
            self.restore_state()
        self.refresh()

    def abandon(self):
        it = self.cur()
        if not it:
            return
        r = self.rec_of(it)
        patch = {'dropped': not bool(r.get('dropped'))}
        if patch['dropped'] and r.get('chosen'):
            r.pop('chosen', None)
            r.pop('mirror', None)
        if not patch['dropped']:
            patch.pop('dropped')
            self.rec_set(it, {'dropped': ''}, drop_empty=['dropped'])
        else:
            self.rec_set(it, patch)
        self.top.config(text='已作废: 卡%s' % it['tid'] if patch.get('dropped') else '已撤销作废')
        self.refresh()

    def reset(self):
        it = self.cur()
        if it:
            self.state.pop(it['tid'], None)
            save_state(self.state)
            self.refresh()

    def prev(self):
        if self.idx > 0:
            self.idx -= 1
            self.restore_state()
            self.refresh()

    def save_exit(self):
        save_state(self.state)
        self.root.destroy()

    def key(self, e):
        k = e.keysym
        it = self.cur()
        if not it:
            return
        if k in '123456':
            cid = int(k) - 1
            if cid < len(it['cands']):
                self.cid = cid
                self.refresh()
        elif k.lower() == 't':
            self.toggle_mirror()
        elif k.lower() == 'a':
            self.cid -= 1
            self.refresh()
        elif k.lower() == 'd':
            self.cid += 1
            self.refresh()
        elif k == 'Return':
            self.confirm()
        elif k.lower() == 's':
            self.skip_next()
        elif k.lower() == 'p':
            self.prev()
        elif k.lower() == 'b':
            self.abandon()
        elif k.lower() == 'r':
            self.toggle_redraw()
        elif k.lower() == 'o':
            self.toggle_view()
        elif k == 'Escape':
            self.save_exit()


def main():
    os.chdir(os.getcwd())
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    items = load_cards()
    if not items:
        print('!! 未找到任何卡（build_log.csv / picktkid.json 缺失？）')
        return
    state = load_state()
    start = 0
    for i, it in enumerate(items):
        r = state.get(it['tid'], {})
        if not r.get('chosen') and not r.get('dropped') and 'redraw' not in r:
            start = i
            break
    else:
        start = len(items) - 1
    print('卡 %d | 已选定 %d | 待重生成 %d | 从第 %d 张卡开始' % (
        len(items),
        sum(1 for i2 in items if state.get(i2['tid'], {}).get('chosen')),
        sum(1 for i2 in items if 'redraw' in state.get(i2['tid'], {})), start + 1))
    root = tk.Tk()
    App(root, items, state, start)
    if os.environ.get('PICK_GUI_AUTOCLOSE'):
        root.after(int(os.environ['PICK_GUI_AUTOCLOSE']) * 1000, root.destroy)
    root.mainloop()


if __name__ == '__main__':
    main()
