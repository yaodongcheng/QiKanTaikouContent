# -*- coding: utf-8 -*-
# 🔴 2026-08-30 归位 ArtSource/scripts/ 后运行契约：chdir 回 ArtSource（cwd 契约）+ scripts 目录入 sys.path（互 import）
import os as _os, sys as _sys
_os.chdir(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'ArtSource'))
if _os.path.dirname(_os.path.abspath(__file__)) not in _sys.path:
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

"""主路抠图：rembg u2net → 512x768 透明 PNG。

P5 已落地（2026-08-28）：不再做中轴平移，紧贴人物裁切、水平居中、贴底对齐，
512 宽全部给人物。「脸偏右」由画面内朝向实现，不由画布内平移实现。
🔴 2026-08-30 模型选型：isnet-general-use（丢部件：深色甲×深背景误删手臂/袖子；
  实测 987/16 两案缺臂）→ 对比实验中 u2net 肢体完整率最高、边缘干净、0.2-0.9s/张
  （birefnet-general 完整但 halo 雾边 + 24s/张）→ 主路模型定为 u2net。
"""
import os, json
import numpy as np
from PIL import Image
from rembg import remove, new_session

OUT_W, OUT_H = 512, 768
SESSION = new_session('u2net')


_FACE_MESH = None
_FACE_DET = None


def _face_mesh():
    global _FACE_MESH
    if _FACE_MESH is None:
        import mediapipe as mp
        _FACE_MESH = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1,
                                                     refine_landmarks=True)
    return _FACE_MESH


def _face_detector():
    global _FACE_DET
    if _FACE_DET is None:
        import mediapipe as mp
        _FACE_DET = mp.solutions.face_detection.FaceDetection(model_selection=1,
                                                              min_detection_confidence=0.5)
    return _FACE_DET


def _eye_anchor(rgb):
    """mediapipe FaceMesh：水平锚 = 头纵中线（额头顶点 10 号 + 下巴顶点 152 号中点——侧脸透视下
    眼里点在头的外侧，用眼中点当水平锚会整体偏移（2026-08-30 350 案例修正））；
    垂直锚 = 双眼中点 y（眼基线稳定，面部一致性关键）；返回 (head_cx, eyes_cy, eye_dist)。失败 None。"""
    try:
        r = _face_mesh().process(rgb)
        if not r.multi_face_landmarks:
            return None
        l = r.multi_face_landmarks[0].landmark
        h, w = rgb.shape[:2]

        def p(i):
            return (l[i].x * w, l[i].y * h)
        le = ((p(33)[0] + p(133)[0]) / 2, (p(33)[1] + p(133)[1]) / 2)   # 左眼外角33+内角133 中点
        re = ((p(362)[0] + p(263)[0]) / 2, (p(362)[1] + p(263)[1]) / 2)  # 右眼内角362+外角263 中点
        d = ((re[0] - le[0]) ** 2 + (re[1] - le[1]) ** 2) ** 0.5
        if d < 8:
            return None
        # 水平锚 = 头纵中线 + 朝向补偿（侧脸透视下额头-下巴轴线偏脑后；头巾/发髻体积多在脑后，
        # 视觉均衡 = 中线向脸侧补 0.25 眼距——鼻尖相对中线判定脸朝向，镜像对称；2026-08-30 350 案例）
        nose_x = p(1)[0]
        sgn = 1.0 if nose_x >= (p(10)[0] + p(152)[0]) / 2 else -1.0
        head_cx = (p(10)[0] + p(152)[0]) / 2 + 0.25 * d * sgn
        eyes_cy = (le[1] + re[1]) / 2
        # v17（2026-08-30，1154 surprised 实证）：尺度基准 = 头长（10→152 距离）——表情（瞪眼/垂眼）
        # 只动眼眉嘴，头几何不变；眼距会被表情撑大（同卡漂移 25-50%）→ 脸占比漂；头长波动 3.8-15%。
        h10 = np.array([p(10)[0], p(10)[1]])
        h152 = np.array([p(152)[0], p(152)[1]])
        head_len = float(np.linalg.norm(h10 - h152))
        eye_mid_x = (le[0] + re[0]) / 2
        return head_cx, eyes_cy, head_len, eye_mid_x
    except Exception:
        return None


