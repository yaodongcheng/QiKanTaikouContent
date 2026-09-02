# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""信长脸素材池参考图：正脸大特写（换脸管线用；与 quick_one.py 半身立绘互为双胞胎）。
用法：
  python quick_bigface.py                      # 默认 3 张（seed 2002/2003/2004）
  python quick_bigface.py 2002 2006            # 指定 seed
参考图 = MINIFACE/195_织田信长/000.dds 解出的正脸头像（refs_koei/_tk5_face/）。
"""
import base64, os, sys, time, urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import gen_portrait as G

REF = 'refs_koei/_tk5_face/195_织田信长_face.png' if os.environ.get('QUICK_FEMALE') != '1' else 'refs_koei/_tk5/1049_阿市_朝右.png'

# 英雄字段（build_prompt 仅用这几个；不依赖 run_trial CSV 路径）
# 默认 = 信长（男）；QUICK_FEMALE=1 时用阿市（女）——女包验证管线用
import os
H = {'id': 'lord_1_oda', 'name': '织田信长', 'age': 40, 'gender': '男',
     'identity': '大名', 'temper': '冷静', 'spirit': '普通', 'force': '60'}
if os.environ.get('QUICK_FEMALE') == '1':
    H = {'id': 'lord_1_azai_1', 'name': '阿市', 'age': 24, 'gender': '女',
         'identity': '公主', 'temper': '温和', 'spirit': '勇敢', 'force': '40'}

# 换脸管线专用：与立绘构图相反的构图段（正脸直视镜头大特写）——见 gen_portrait.composition_face
def bigface_prompt(h):
    character = G.character_layer(dict(h), include_appearance=False, include_dress=False)
    return '，'.join([G.STYLE, character, G.composition_face(), G.REF_HINT, G.NEG_FACE])


def main():
    os.makedirs('raw', exist_ok=True)
    h = dict(H)
    prompt = bigface_prompt(h)
    seeds = sys.argv[1:] or ['2002', '2003', '2004']
    print('人物=%s 参考=%s' % (h.get('name'), REF))
    for seed in seeds:
        t0 = time.time()
        try:
            res = G.generate(prompt, ref=[G.data_uri(REF)], seed=int(seed))
            data = base64.b64decode(res['val']) if res['type'] == 'b64' \
                else urllib.request.urlopen(res['val'], timeout=180).read()
            out = 'raw/oda_bigface_s%s.jpg' % seed
            with open(out, 'wb') as f:
                f.write(data)
            print('OK %s %.0fKB %.1fs' % (out, len(data) / 1024, time.time() - t0))
        except Exception as e:
            print('ERR seed %s: %s' % (seed, str(e)[:200]))


if __name__ == '__main__':
    main()
