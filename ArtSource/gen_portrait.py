# -*- coding: utf-8 -*-
"""立绘生成器（试跑版）。提示词模板是唯一事实源（铁律 22）——改画风改这里，不许手 P 图。"""
import base64, io, json, mimetypes, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

# 取配置：环境变量优先，ArtSource/api_config.json 兜底（已 gitignore）。
# 全程只读取、永不打印，避免 key 溅进日志/会话（2026-08-28 用户约定）。
def _load_config():
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_config.json')
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

_CFG = _load_config()
BASE = os.environ.get('LEIHUO_BASE') or (_CFG.get('base_url') or 'https://ai.leihuo.netease.com/v1')
KEY = os.environ.get('LEIHUO_KEY') or (_CFG.get('api_key') or '')
MODEL = os.environ.get('LEIHUO_MODEL') or (_CFG.get('model') or 'doubao-seedream-5-0-260128')

def _require_key():
    if not KEY:
        raise SystemExit('未找到雷火网关 API Key：请设环境变量 LEIHUO_KEY，'
                         '或把 key 填入 ArtSource/api_config.json（已 gitignore，不进库）')

_require_key()
GEN_SIZE = '1568x2352'          # 服务最小 3,686,400 像素门槛下最省的 2:3 档

# ---------- 风格层（全人固定，逐字不变，保证 1000 张画风一致） ----------
# 2026-08-28 用户裁定：目标 = 现代光荣 CG 立绘（信长之野望/三国志14 主立绘那样的
# 写实厚涂数字绘画），明确不是浮世绘/水墨/工笔。禁用低饱和与"笔触克制"措辞。
# ---------- 风格层（纯画风，全人固定；身份/装束/色彩归人物层——2026-08-28 用户裁定：
#   金属/鎏金/华丽配色/英雄气质都是"武将专属"，忍者/商人/海盗/百姓不该被套用） ----------
STYLE = (
    '日本光荣公司战国人物立绘CG画风：写实厚涂数字绘画，笔触细腻专业；'
    '人物面部写实，五官立体分明、肌肤质感自然；严禁偶像化嫩脸与美颜磨皮感。'
    '戏剧性光影：强烈侧顶光与轮廓光，明暗层次分明。'
    '统一现代 CG 电影级的专业调色与质感。'
)
NEG = (
    '禁止：浮世绘、版画、水墨画、工笔淡彩、扁平插画、平涂上色、'
    '动漫萌化脸、大眼睛、偶像俊美脸、嫩肤美颜磨皮、Q版、正面直视镜头、'
    '扭脖式转头、人物贴画面右缘、'
    '3D渲染、真人照片、赛博朋克、奇幻魔法元素、现代服饰、呆板站姿、'
    '任何文字、边框、签名、印章、水印、装饰花纹、多个人物。'
)
# 参考图约束：必须随参考图一起进 prompt，否则裸传 base64 = 模型随意把整张古画当模板
# （P2 根因：真田 C/D 被江户古画带跑了姿态和画风）
# 2026-08-28 用户裁定：img2img 正式启用（TK5 原图当底稿），但「加工重绘」必须显式写死——
# 底稿只借长相/造型，姿势构图画风光影一律重绘，禁止照抄。
REF_HINT = (
    '以上参考图仅提供该人物的面部骨相、发型须发与标志性服饰（形制与配色）的底稿；'
    '姿势、构图、画风、光影、背景一律重绘，严格遵循本提示词；'
    '禁止沿用参考图的姿态、构图与绘画风格，禁止画面复制或临摹感；'
    '成品必须是现代 CG 写实厚涂成色。'
)