def _skin_face_center(img, cx, cy, side):
    """后验平衡（v15.1，2026-08-30）：候选窗收窄到锚邻域（±0.5side 水平 × ±0.4side 垂直，
    v15 全域 ±0.9side 会把肩/颈/手框进来 → 最大连通域抓成肩甲块 → 窗口拖飞（14 全卡翻车）），
    YCrCb×HSV 三闸皮肤 + 最大连通域 = 脸部皮肤块；返回其质心；无块返回 None。"""
    import cv2
    w, h = img.size
    x0 = max(0, int(cx - side * 0.5)); x1 = min(w, int(cx + side * 0.5))
    y0 = max(0, int(cy - side * 0.4)); y1 = min(h, int(cy + side * 0.4))
    reg = np.asarray(img)[y0:y1, x0:x1]
    hsv = cv2.cvtColor(reg, cv2.COLOR_RGB2HSV)
    ycc = cv2.cvtColor(reg, cv2.COLOR_RGB2YCrCb)
    skin = ((hsv[..., 1] >= 40) & (hsv[..., 2] >= 50)
            & (ycc[..., 0] >= 77) & (ycc[..., 0] <= 127)
            & (ycc[..., 1] >= 133) & (ycc[..., 1] <= 180)).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(skin, 8)
    if n <= 1:
        return None
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    if stats[big, cv2.CC_STAT_AREA] < 500:
        return None
    ys, xs = np.where(lab == big)
    return x0 + xs.mean(), y0 + ys.mean()


def _face_ratio(img):
    """脸占比（皮肤块面积/画面）：YCrCb×HSV 三闸最大连通域。用于 v16 占比闸。"""
    import cv2
    hsv = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2HSV)
    ycc = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2YCrCb)
    skin = ((hsv[..., 1] >= 40) & (hsv[..., 2] >= 50)
            & (ycc[..., 0] >= 77) & (ycc[..., 0] <= 127)
            & (ycc[..., 1] >= 133) & (ycc[..., 1] <= 180)).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(skin, 8)
    if n <= 1:
        return None
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return float(stats[big, cv2.CC_STAT_AREA]) / float(skin.shape[0] * skin.shape[1])


def _save_square(img, cx, cy, side, size, out_path):
    """正方形裁剪（v16 face% 闸已删——face_ratio 域对惊讶脸不可靠（实测 12%/2% 误报）；尺度
    统一改由锚基准保证：level0=头长×2.2（v17，表情无关），level1=脸框×2.1，level2=皮肤带×2.4）。"""
    w, h = img.size
    x0 = min(max(int(cx - side / 2), 0), int(w - side))
    y0 = min(max(int(cy - side * 0.45), 0), int(h - side))
    crop = img.crop((x0, y0, x0 + side, y0 + side))
    crop.resize((size, size), Image.LANCZOS).save(out_path)


