# scripts/ — 内容包生成脚本（唯一事实源）

> 铁律 22：本目录 = 唯一事实源。改内容 = 改这里 - 重跑 - 验收输出。
> 2026-09-02 用户裁定：立绘/换脸脚本从 ArtSource/scripts/ 迁到本目录（可入库）；ArtSource 只剩图片素材（全忽略）。
> 运行契约：脚本自带 chdir 回 ArtSource（api_config.json / refs_koei / raw 相对路径），任意目录 `python scripts/xxx.py` 即可；
> 依赖：Python 3.12 + numpy/PIL/mediapipe/cv2/rembg + 雷火 API key（ArtSource/api_config.json，禁入 git）。

## 换脸/头部管线（2026-09-02）
- `decode_miniface.py` - -*- coding: utf-8 -*- /// MINIFACE DDS(BC1/BC3) → PNG 解码器（换脸管线参考图用；numpy+PIL，零外部依赖） /// 用法: decode_miniface.py <src.dds> <out.png>
- `quick_bigface.py` -  quick_bigface.py                      # 默认 3 张（seed 2002/2003/2004） quick_bigface.py 2002 2006            # 指定 seed 参考图 = MINIFACE/195_织田信长/000.dds 解出的正脸头像（refs_koei/_tk5_face/）。  import base6
- `gen_portrait.py` - import base64, io, json, mimetypes, os, sys, time, urllib.request from concurrent.futures import ThreadPoolExecutor  # 取配置：环境变量优先，ArtSource/api_config.json 兜底（已 gitignore）。 # 全程只读取、永不打印，避免 key 溅进日志/会话（2026-08-2
- `quick_one.py` -  quick_one.py <sid> [sid...]        # 英雄：lord_1_oda 等 quick_one.py 1112                  # 身份底稿：数字 = identity/{编号}_*.png quick_one.py --all                 # refs_koei 全部底稿各一张（27 张，~25 分
- `verify_pose.py` - 方向裁判：用 face/pose 关键点坐标（mediapipe 0.10.14）对生成图判「脸方向 + 肩部转向」， 替代肉眼判读（2026-08-28：肉眼左右判读存在系统性镜像误读，改数字判向）。  判据（用户标定，锚定样本 = 阿市 / 訚千代；用户按解剖语言说「右肩近镜」）： face  : 鼻 x − 双眼中点 x ≥ 0.030 → 脸清晰朝画面右（RIGHT） sh    : 解剖右肩 x − 解剖左