# ---------- 构图层（全人固定；立绘贴屏幕左下角，脸朝右；背景改风暴天空，抠图交给 rembg） ----------
# 2026-08-28 构图判据定稿（用户标定样本 = 阿市/訚千代）：
#   脸清晰朝画面右（鼻偏 ≥0.030）且画面右肩近镜（解剖左肩 x − 右肩 x ≤ −0.15）。
#   v4 写法：把"转身"改成画面语言（鼻梁剪影/半边脸/一肩大一肩小），删掉角度词。
def composition():
    return (
        '竖幅单人半身战国人物立绘，下沿切在胸腰之间，不画腿脚。'
        '人物身体与头部作为一个整体倾向画面右侧：'
        '鼻梁与下颌剪影朝向画面右方；'
        '画面左侧的肩膀位于近景，体积大而完整；'
        '画面右侧的肩膀缩向远处、只露出小半——两肩一前一后呈明显对角透视；'
        '不得双肩平齐，不得正面平视镜头，不得单独扭动头部。'
        '面部位于画面中上部，人物整体大致居中（中轴不超过画面横向 55%），'
        '左侧留少量氛围余白，不得贴画面右缘。'
        '头部连同盔帽的高度约占画面总高四分之一（24~28 百分比），'
        '人物整体高度约占画面九成，半身取景统一，不要特写、不要全身。'
        '头顶留白约占画面高度 8 百分比，头部完整不得被裁切。'
        '背景为暗色风暴战场天空：浓云翻滚，四周边缘渐暗，光线压向人物一侧；'
        '背景干净，无杂物，无文字，无图案，无装饰纹样。'
    )


# ---------- 构图铁律（composition_boost 用，2026-08-28 用户裁定） ----------
# 只重复核心失败句（脸朝右/左近右远/禁平视），开头+结尾双出现 = 开头与结尾注意力最高区；
# 不整段重复三次 = 费 token 且读感差。A/B 基线 = seed 2002 FAIL(0.003/0.302)。
COMP_RULE = ('构图铁律：人物身体与头部整体倾向画面右侧，鼻梁与下颌剪影朝向画面右方；'
             '画面左侧肩位于近景、体积大而完整，画面右侧肩缩向远处仅露小半，'
             '两肩一前一后呈明显对角透视；禁止正面平视镜头，禁止双肩平齐，禁止单独扭动头部。')
# 对抗句：跟 REF_HINT 一起用，正面推+负面挡，防止构图继续被底稿姿势带跑
REF_ANTI_POSE = '构图姿势一律以本提示词铁律为准：禁止跟随参考图的姿态与构图。'


# ---------- 人物层（每人不同，全部从 TaikouHero 表字段推出） ----------
# 29 类身份装束全量（2026-08-28 枚举主源 CSV Identity_* 列补齐）；
# 「无效」= 无身份平民→朴素素衣兜底（不再错套足轻组头）。
IDENTITY_DRESS = {
    '大名':   '战国大名，头戴乌帽子，身着上等黑地金纹阵羽织，内衬小袖与肩衣，气度威严',
    '国主':   '一国之主大名，阵羽织配具足，庄重堂皇',
    '城主':   '城主，具足肩甲配阵羽织，武将气派',
    '当家':   '家当主，素纹小袖配肩衣，持重干练',
    '家老':   '家老重臣，深色羽织加肩衣，腰佩打刀，沉稳老练',
    '部将':   '部将，轻铠与阵羽织配色协调，军中稳健',
    '侍大将': '侍大将，具足胴丸配阵羽织，武人身板',
    '足轻大将': '足轻大将，简素具足，腰佩太刀',
    '足轻组头': '足轻组头，粗布小袖配简朴胴丸，无华饰，出身寒微而眼神机敏',
    '浪人':   '浪人，洗旧的小袖，蓬乱月代，腰间一口打刀',
    '上忍':   '上忍，深黑夜行装束，束袖束腰，潜伏干练',
    '中忍':   '忍者，深靛夜行小袖，机动隐匿',
    '下忍':   '忍者，布帛夜行装，轻快勤勉',
    '师范':   '剑豪师范，素色小袖短袴，气定神闲',
    '师范代': '师范代，素小袖短袴，英气干练',
    '见习':   '习武少年，粗布小袖，稚气微露',
    '头领':   '海贼头领，深色半缠，佩刀豪放',
    '头目':   '山贼头目，敝袍束腰，粗犷凶狠',
    '船大将': '船大将，半缠海装，佩刀，海上豪勇',
    '船头':   '船头，半缠短衣，绑腿，船夫装束',
    '水夫头': '水夫头，半缠卷袖，短衣布',
    '水夫':   '水手，半缠短甲布，轻捷',
    '掌柜':   '掌柜，素色小袖配羽织，圆滑精明',
    '伙计':   '伙计，短打小袖，脚不沾地地忙碌',
    '锻冶匠': '锻冶匠，围裙短袜护臂，壮实',
    '医师':   '医师，素色小袖，背药笼，沉静',
    '僧侣':   '僧侣，法衣袈裟，剃发',
    '茶人':   '茶人，薄色小袖与羽织，清雅简素',
    '商人':   '商人，素色小袖配羽织，圆滑精明',
    '公家':   '公家贵族，狩衣与立乌帽子，白面文雅',
    '无效':   '平民，素色小袖，朴实无华',
}
TEMPER_FACE = {'性急': '眉峰紧锁，神情锐利急切', '温和': '眉眼舒展，神情温厚沉静',
               '冷静': '面无波澜，眼神冷峻', '豪放': '眉目开阔，神情豪迈'}
