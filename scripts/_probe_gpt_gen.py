# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""探测：gpt-image-2 走 /images/generations（无 reference）是否可用。1 张，最低费用。"""
import json, time, urllib.request
import gen_portrait as G

print('billing before:', G.billing())
t0 = time.time()
body = {'model': 'gpt-image-2', 'prompt': '测试：穿暗蓝色素袍的日本武将半身立绘，写实厚涂，侧脸朝右。',
        'size': '1024x1536', 'output_format': 'png', 'quality': 'medium', 'seed': 1001}
req = urllib.request.Request(G.BASE.rstrip('/') + '/images/generations',
                             data=json.dumps(body).encode('utf-8'),
                             headers={'Content-Type': 'application/json',
                                      'Authorization': 'Bearer ' + G.KEY})
try:
    r = json.load(urllib.request.urlopen(req, timeout=300))
    d = r['data'][0]
    if 'b64_json' in d:
        import base64
        open('_probe_gpt_gen.png', 'wb').write(base64.b64decode(d['b64_json']))
        print('OK b64, %.1fs' % (time.time() - t0))
        print('billing after:', G.billing())
    else:
        print('URL 输出:', d['url'])
except urllib.error.HTTPError as e:
    print('HTTP %s: %s' % (e.code, e.read().decode()[:400]))
except Exception as e:
    print('ERR:', str(e)[:300])