## AI 生图主链（立绘批量）
- `run_batch.py` - 范围：TaikouHero.csv 全部 1047 名英雄 + 身份模板 19 张（15 有底稿 R 版 + 4 无底稿 A 版）。 分档： R 版（有 TK5 底图）= gpt-image-2 /images/edits + images[]（¥0.40/张，种子 2002 起） A 版（无底图）= gpt-image-2 /images/generations（2026-08-29 探测可用，￥0.33/张，种子
- `run_trial.py` - 2026-08-28 用户裁定：维基古画参考图退役（画风不符现代审美），B/C/D 变体废弃。
- `stage_pipeline.py` - 不在 manifest 主形象 = raw 已有) → 底稿转置 → R 版生成 + 双闸 → 追加 build_log.csv (key = '{sid}#{stage}')，pick_gui 第二轮窗口按同机制审。 stage_pipeline.py [--refs-only]  import base64, csv, glob, io, json, os, sys, time, urllib
- `rerun_gates.py` - 判定循环 = 生成 → matte → 脸闸(RIGHT≥0.030) + 肩带闸(∈[1.05,1.65]) → 任一不过换 seed。 与上一轮 R 版完全同参数（同底稿/同 prompt 语义），只改 seed；通过后留底并记 gate_rerun_log.json。 rerun_gates.py  import io, os, json, sys, time, urllib.request
- `rerun_remaining.py` - 缺口（250）= 块1 旧83清单 + 块2 新缺口158（无卡池/零散）+ 块3 阶段版FAIL 9。 卡 → 身份 prompt：CSV 反查 tkid → StringId 行 → h（列抽取 + RT.OVERRIDES；模板/英雄统一）。 复用 run_batch 的 job_run/gate/pack_row/write_rows/existing_done（MAX_ATT=2）。 key：普通卡 = t
- `gate.py` - 🔴 2026-08-28 闸门修复：肩闸由剪影法（M.shoulder_ratio 像素比）切回解剖法—— 同图实测两指标打架（信长 boost 版：解剖 -0.358 ✅ vs 剪影 0.149 ❌），用户肉眼+解剖 一致 = 躯干对、脸单偏。剪影法失准根因：①画布中轴≠躯干中轴（紧贴裁切+居中+头偏时错位） ②远侧胸甲硬件占像素多 ≈ 假「近大远小」。解剖法原文义见 verify_pose.py（用户「右肩近镜」
- `rescue_mirror.py` - 用法（跑批完成后）： rescue_mirror.py --review            # 重测全部 raw 尝试文件 → _review/review_manifest.csv rescue_mirror.py --rescue            # FAIL/PASS_EYES 的 key 逐尝试文件镜像 → 双闸 → 第一个过=RESCUED rescue_
- `eye_screen.py` - 方法：FaceMesh 眼框四点 → 眼区灰度 → 虹膜（暗质心）vs 眼白（亮区）质心偏移： offx = 虹膜x - 眼区中心x；两眼的 offx 平均 < -0.01（眼宽归一）= 眼神左，> +0.01 = 右。 输出：refs_koei/eye_dirs.csv（file, offx, eye_dir）——eye_dir ∈ L/R/F/N（N=检测失败）。 eye_screen.py 
- `diag_nobu.py` - from PIL import Image, ImageDraw, ImageFont import os  files = [ ('底稿 195 信长', 'refs_koei/_tk5/195_织田信长_朝左.png'), ('底稿 1154 信长', 'refs_koei/_tk5/1154_织田信长_朝左.png'), ('原 R seed2001(0.73)', 'raw/lord_1_oda_织田信长_R

## TK5 参考图转换与判向
- `build_refs_full.py` - CSV（1047 英雄）→ TK5 BUSTUP（E:/taikou5/TaikouImage/BUSTUP/{编号}_{简体名}） 匹配（CNName）→ 000.dds → PNG → verify_pose 判向 → 朝左镜像 / 朝右原样 / 朝正标注 → 存 refs_koei/_tk5/{编号}_{姓名}_{朝右|朝正}.png（现有 7 张同名覆盖为同规则生成物） + hero_refs_manifes
- `apply_verdicts.py` - 🔴 v2 修复：v1「对当前文件再镜像」非幂等——补 1279 时全表重跑，L 项二次镜像 = 翻回反面， 用户抓包（1288 被覆盖回朝左）。v2 一律 **从 E 盘源 dds 重新转换**（不论当前文件处于 多少次镜像态），L = 源→镜像一次落 _朝右；F = 源→原样落 _朝正。结果 = 唯一正确终态。 只动 VERDICT 列的角色，其余 0 改动。跑完 build_refs_full 重刷 manife
- `ref_verdicts.py` - 规则（用户裁定）：L = 身体偏左 → 整图镜像 → 朝右（身体优先，脸翻左靠生成层 seed 补救）； F = 身正面微偏左+脸正（用户接受）→ 朝正中性锚；R = 已达标不动。 判向优先级：VERDICT > mediapipe face-only（build_refs_full.py 用）。 应用脚本：apply_verdicts.py（文件落地）→ build_refs_full.py（manifest 重跑
- `annotate_orient.py` - 写 refs_koei/_tk5/orientation.json（机器台账，可重跑刷新）。 人工台账（meta.json / identity_refs.py 的 ORIENTATION）以此文件为测量源。 annotate_orient.py   （本地 mediapipe，~1 分钟，零 API 成本）  🔴 人名 = 感知仲裁（2026-08-28 用户裁定）：近正图 mediapipe 
- `enforce_right.py` - 扫描 refs_koei/_tk5/** 下全部 *_朝左.png（主目录旧资产 + identity 身份模板）， 镜像处理 → 写为 _朝右（已存在同名朝右则覆盖为镜像版一致性检查后删朝左）， 最终全目录 0 个朝左。朝正（FRONT, 108 张）保留：正脸无法靠镜像变侧脸，属中性锚 （生成时无方向锚，靠 seed 抽——朝正不是"朝左"，不违反禁令）。  enforce_right.py 
- `ensure_ref_all.py` - diff = BUSTUP 全 tkid − refs 已转 tkid → 逐个 ensure_ref（dds→判向→朝右化，近正/漏检落朝正）。 幂等：已有 _朝右/_朝正 跳过；缺 000.dds 跳过并报告。零 API 成本。 ensure_ref_all.py [--limit N]   # 缺哪些 id 单独提示输到 _missing_refs.txt  import glob, os,
- `extract_features.py` - 对 refs_koei/_tk5/*.png 全量抽取 6 维特征向量 + 真值标签列： features = [ratio(脸心-肩距比 dL/dR), shd(肩轴), dy(双肩垂直差), nose(鼻偏), sw(双肩宽比), dyNear(脸心-近肩垂直差)] 标签列 groundwork: label = R/F/L（0=无真值）— 真值源 = ref_verdicts.py + 用户口述清单。 输出：r
- `extract_identity_refs.py` - 把「每身份一张代表」所需的全部候选项从 E:/taikou5/TaikouImage/BUSTUP 转 PNG 入 refs_koei/_tk5/identity/（gitignore 覆盖整目录），并生成带编号的预览拼图 preview/identity_contact_*.jpg，供人眼选代表（无卡X 组 55~62 张/组，只用看拼图挑）。  import os from PIL import Image  S
- `identity_refs.py` - 来源：E:/taikou5/TaikouImage/BUSTUP（本机真源，gitignore 不入库），转换件在 refs_koei/_tk5/identity/{编号}_{姓名}_{朝左/朝正}.png —— 用了哪张 = 本表唯一事实源； 2026-08-28 文件名带朝向（用户裁定：文件名即为第一视角，_朝左 = 实测脸朝画面左，生成构图需镜像）。 注意：TK5 通用立绘只有一批固定类型；表格里标注「借」的 
- `make_identity_picks.py` - import os from PIL import Image, ImageDraw, ImageFont  DIR = 'refs_koei/_tk5/identity  # 身份 → 底稿 ID（2026-08-28 用户裁定：一个 TK5 类型一张，与 identity_refs.py 一致） PICKS = [ ('商人', 952), ('忍者', 886), ('海贼(船系)', 1012), ('海贼头
- `build_template_map.py` - ① 简繁异性之名 = 并；② 教头=师范（代分开）；③ 足轻/海贼船系等级不可并； ④ 町民（同性）可并；⑤ 未批的相似（店家×店/商人来源/公主系）= 保持独立； ⑥ 双性别职业 _male/_female 分开。 输出：_template_id_final.tsv（ScriptName → template_id 终映射，供用户终批 → 迁移执行）。  import csv, io, sys from colle

## 抠图/画布
- `matte.py` - import numpy as np, os, sys from PIL import Image, ImageFilter  OUT_W, OUT_H = 512, 768 AXIS_LO, AXIS_HI = 0.55, 0.62      # 人物中轴必须落在画布横向 55%~62%  def key_by_border(img, tol=42.0, soft=18.0):
- `matte_rembg.py` - P5 已落地（2026-08-28）：不再做中轴平移，紧贴人物裁切、水平居中、贴底对齐， 512 宽全部给人物。「脸偏右」由画面内朝向实现，不由画布内平移实现。 🔴 2026-08-30 模型选型：isnet-general-use（丢部件：深色甲×深背景误删手臂/袖子； 实测 987/16 两案缺臂）→ 对比实验中 u2net 肢体完整率最高、边缘干净、0.2-0.9s/张 （birefnet-general 完整
- `collect_selected.py` - ① 校验：picktkid 全部 tkid 状态分布（期望：仅 chosen/dropped，redraw=0，无「未定」）。 ② 收集：按 chosen（+ mirror 翻转）把 raw/ 成品 → selected/{tkid}_{StringId}.png（后续处理源头）。 mirror=1 的做左右镜像翻转（选图窗口的镜像预览 = 成品方向）。 幂等：已有目标文件跳过；输出统计与缺失清单。 pytho

## 审核 UI 与选定台账
- `pick_gui.py` - 记录单位 = 一张底稿卡（tkid）：每卡 = 一个审批位（chosen 选定 / dropped 作废 / redraw 待重生成+意见）。 唯一台账 = _review/picktkid.json（键 = tkid；picks.json/redraw.json 已是旧档只读）。 无底稿的图（A 版）不进入审批队列（避免「没有底稿还出图被审」）。 筛选三态：全部 / 只看未审 / 只看待重生成（待重生成的卡显示标记
- `pick_finish.py` - ① mirror=1 的镜像翻转 ② 全尺寸规范命名 normal 成品 ③ 台账文件 final_manifest.csv。 输入：_review/picks.json（pick_gui.py 产出）+ raw/ 尝试文件 输出：final/{sid}_{cn}.png（翻转后的正常向全尺寸图 = 情绪/头像/抠图/TPAC 的统一输入） _review/final_manifest.csv（sid, cn, sr
- `build_picktkid.py` - 新结构（键 = tkid，值 = 该卡的审批意见）： {"913": {"sid": "template_merchant_01", "cn": "无卡商人", chosen": "tk913_无卡商人_R2.png", "mirror": 0, dropped": false, "redraw": "", "legacyA": false}, ...} chosen  选定的成品文件名（空 = 未定） droppe
- `make_stage_boards.py` - 产出：preview/stage_boards/b{:02d}.jpg（每板 8 人，每格 = 一人全部阶段图并排）。 make_stage_boards.py [--from N]    # 从第 N 板开始  import os, sys, json, re from PIL import Image  SRC = r'E:\taikou5\TaikouImage\BUSTUP TSV = '

## 成品打包（立绘→内容包）
- `build_profileassets.py` - 输入：_review/picktkid.json（chosen=用户认证的成品）+ selected/（= 用户选定+镜像，2026-08-30 末定：源头）； 兜底 raw/（selected 缺时）。 产出：ArtSource/ProfileImage/{tkid}_{StringId}_bustup_normal.png   （半透明立绘 512x768，matte+place 贴底） ArtSource/Pr
- `build_profile_pack.py` - 输入： ProfileImage/                     bustup 512x768 + minihead 256x256（终版图谱） ProfileImage/emotion/             17 卡 x 4 情绪（bustup + minihead） Knowledge/.../csv/ProfileImage.csv tkid,StringId,bustup,minihead（上游
- `deploy_portraits.py` - 2026-08-30 用户定：图归补充包（世界观的肉 = 内容包资产）；CSV 暂留织丰目录 （Knowledge/骑砍2织丰角色ID对应/csv/ProfileImage.csv，功能稳定后再搬）。 数据来源 = ProfileImage.csv（唯一事实）——按 CSV 每行的 bustup/minihead 路径逐文件复制， 复制后校验尺寸（bustup 512x768 / minihead 256x256），
- `make_avatars.py` - 定位三层（从优到兜底）： 1. mediapipe face bbox（verify_pose.judge['face_bbox']，顶部已外扩盖发髻/盔帽） 2. OpenCV Haar 正脸 → 还原成正方形 3. 构图比例兜底（提示词铁律：头占高 24~28% / 头顶留白 8% → 头带 y∈[0.10,0.36]） 裁切：以脸框为中心取正方形（max(W,H)×1.12 边），从**原图 raw** 裁（全
- `update_portrait_stages.py` - 列含义（一单元格 = 一个 JSON 数组，一条 = 一个形象阶段）： [{"stage":"若君","tkid":"1154","ref":"1154_织田信长_朝右.png","emotion":1}, ...] 字段：stage   阶段词（TK5 时期名/身份词；普通单图人物 = ""） tkid    TK5 BUSTUP 编号（决定 refs_koei/_tk5 取图路径） ref     已转好的朝右底
- `update_appearance.py` - 光荣形象描述 → 太阁数据主源 CSV（Knowledge/骑砍2织丰角色ID对应/csv/TaikouHero.csv）。  2026-08-28 数据源裁定：主源 = Knowledge/.../csv/（用户让其他 agent 从 xlsx 导出的最新版）， xlsx 退役为归档（不再维护）。该 CSV 已有「外观描述_光荣」中文列（其他 agent 导出时保留了 xlsx 列名），本脚本按 ID 填充/刷新，
- `repair_csv.py` - base = git HEAD（已有：模板NPC列+标记 / TK5编号列 / 立绘阶段/模板列空壳）。 目标态（与受损前一致）：1119 行 · template_ 70 行 · 各列全填。 步骤带计数断言，跑完与 COORD 常量核对。  import csv, io, json, os, re, sys sys.path.insert(0, os.getcwd()) import build_template_
- `emotion_edit.py` - ① 参考图 = selected/ 对应当前图（用户审定正式图，姿势/镜像一致，只改表情） ② 目录 = ProfileImage/emotion/ 专用子文件夹（normal 留根） ③ 命名 = emotion/{tkid}_{StringId}_bustup_{emo}.png / …_minihead_{emo}.png（第 4 段 = 情绪） ④ 名单 = 9 人 17 卡（plan §二「emotion 

## 地图/剧本层
- `gen_map_patch.py` - 用途：本包发布形态 = 自带织丰整张地图 + 剧本层新增据点实体（场景文件无增量通道， 只能整目录覆盖织丰的 Main_map；本包在织丰之后加载，地图覆盖生效）。  做什么： 1. 从织丰模块拷贝 SceneObj/Main_map 全套（52MB：scene.xscene + terrain/flora/navmesh bin 等） 2. 在 scene.xscene 中克隆 Kameoka（village_KI

## 一次性/探测
- `_probe_gpt_gen.py` - import json, time, urllib.request import gen_portrait as G  print('billing before:', G.billing()) t0 = time.time() body = {'model': 'gpt-image-2', 'prompt': '测试：穿暗蓝色素袍的日本武将半身立绘，写实厚涂，侧脸朝右。', size': '1024x1536', 

> 详细说明在各脚本头部 docstring；描述如需修正以脚本注释为准（README 由脚本自述生成，2026-09-02）。