SPIRIT_FACE = {'勇敢': '目光炯炯有神，下颌绷紧', '胆小': '眼神谨慎游移，肩略收',
               '普通': '神情平和'}

# ---------- 女性模板（2026-08-28：阿市/誾千代试跑新增；女性单独一套服饰/面部规则） ----------
FEMALE_DRESS = {
    '公主':   '战国贵女：浅色小袖与绯红打褂，举止端仪',
    '女城主': '巾帼城主：束发高髻，深青雁羽纹打褂，腰佩细刀，女中豪杰',
    '女将':   '女武将：轻羽织配半甲，飒爽军装',
}
FEMALE_FACE = ('面容清丽写实，秀眉凤目，气韵端庄自然，绝不卖萌不娇艳媚俗；'
               '无月代、不蓄须，束发高髻或编发')
# R 版（有底稿）用：须发/发型交底稿（REF_HINT），只留面部气质句
FEMALE_FACE_BARE = '面容清丽写实，秀眉凤目，气韵端庄自然，绝不卖萌不娇艳媚俗；'

def character_layer(h, include_appearance=True, include_dress=True):
    """形象层。include_dress=False（R 版，有 TK5 底稿）：服饰/须发交给底稿，只留面容气质
    ——2026-08-28 用户裁定分层裁剪：教训 = 身份层『头戴乌帽子』把 195 信长底稿的
    束发髻+黑甲绯红披风覆盖成了奇怪帽子+黑金袍。"""
    # 🔴 形象还原优先（2026-08-28 用户裁定）：有「外观描述_光荣」的角色，
    #    发型/年龄感/表情/服饰一律以描述为准——跳过身份服饰、性情表情、蓄须规则，
    #    禁止表字段覆盖底稿特征（教训：大名=乌帽子 把 517 秀吉的白钵卷马尾覆盖了）。
    app = (h.get('appearance') or '') if include_appearance else ''
    if app:
        who = '女性' if h.get('gender') == '女' else '男性'
        return '。'.join(['%d 岁的日本战国时代%s' % (int(h['age']), who),
                          app,
                          '发型、年龄感、表情与服饰以上述形象描述为准，'
                          '禁止另加乌帽子、头盔、银发老态或与描述冲突的特征。']) + '。'
    if h.get('gender') == '女':
        ident = h['identity']
        dress = FEMALE_DRESS.get(ident, FEMALE_DRESS['公主']) if include_dress else ''
        face = FEMALE_FACE if include_dress else FEMALE_FACE_BARE
        parts = ['%d 岁的日本战国时代女性' % int(h['age']), dress, face]
        if include_appearance and h.get('appearance'):
            parts.append(h['appearance'])
        return '。'.join(p for p in parts if p) + '。'
    ident = h['identity']
    dress = IDENTITY_DRESS.get(ident, IDENTITY_DRESS['无效']) if include_dress else ''
    build = ('体格健壮，武人身形' if int(h['force']) >= 75
             else ('体形清瘦，文吏气质' if int(h['force']) < 60 else '体格匀称'))
    face = '，'.join(x for x in [TEMPER_FACE.get(h['temper'], ''),
                                 SPIRIT_FACE.get(h['spirit'], '')] if x)
    if include_dress:
        beard = ('留着整洁的黑色短须与唇髭，面容干练、无皱纹无老态'
                 if int(h['age']) >= 30
                 else '面部整洁无须，或仅存短髭')
    else:
        # 须发归底稿；无老态句保留（底稿不提供年龄感信息）
        beard = '面容干练、无皱纹无老态' if int(h['age']) >= 30 else ''
    parts = ['%d 岁的日本战国时代人物' % int(h['age']), beard, dress, build, face]
    # 光荣形象描述（xlsx「外观描述_光荣」列，update_appearance.py 维护）：有则注入
    if include_appearance and h.get('appearance'):
        parts.append(h['appearance'])
    return '。'.join(p for p in parts if p) + '。'

