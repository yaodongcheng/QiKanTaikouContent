using TaleWorlds.MountAndBlade;

namespace ShokuhoTaikouExpansionPack
{
    /// <summary>
    /// 织丰补充包入口（骨架阶段：空壳，不产生任何行为）。
    ///
    /// 定位（plan 07 方案 A）：织丰的剧本层载体，一个包承载：
    /// 1. 兼容层（07a 曾实施，2026-08-25 删除）：1.5.1 硬不兼容（GetTypes 86 个 API 签名差异）、
    ///    1.2.12 原生可运行——无使用场景；实现细节见主仓库 plan 07a 证据链实录
    /// 2. 剧本层（plan 07/01-06 审核通过后）：剧本入口 / 时间覆盖 / 剧本行为注入。
    ///
    /// 🔴 实施纪律：剧本工程全部 plan 审核通过前，本类保持空壳。
    /// </summary>
    public class MySubModule : MBSubModuleBase
    {
        protected override void OnSubModuleLoad()
        {
            base.OnSubModuleLoad();
            // 剧本层实施逻辑待 plan 07 审核通过后写入
        }
    }
}
