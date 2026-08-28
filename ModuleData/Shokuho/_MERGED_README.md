# 本目录（ModuleData/Shokuho）收编说明（2026-08-28 合并）

原 `ModuleData/DesignData/` 与 `ModuleData/Shokuho/` 内容重复，已合并到本目录：

- 3 个生成物（clans/heroes/lords.xml）：原两目录各有拷贝（同字节），保留本目录一份
- `output_strings2.xml`（1789 条 my_* 中文串）：原仅 DesignData 一份，现并入（**必不可少**：753
  人生成物的中文名 key 都在这里；注册时 strings.xml 必须一并声明）
- 4 个手工示例/补丁原就在本目录：settlements.xml（KIN23——与基础织丰 mod 同 id，注册有双定义风险）、
  spcultures.xml（2 文化示例）、spkingdoms.xml（noKingdom）、my_helmets.xml（17 头盔）

重建命令：`python plans/scenario-campaign-mode/tools/GenerateXml.py`（输入 = csv/ 镜像，
产出与本目录 3 件 md5 完全一致；07c 裁定 1 后新管线产物将入 `ModuleData/Supplementary/`）。