def build_prompt(h, style_boost=False, has_ref=False, include_appearance=True,
                 composition_boost=False):
    style = STYLE + ('严格遵守写实厚涂CG画风，坚决禁用任何浮世绘、水墨、工笔或扁平插画倾向。'
                     if style_boost else '')
    # 有底稿（R 版）：服饰/须发交给底稿（REF_HINT），裁掉身份装束段（2026-08-28 用户裁定分层裁剪）
    char = character_layer(h, include_appearance, include_dress=not has_ref)
    if composition_boost:
        # 构图铁律开头+结尾双出现；有底稿时 REF_HINT + 对抗句（禁跟底稿姿势）
        segs = [style, COMP_RULE, char, composition()]
        if has_ref:
            segs += [REF_HINT, REF_ANTI_POSE]
        segs += [NEG, COMP_RULE]
    else:
        segs = [style, char, composition(), NEG]
        if has_ref:
            segs.append(REF_HINT)
    return '，'.join(segs)

# ---------- API ----------
def data_uri(path):
    mt = mimetypes.guess_type(path)[0] or 'image/jpeg'
    with open(path, 'rb') as f:
        return 'data:%s;base64,%s' % (mt, base64.b64encode(f.read()).decode())

def generate(prompt, ref=None, seed=None, timeout=300):
    """主生图入口。gpt-image-2 = /images/edits + images:[{image_url}]（b64 输出）；
    其余模型（豆包）= /images/generations + image（URL 输出）。"""
    cli = BASE.rstrip('/') + ('/images/edits' if MODEL.lower().startswith(('gpt-', 'gptimage', 'gpt_image')) else '/images/generations')
    if 'gpt' in MODEL.lower():
        body = {'model': MODEL, 'prompt': prompt, 'size': '1024x1536',
                'output_format': 'png', 'quality': 'medium', 'background': 'opaque'}
        if seed is not None:
            body['seed'] = seed
        if ref:
            refs = ref if isinstance(ref, list) else [ref]
            body['images'] = [{'image_url': r} for r in refs]
    else:
        body = {'model': MODEL, 'prompt': prompt, 'size': GEN_SIZE,
                'response_format': 'url', 'watermark': False}
        if seed is not None:
            body['seed'] = seed
        if ref:
            body['image'] = ref
    req = urllib.request.Request(cli,
                                 data=json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': 'Bearer ' + KEY})
    r = json.load(urllib.request.urlopen(req, timeout=timeout))
    d = r['data'][0]
    return {'type': 'b64' if 'b64_json' in d else 'url',
            'val': d['b64_json'] if 'b64_json' in d else d['url']}

def billing():
    try:
        req = urllib.request.Request(BASE + '/dashboard/billing/usage',
                                     headers={'Authorization': 'Bearer ' + KEY})
        return json.load(urllib.request.urlopen(req, timeout=30)).get('total_usage')
    except Exception:
        return None
