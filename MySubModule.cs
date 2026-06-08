using LivingWorldNpcs;
using System.IO;
using TaleWorlds.ModuleManager;
using TaleWorlds.MountAndBlade;

namespace TaikouContent
{
    public class MySubModule : MBSubModuleBase
    {
        protected override void OnSubModuleLoad()
        {
            base.OnSubModuleLoad();

            // ── 注入日本战国世界观 —— Mod A 的 PromptBuilder 自动生效 ──
            Settings.Instance.WorldDescription =
                "骑马与砍杀2织丰Mod塑造的日本战国世界";
            Settings.Instance.EraDescription =
                "日本战国时代";
            Settings.Instance.SpeechStyle =
                "风格口语化、口吻符合日本战国背景。使用符合时代的大河剧风格口语。多用反问、感叹。";
            Settings.Instance.WarriorTerms =
                "使用「在下」、「主公」、「混账」等日本战国武家词汇。";
            Settings.Instance.FemaleSelfAddress =
                "如果你是女子，需要有女子的说话风格，如「妾身」。";

            // ── 注入织丰数据表 —— 覆盖 Mod A 初始化时的空表 ──
            string designDataPath = Path.Combine(
                ModuleHelper.GetModuleFullPath("TaikouContent"),
                "ModuleData", "DesignData");
            GameDatabase.LoadTablesFromPath(designDataPath);
        }
    }
}
