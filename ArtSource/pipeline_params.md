# 立绘生成管线参数速查（2026-08-28 快照）

> 用途：**当前参数全貌**——查询、交接、防止走回头路。修改任一常量后同步本文件。
> 管线入口：[quick_one.py](#命令行) 最快；参数源 = [gen_portrait.py](gen_portrait.py)（提示词模板唯一事实源）。
> 数据流：`TaikouHero.csv` → `gen_portrait.build_prompt` → 雷火网关（豆包 seedream）→ `raw/` → `matte_rembg/` → 闸门。

---

## 1. 调用链总览

```
TaikouHero.csv ──load_heroes()──> h{age,identity,temper,spirit,force,appearance...}
        │
build_prompt(h, has_ref, include_appearance, composition_boost)
  段：STYLE → [COMP_RULE?] → character_layer → composition() → [REF_HINT + REF_ANTI_POSE?] → NEG → [COMP_RULE?]
        │                        （R 版裁身份服饰/须发；A 版全量）
generate() ──> 豆包 /images/generations ──> raw/quick_<sid>_<中文名>.jpg
```

## 2. API 参数（gen_portrait.py 顶部）

| 项 | 值 | 备注 |
|---|---|---|
| BASE | `https://ai.leihuo.netease.com/v1` | env `LEIHUO_BASE` 优先，`api_config.json` 兜底（gitignore，key 不打印） |
| MODEL | `doubao-seedream-5-0-260128` | `gpt-*` 走 `/images/edits` + `images[]` + b64 输出；豆包走 `/images/generations` + url 输出 |
| SIZE | 豆包 `1568x2352`（服务门槛 3,686,400 像素下最省的 2:3 档）；gpt `1024x1536` | 生成时间 ~40-50s/张（日志实测） |
| 输出 | `response_format=url`、`watermark=false`；seed 固定传 body | seed 同值 = 同图（同版本内）；换 seed = 重新抽签 |

**seed 约定**：A/E 版 = 1001/1002；R 版 = 2001；重跑 = 2002 起递增（`QUICK_SEED` 可覆盖）。

## 3. 环境变量开关

| 开关 | 值 | 效果 | 结论 |
|---|---|---|---|
| `QUICK_BOOST` | `1` | 构图铁律 + REF 对抗句（开头/结尾双出现） | 🔴 **确认无净效果**（同 seed：0.003 → -0.024 不救回），默认 OFF，仅 A/B 用 |
| `NOBU_MIRROR` | `1` | 信长底稿换 `195_织田信长_朝右.png` | ✅ **2026-08-28 过闸关键**（头跟底稿走，镜像翻正锚点，seed 2002 一次 PASS） |
| `NOBU_REF` | `1154` | 信长换青年版 `1154_织田信长_朝左.png` | 备选 |
| `QUICK_SEED` | 数字 | quick_one 指定 seed | 默认 2002 |

## 4. 提示词分段（build_prompt 组装顺序）

| 段 | 参数 | 内容 | 变否 |
|---|---|---|---|
| ① 风格层 | `STYLE` | 光荣战国立绘 CG 写实厚涂 + 戏剧光影 + 电影级调色 / 禁偶像脸磨皮 | 全人固定 |
| ①b 构图铁律 | `COMP_RULE` | 脸朝右/左肩近右肩远/禁平视禁双肩齐（**仅 boost**） | 全人固定 |
| ② 人物层 | `character_layer(h, include_appearance, include_dress)` | 见 §5 | **每人不同** |
| ③ 构图层 | `composition()` | 竖幅半身/脸朝右+左肩近景对角透视/头占 1/4（24~28%）/人物高 9 成/头顶留白 8%/中轴 ≤55%/禁贴右缘/风暴天空无杂物 | 全人固定 |
| ④ 负面词 | `NEG` | 26 项：浮世绘/漫画脸/正面直视/贴右缘/文字水印/多人物… | 全人固定 |
| ⑤ 底稿约束 | `REF_HINT` | 参考图只借：面部骨相、发型须发、标志性服饰（**形制与配色**）；姿势/构图/画风/光影/背景一律重绘 | 仅 R 版 |
| ⑤b 对抗句 | `REF_ANTI_POSE` | 构图姿势以提示词铁律为准，禁止跟随底稿姿态（**仅 boost**） | 仅 R 版 |

## 5. 人物层规则（含全部裁剪裁定）

| 规则 | 现状 | 裁定日期 |
|---|---|---|
| 身份服饰 `IDENTITY_DRESS`（29 类）/ `FEMALE_DRESS` | **R 版（有底稿）裁掉**——服饰/发型交底稿（REF_HINT）；A 版（无底稿）保留（唯一服装来源） | 2026-08-28 分层裁剪 |
| 武器段 `WEAPON` | **整表已删除**（枪/刀剑/弓/铁炮四句 + 女性「腰佩细刀」兜底） | 2026-08-28 用户裁定 |
| 须发（黑短须/无须短髭） | R 版裁（交底稿）；「面容干练、无皱纹无老态」**保留**（底稿不提供年龄感） | 2026-08-28 |
| 体格（force ≥75 健壮 / <60 清瘦） | 保留 | — |
| 性情/精神（TEMPER_FACE/SPIRIT_FACE） | 保留 | — |
| 外观描述列注入 | `PATCH_DESC` 细节补丁制：仅秀吉；注入=「以描述为准，禁止另加乌帽子/头盔/银发老态」 | 2026-08-28 形象还原优先 |
| 年龄 | 公式：首末登场年代中点 − 生年，钳制 [18,55]；`OVERRIDES` 可人工覆盖（阿市27/訚千代25/秀吉21=对齐底稿） | — |

## 6. 闸门参数（gate.py / verify_pose.py）

| 闸门 | 判据 | 门槛 | 状态 |
|---|---|---|---|
| 脸朝向 face_gate | 鼻x − 双眼中点x（`V.judge`） | **≥ 0.030**（脸清晰朝画面右） | ✅ 现行 |
| 肩轴 shoulder_gate | 解剖右肩x − 解剖左肩x（mediapipe） | **≤ -0.15**（近景肩=右肩在画面左） | ✅ 现行（2026-08-28 修复） |
| 剪影比 shoulder_ratio | 上半身带画布左/右半像素比 | [1.05, 1.65] | ⚠️ **已降级**：仅参考输出，不作闸门（同图 −0.358 ✅ vs 0.149 ❌ 打架实证） |
| 分类带（face_dir 标签） | 鼻偏 | ±0.003；外按符号 LEFT/RIGHT | 2026-08-28 收窄（原 ±0.012 吞符号） |
| 漏检 | — | None = FAIL（宁可重跑） | 设计如此 |

**标定样本（旧剪影数，仅对照）**：阿市 1.10 / 幸村 1.49 / 信长 0.73 / 訚千代 0.95 / 秀吉 1.93。

## 7. 底稿命名与台账

命名：`{编号}_{姓名}_{朝左|朝右|朝正}.png`。
**判向 = 感知仲裁（2026-08-28 用户裁定）**：近正图 mediapipe 鼻偏不可靠（面罩/额带/眉形干扰鼻尖定位——
886 面罩判出 +0.007 假右、517 钵卷判出 +0.001 假正），文件名朝向以**用户肉眼**为准。
规则：|face_rel| > 0.003 按符号判向；近正（|x| ≤ 0.003）与戴面罩/额带类由用户肉眼逐张校准——
校准表 = `annotate_orient.py` 的 `PERCEPT_OVERRIDE`（机器台账 orientation.json 同时存值与感知标签）。

**感知校准 5 张（2026-08-28）**：517 秀吉→朝左（+0.001 钵卷干扰）；517 镜像→朝右（感知翻转，1057 先例）；
1012 海贼→朝左（-0.002）；952 商人→朝右（-0.001）；886 忍者→朝正（+0.007 面罩假右）。

**判向原则（2026-08-28 用户裁定，最高优先级）**：**台账 = 人眼仲裁为主、脚本测量为辅**——
人名（_朝左/_朝右/_朝正）以用户肉眼为准，脚本测量值（face_rel）只作参考与兜底
（近正看图时鼻偏为感知代理，面罩/额带/眉形会干扰鼻尖定位）；脚本侧设有
`PERCEPT_OVERRIDE`（annotate_orient.py 内）保护人眼裁定不被重测覆盖。

**已知保留项（记录在案的边界）**：① `891_无卡忍者_朝左` 肩轴 = null（mediapipe 未检出肩膀，
画幅遮挡）——方向标记完整，肩轴数据缺；② `517_丰臣秀吉_朝右` 为镜像翻转推得
（原版微左 → 镜像微右），用户尚未亲眼核对，数值仅 +0.002 作不了证。

| 台账 | 内容 | 刷新方式 |
|---|---|---|
| `refs_koei/_tk5/meta.json` | 人读台账：desc + orientation（幅度+肩轴） | 手工 |
| `identity_refs.py` `IDENTITY_REF` + `ORIENTATION` | 身份 → 底稿映射 + 朝向 | 手工 |
| `refs_koei/_tk5/orientation.json` | 机器台账（30 张实测值） | `python annotate_orient.py` 重刷 |

**实测分布（2026-08-28 感知校准后）**：全部 30 张 = **LEFT 23 / FRONT 2 / RIGHT 5**。

**关键锚点强度**：195_织田信长_朝右（+0.025，强锚，seed 2002+boost 实证过闸：face 0.041 / 肩轴 -0.298）；
517_丰臣秀吉_朝右（镜像，感知翻转推得，实测 +0.002 仅供参考）；1057_訚千代_朝右（+0.007，**弱锚**）；1162_真田幸村_朝右（+0.006，弱锚）。

**用图规则**：朝左 → 生成前运行时 PIL 镜像；朝正 → 镜像无效靠 seed；朝右 → 直接用（目前只有 195 一张）。

## 8. 命令行

```bash
python quick_one.py lord_1_oda              # 快速单张（~45s，跳 matte/闸门/账单）
python quick_one.py lord_1_azai_1 517...    # 多人顺次；QUICK_SEED / QUICK_BOOST / NOBU_MIRROR 随时接
python run_trial.py [a|e|r|f|w]             # 三人/女性试跑（r=R版 img2img）
python rerun_gates.py lord_1_oda            # 完整管线：生成→matte→脸闸+肩轴闸，不过换 seed ≤3，写 gate_rerun_log.json + preview 拼图
python gate.py check                        # 复算 matte_rembg/ 全部成品两闸（含剪影参考）
python annotate_orient.py                   # 重测底稿朝向 → orientation.json
python matte_rembg.py                       # 全量抠图 + 质检 + preview 拼图
```

## 9. 已定结论（勿走回头路）

1. **镜像底稿是头朝向的唯一解开方式**——头 100% 跟底稿走，prompt 压不住（boost 三遍构图铁律零效果）；躯干靠构图指令 + 底稿镜像后自然归位。
2. **boost 无净效果**——默认关，保留为 A/B 开关。
3. **闸门 = 解剖法**（脸 0.030 + 肩轴 -0.15），剪影法历史推翻。
4. **R 版裁身份服饰**；**WEAPON 删除**；**文件名带朝向**（用户裁定：文件名即第一视角）。
5. 身份底稿 20 张中 15 张朝左 → 批量生成身份 NPC 时记得镜像（或日后接 AUTO_MIRROR）。

## 10. 未归档待办

- `_tk5_orientation_raw.json`（临时中间产物）可删，已被 orientation.json 取代。
- `AUTO_MIRROR=1`（出图前自动测底稿朝向 → LEFT 即镜像）未实现——目前靠 `NOBU_MIRROR` 手动。