def build_minihead(orig_path, out_path, size=256, alpha_path=None):
    """方形小头像 v4（2026-08-30 用户裁定）：双眼锚定，三级锚。
    0=mediapipe 眼锚（眼距×5.0 为边长；同人不同表情/卡 → 眼距稳定 → 面部位/大小一致）；
    1=cv2 脸框（mediapipe 失败时）；2=抠图 alpha 人物顶区引导（双失败——如深侧脸低头闭眼，
    mediapipe+cv2 都失效；head 位 = alpha 顶带重心，直接从 alpha 图裁，边长=bbox 高×0.5）。
    返回 (level, eye_dist, cx, cy, side)：level 入库为必审依据（>=1 视为降级锚）。
    v1（从抠图立绘上部 512 裁）已废。"""
    import cv2
    img = Image.open(orig_path).convert('RGB')
    w, h = img.size
    rgb = np.asarray(img)
    anchor = _eye_anchor(rgb)
    level = 0
    if anchor:
        side = anchor[2] * 2.2                     # v17：尺度 = 头长×2.2（头部尺寸，表情无关）
        cy = anchor[1]                             # 垂直 = 眼基线（不变）
        # v18（2026-08-30 用户裁定）：左右平移窗口，使双眼中心 = 画面 52%（保持头部尺寸不动）。
        # 此前头中线+补偿/皮肤平衡全弃用（皮肤平衡在露肤大图拖飞；纯净几何眼点才是可核指标）。
        side = max(side, int(w * 0.24))
        tx = anchor[3] - 0.52 * side               # 窗口左缘 = 眼心 - 52%×side
        tx = min(max(tx, 0), int(w - side))
        cx = tx + side / 2
        _save_square(img, cx, cy, side, size, out_path)
        return level, side / 2.2, cx, cy, side
    # level 1：blaze FaceDetection（mesh 失败时的高阶脸框锚；与眼锚同基准：side = 脸框高×2.1 → 脸占 ~48%。
    # 2026-08-30：取代 cv2 级联+皮肤闸（14 sad 实证 mesh/lagacy 均失败但 blaze 命中 0.72；同卡基准统一）
    fd = _face_detector().process(rgb)
    if fd.detections:
        b = fd.detections[0].location_data.relative_bounding_box
        bw_, bh_ = b.width * w, b.height * h
        cx = (b.xmin + b.width / 2) * w
        cy = (b.ymin + b.height / 2) * h
        side = max(max(bh_, bw_) * 2.1, h * 0.22)
        _save_square(img, cx, cy, side, size, out_path)   # v17：FaceDetection 锚纯几何（同去 fc 平衡）
        return 1, 0, cx, cy, side
    if alpha_path and os.path.exists(alpha_path):        # 独立 if（非 elif）：cv2 皮肤闸判假脸后必须能落到这里
        al = np.array(Image.open(alpha_path).convert('RGBA'))[..., 3]
        ys, xs = np.where(al > 25)
        if len(xs):
            level = 2
            bh = int(ys.max() - ys.min() + 1)
            # 2026-08-30 修正（14 sad 案例）：alpha 顶带重心把"盔顶"当头位 → 裁到盔上。
            # 脸部 = 皮肤色块；限定 bbox 顶 60% 带内的肤色质心 = 脸位（蒙面/无肤色时退回顶带重心）。
            img_alpha = Image.open(alpha_path).convert('RGB')
            rgb_a = np.asarray(img_alpha)
            hsv = cv2.cvtColor(rgb_a, cv2.COLOR_RGB2HSV)
            ycc = cv2.cvtColor(rgb_a, cv2.COLOR_RGB2YCrCb)
            band0, band1 = ys.min(), ys.min() + int(bh * 0.60)
            # v13（2026-08-30）：金橙盔甲/护甲亮片会混入 HSV 皮肤域（14 sad 实证：域过宽 → side 拉爆）
            # 三重闸：HSV(S40/V50) × YCrCb(Cr 133-180, Cb 77-127) × 最大连通块（脸，剩面具/肤块）
            skin = ((hsv[band0:band1, ..., 1] >= 40) & (hsv[band0:band1, ..., 2] >= 50)
                    & (ycc[band0:band1, ..., 0] >= 77) & (ycc[band0:band1, ..., 0] <= 127)
                    & (ycc[band0:band1, ..., 1] >= 133) & (ycc[band0:band1, ..., 1] <= 180)
                    & (al[band0:band1] > 25))
            skin = skin.astype(np.uint8)
            n, lab, stats, _ = cv2.connectedComponentsWithStats(skin, connectivity=8)
            if n > 1:
                big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
                skin = ((lab == big) & (skin > 0)).astype(np.uint8)
            sy, sx = np.where(skin)
            if len(sx) > 200:                       # 有肤色块 → 脸位 = 肤色带中心，脸高 = 带高
                # v12（2026-08-30）：14 sad 案例——人物高×0.52 偏大（脸被拉小）、质心 1.12 下压过火（脸偏下）
                # 改为：side = 肤色带高×2.4（脸占画面 ≈42% 稳定），心 = 带中（sy.min+max)/2
                sh = float(sy.max() - sy.min() + 1)
                cx = float(sx.mean())
                cy = band0 + (float(sy.min()) + float(sy.max())) / 2
                side = max(sh * 2.4, bh * 0.30)
            else:                                    # 无肤色（蒙面/全甲）→ alpha 顶带重心
                wsum = al[band0:band1].sum(axis=0).astype(float)
                cx = float(np.dot(np.arange(al.shape[1]), wsum) / wsum.sum()) if wsum.sum() > 0 else \
                    float((xs.min() + xs.max()) / 2)
                cy = band0 + bh * 0.10
                side = bh * 0.52
            im_a = Image.open(alpha_path).convert('RGB')
            ah, aw = im_a.size
            x0 = min(max(int(cx - side / 2), 0), int(aw - side))
            y0 = min(max(int(cy - side * 0.45), 0), int(ah - side))
            _save_square(im_a, cx, cy, side, size, out_path)
            return level, 0, float(cx), cy, side
    cx, cy, side = w / 2, h * 0.22, h * 0.22     # 无脸启发：上中区（level = 3，最底线，必审）
    x0 = min(max(int(cx - side / 2), 0), int(w - side))
    y0 = min(max(int(cy - side * 0.45), 0), int(h - side))
    _save_square(img, cx, cy, side, size, out_path)
    return 3, 0, cx, cy, side


def matte(src, alpha_matting=True):
    img = Image.open(src).convert('RGB')
    cut = remove(img, session=SESSION, alpha_matting=alpha_matting,
                 alpha_matting_foreground_threshold=250,
                 alpha_matting_background_threshold=20,
                 alpha_matting_erode_size=6)
    return cut.convert('RGBA')


