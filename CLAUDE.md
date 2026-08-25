# ShokuhoTaikouExpansionPack — 织丰补充包

> **本包是 LivingWorldNpcs 的姊妹工程**：同一 VSCode/Claude Code 工作区（见 `../LivingWorldNpcs/livingworld.code-workspace`），但**独立 git 仓库、独立打包发布**。

## 本包是什么

织丰 mod（日本战国全量素材）的补充层，一个包承载两块：

1. **兼容层**（plan 07 方案 A 前提）——让织丰 DLL 在 1.5.1+ 加载成功：
   - 织丰 DLL 报 `dependency conflict` 的根因 = 游戏 `AssemblyLoader` 引用循环用相对文件名从游戏 bin 找第三方 DLL（0Harmony/ButterLib/UIExtenderEx/MCMv5 等），而它们在各模块 bin
   - 本模块通过 `SubModule.xml` 的 `ModulesToLoadAfterThis` 声明排在织丰之前加载，实施时：补丁 `AssemblyLoader.LoadFrom`（相对名 → 模块 bin 兜底）+ 预加载织丰依赖
   - 反编译证据链与版本验证矩阵见主仓库 `plans/scenario-campaign-mode/07-织丰接入与克隆注册层.md`
2. **剧本层**（01-06/08-17 剧本工程）——剧本入口 / 时间覆盖 / 剧本行为注入，数据全用织丰，**零资源搬运**

## 🔴 规则来源

**本包不重复规则，一切以主仓库为准**：

- 必读：[`../LivingWorldNpcs/CLAUDE.md`](../LivingWorldNpcs/CLAUDE.md)（铁律 1-20、wheels.md 索引、双配置体系、版本兼容）
- 工程总纲：[`../LivingWorldNpcs/plans/scenario-campaign-mode/README.md`](../LivingWorldNpcs/plans/scenario-campaign-mode/README.md)（会话交接、审核表、设计裁定）

## 铁律（本包特化）

1. 🔴 **剧本工程全部 plan 审核通过前，本包不写实施逻辑**（当前 = 能编译的空壳）
2. 🔴 **零资源搬运**：织丰的一切（场景/模型/贴图/数据文件）归织丰 mod，本包不复制不打包；兼容层只补程序行为
3. 🔴 **打包分开**：本包与 LivingWorldNpcs 各自独立打包发布；本包发布依赖：玩家装 织丰 + LivingWorldNpcs + StartAsAnyone + 本包
4. 🔴 **兼容层 DLL 不得引用 LivingWorldNpcs.dll**（AssemblyRef 存在即触发加载循环报错；剧本层若需引用 LWN，按 plan 07 实测结论拆 DLL）
5. 世界观铁律、StringId 铁律、本地化铁律等均继承主仓库（`../LivingWorldNpcs/CLAUDE.md`）

## 工程结构

- `SubModule.xml` — 模块声明（织丰前加载的关键在 `ModulesToLoadAfterThis`）
- `ShokuhoTaikouExpansionPack.csproj` — 对齐 LivingWorldNpcs 的 csproj 模式（MB2_PATH 环境变量 + 版本宏）
- `MySubModule.cs` — 入口（空壳）
- `ModuleData/` — 旧 TaikouContent 残留数据（待按 plan 07 审核结果决定保留/清理；当前 SubModule.xml 未注册任何 Xmls）
