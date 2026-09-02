# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""plan 7.1：全量 BUSTUP → refs_koei/_tk5 转置补全（2026-08-29）。

diff = BUSTUP 全 tkid − refs 已转 tkid → 逐个 ensure_ref（dds→判向→朝右化，近正/漏检落朝正）。
幂等：已有 _朝右/_朝正 跳过；缺 000.dds 跳过并报告。零 API 成本。
用法：python ensure_ref_all.py [--limit N]   # 缺哪些 id 单独提示输到 _missing_refs.txt
"""
import glob, os, re, sys
sys.path.insert(0, os.getcwd())
import stage_pipeline as SP

SRC, OUT = SP.SRC, SP.OUT


def main():
    limit = 0
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    src_ids = set()
    for d in os.listdir(SRC):
        p = d.split('_', 1)[0]
        if p.isdigit():
            src_ids.add(int(p))
    out_ids = set()
    for f in os.listdir(OUT):
        m = re.match(r'^(\d+)_', f)
        if m:
            out_ids.add(int(m.group(1)))
    miss = sorted(src_ids - out_ids)
    if limit:
        miss = miss[:limit]
    print('缺口 tkid: %d 个' % len(miss))
    ok, fail = 0, []
    for tkid in miss:
        r = SP.ensure_ref(tkid, 'gap-%d' % tkid)
        if r:
            ok += 1
        else:
            fail.append(tkid)
    with open('_missing_refs.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(str(t) for t in fail))
    print('转置完成: %d 成功 / %d 失败（缺 000.dds，清单 _missing_refs.txt）' % (ok, len(fail)))


if __name__ == '__main__':
    main()