def place(rgba, out_path):
    """紧贴人物包围盒裁切 → 等比放到 512x768 内最大 → 水平居中 + 贴底。
    2026-08-28 追加头占比质检（用户裁定：头占比须统一）——用 OpenCV 人脸框高 ÷ 人物包围盒高。"""
    a = np.asarray(rgba)[..., 3]
    ys, xs = np.where(a > 25)
    if not len(xs):
        return None
    cut = rgba.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    cw, ch = cut.size
    # 等比缩放，短边顶格：优先撑满高度，撑不下（人物太宽）就改撑满宽度
    scale = min(OUT_W / cw, OUT_H / ch)
    tw, th = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    cut = cut.resize((tw, th), Image.LANCZOS)
    canvas = Image.new('RGBA', (OUT_W, OUT_H), (0, 0, 0, 0))
    canvas.alpha_composite(cut, ((OUT_W - tw) // 2, OUT_H - th))
    canvas.save(out_path)
    al = np.asarray(canvas)[..., 3]
    # 质检：不透明占比 / 是否有半透明破洞（人物内部 alpha 中间值过多 = 抠穿了）
    inner = al[al > 0]
    holes = float(((inner > 25) & (inner < 230)).mean()) if inner.size else 0.0
    # 头占比：人脸框高 / 人物包围盒高，约 0.18~0.30（半身立绘统一取景约定）
    head_ratio = None
    try:
        import cv2
        rgb = np.asarray(canvas.convert('RGB'))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) > 0:
            fh = max(f[3] for f in faces)
            head_ratio = round(fh / th, 3)   # 人脸高 ÷ 缩放后人物全高（th = 人物在 512x768 内的高）
    except Exception:
        pass
    return {'opaque': round(float((al > 25).mean()), 3),
            'holes': round(holes, 3),
            'fill_w': round(float(tw) / OUT_W, 3),
            'head_ratio': head_ratio,
            'head_ok': None if head_ratio is None else (0.14 <= head_ratio <= 0.34)}


def shoulder_ratio(rgba):
    """肩带比（剪影法，2026-08-28 用户标定 → T1a 正式落位）：
    上半身（人物包围盒顶 40% 高度带）内，画布中轴左半/右半的 alpha>25 像素比。
    通过区间 ∈ [1.05, 1.65] = 自然侧身（两面出界=拧巴，换 seed 重跑）。
    标定样本：阿市 1.10✅ 幸村 1.49✅ 信长 0.73❌ 訚千代 0.95❌ 秀吉 1.93❌。"""
    a = np.asarray(rgba)[..., 3]
    ys, xs = np.where(a > 25)
    if not len(xs):
        return None
    top = ys.min()
    H = int(ys.max() - top + 1)
    band = a[top: top + int(0.40 * H)]              # 上半身带：包围盒顶 40% 高
    h, w = band.shape
    left = int((band[:, :w // 2] > 25).sum())
    right = int((band[:, w // 2:] > 25).sum())
    if right == 0:
        return None
    return round(left / right, 3)


def qc_sheet(pngs, out_path, bg):
    """把成品贴到指定底色上拼成质检长图。"""
    cols = len(pngs)
    sheet = Image.new('RGB', (OUT_W * cols, OUT_H), bg)
    for i, p in enumerate(pngs):
        im = Image.open(p).convert('RGBA')
        tile = Image.new('RGB', (OUT_W, OUT_H), bg)
        tile.paste(im, (0, 0), im)
        sheet.paste(tile, (OUT_W * i, 0))
    sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS).save(out_path, quality=88)


if __name__ == '__main__':
    os.makedirs('matte_rembg', exist_ok=True)
    os.makedirs('preview', exist_ok=True)
    rows = []
    print('%-40s %-10s %-10s %-8s' % ('file', '不透明占比', '半透明破洞', '横向占比'))
    for f in sorted(os.listdir('raw')):
        if not f.endswith('.jpg'):
            continue
        out = os.path.join('matte_rembg', f[:-4] + '.png')
        r = place(matte(os.path.join('raw', f)), out)
        rows.append({'file': f, 'png': out, 'qc': r})
        print('%-28s %-10s %-10s %-8s' % (f, r and r['opaque'], r and r['holes'], r and r['fill_w']))
    json.dump(rows, open('matte_rembg_log.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    # 每人一张质检图：深底 + 浅底（组键 = 去掉末尾 _X.jpg 的版本后缀，版本约定为单字母）
    for sid in sorted({f[:-6] for f in (r['file'] for r in rows)}):
        ps = [r['png'] for r in rows if r['file'].startswith(sid + '_')]
        qc_sheet(ps, os.path.join('preview', sid + '_rembg_dark.jpg'), (28, 28, 34))
        qc_sheet(ps, os.path.join('preview', sid + '_rembg_light.jpg'), (232, 230, 224))
    print('done')
