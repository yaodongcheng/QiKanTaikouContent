# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""阶段读图板：35 人多阶段人物 → 每人数张原图拼板（供 Claude 读图 + 用户终审）。
产出：preview/stage_boards/b{:02d}.jpg（每板 8 人，每格 = 一人全部阶段图并排）。
用法：python make_stage_boards.py [--from N]    # 从第 N 板开始
"""
import os, sys, json, re
from PIL import Image

SRC = r'E:\taikou5\TaikouImage\BUSTUP'
TSV = '_stage_candidates.tsv'
OUT = 'preview/stage_boards'
CELL_W, CELL_H = 300, 360   # 每阶段图格
PER_ROW = 4                 # 每行 4 人


def load_cands():
    rows = [r for r in open(TSV, encoding='utf-8').read().splitlines() if r.strip()]
    out = []
    for r in rows[1:]:
        sid, cn, rest = r.split('\t', 2)
        hits = re.findall(r'([^;]+)->\[([\d, ]+)\]', rest)
        ids = []
        for name, vals in hits:
            for v in vals.replace(' ', '').split(','):
                if v and int(v) not in ids:
                    ids.append(int(v))
        out.append((sid, cn, ids))
    return out


def img_for(pid):
    for d in os.listdir(SRC):
        if d.startswith('%s_' % pid) and os.path.exists(os.path.join(SRC, d, '000.dds')):
            im = Image.open(os.path.join(SRC, d, '000.dds')).convert('RGBA')
            bg = Image.new('RGB', im.size, (40, 40, 46))
            bg.paste(im, (0, 0), im)
            # 等比裁成纵格
            w, h = bg.size
            scale = max(CELL_W / w, CELL_H / h)
            bg = bg.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            x = (bg.width - CELL_W) // 2
            y = (bg.height - CELL_H) // 2
            return bg.crop((x, y, x + CELL_W, y + CELL_H))
    return Image.new('RGB', (CELL_W, CELL_H), (60, 20, 20))


def main():
    from_ = 0
    if '--from' in sys.argv:
        from_ = int(sys.argv[sys.argv.index('--from') + 1])
    os.makedirs(OUT, exist_ok=True)
    cands = [c for c in load_cands() if c[2] and len(c[2]) > 1]
    cands = [c for c in cands if c[0] not in (
        'lord_1_oda', 'lord_1_kinoshita')]  # 已核的主角跳过
    boards = (len(cands) + 7) // 8
    print('待核 %d 人 → %d 板' % (len(cands), boards))
    for bi in range(from_, boards):
        grp = cands[bi * 8:(bi + 1) * 8]
        if not grp:
            break
        sheet = Image.new('RGB', (CELL_W * PER_ROW, CELL_H * 2), (22, 22, 28))
        for i, (sid, cn, ids) in enumerate(grp):
            row, colx = i // PER_ROW, i % PER_ROW
            x0 = colx * CELL_W
            cw = CELL_W // max(1, len(ids))  # 多图等分一人宽
            for j, pid in enumerate(ids):
                sheet.paste(img_for(pid).resize((cw, int(CELL_H * cw / CELL_W)), Image.LANCZOS),
                            (x0 + j * cw, row * CELL_H))
        sheet.save(os.path.join(OUT, 'b%02d.jpg' % (bi + 1)), quality=88)
        print('b%02d.jpg: %s' % (bi + 1, ' ; '.join('%s#%s' % (c[1], ','.join(map(str, c[2]))) for c in grp)))

if __name__ == '__main__':
    main()
