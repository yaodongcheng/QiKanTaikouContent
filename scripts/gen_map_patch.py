#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""地图合成脚本（生成物纪律：铁律 22 —— 本包 SceneObj/Main_map 是脚本产物，禁止手改）

用途：本包发布形态 = 自带织丰整张地图 + 剧本层新增据点实体（场景文件无增量通道，
     只能整目录覆盖织丰的 Main_map；本包在织丰之后加载，地图覆盖生效）。

做什么：
  1. 从织丰模块拷贝 SceneObj/Main_map 全套（52MB：scene.xscene + terrain/flora/navmesh bin 等）
  2. 在 scene.xscene 中克隆 Kameoka（village_KIN5_1）实体块为新增村庄实体
     （实体模板 = 本包 ModuleData/settlements.xml 中的新区条目，按 id 匹配）
  3. 校验：实体存在且唯一、坐标与 settlements.xml 一致、地形文件齐全

用法：
  python gen_map_patch.py            # 织丰默认在 ../Shokuho（本脚本位于 Modules/ShokuhoTaikouExpansionPack/）
  python gen_map_patch.py --shokuho <织丰模块路径> --clean   # --clean 先清空目标目录再拷贝

织丰更新地图后：重跑本脚本即可（实体块自动从 settlements.xml 读取坐标，无需改动）。
"""

import os
import re
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(SCRIPT_DIR)                     # Modules/
DEFAULT_SHOKUHO = os.path.join(MODULE_DIR, "Shokuho")
TARGET_DIR = os.path.join(SCRIPT_DIR, "SceneObj", "Main_map")
SETTLEMENTS_XML = os.path.join(SCRIPT_DIR, "ModuleData", "settlements.xml")

# 新增据点条目：在此登记 id（settlements.xml 中的 <Settlement id=...>）
NEW_SETTLEMENT_ID = "village_tk_lianshui"


def log(msg):
    # 全 GBK 可编码字符：Windows PowerShell 默认 cp936 控制台，emoji（如 ✅）会抛 UnicodeEncodeError
    print(f"[gen_map_patch] {msg}", flush=True)


def fail(msg):
    log(f"[FAIL] {msg}")
    sys.exit(1)


def read_text(path):
    # newline="" : 禁止万能换行转换（scene.xscene 是 CRLF，读成 \n 再写回会改字节）
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def parse_new_settlement(text):
    """从本包 settlements.xml 提取新增据点的 id + posX/posY（单一数据源，坐标不手编）。"""
    root = re.search(r'<Settlement\b[^>]*id="%s"[^>]*>' % re.escape(NEW_SETTLEMENT_ID), text)
    if not root:
        fail(f"settlements.xml 中找不到 <Settlement id=\"{NEW_SETTLEMENT_ID}\"> 条目")
    attrs = dict(re.findall(r'([a-zA-Z_]+)="([^"]*)"', root.group(0)))
    if "posX" not in attrs or "posY" not in attrs:
        fail("条目缺少 posX/posY")
    return NEW_SETTLEMENT_ID, float(attrs["posX"]), float(attrs["posY"])


def extract_entity_block(text, entity_name):
    """提取 <game_entity name="X" ...> 的完整文本块（深度匹配 </game_entity>）。"""
    start_marker = f'<game_entity name="{entity_name}"'
    start = text.find(start_marker)
    if start < 0:
        return None
    depth = 1
    pos = start + len(start_marker)
    for m in re.finditer(r'<game_entity\b|</game_entity>', text[pos:]):
        if m.group(0) == "<game_entity":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                end = pos + m.end()
                return text[start:end]
    return None


def main():
    shokuho_dir = DEFAULT_SHOKUHO
    do_clean = False
    args = sys.argv[1:]
    while args:
        arg = args.pop(0)
        if arg == "--shokuho":
            shokuho_dir = args.pop(0)
        elif arg == "--clean":
            do_clean = True

    src_map = os.path.join(shokuho_dir, "SceneObj", "Main_map")
    if not os.path.isdir(src_map):
        fail(f"织丰地图目录不存在（{src_map}），用 --shokuho <路径> 指定织丰模块")

    # 0) 读数据源
    settle_text = read_text(SETTLEMENTS_XML)
    new_id, pos_x, pos_y = parse_new_settlement(settle_text)

    # 1) 拷贝织丰全套地图
    if do_clean and os.path.isdir(TARGET_DIR):
        shutil.rmtree(TARGET_DIR)
    os.makedirs(TARGET_DIR, exist_ok=True)
    shutil.copytree(src_map, TARGET_DIR, dirs_exist_ok=True)
    log(f"已拷贝织丰地图: {src_map} -> {TARGET_DIR}")

    # 2) 在 scene.xscene 克隆实体
    scene_path = os.path.join(TARGET_DIR, "scene.xscene")
    scene = read_text(scene_path)

    template_block = extract_entity_block(scene, "village_KIN5_1")
    if template_block is None:
        fail("找不到模板实体 village_KIN5_1（织丰场景结构变了？）")

    # 模板坐标 z（贴地高度）直接沿用，x/y 用 settlements.xml 的（避免手编多份）
    tmpl_transform = re.search(r'<transform position="([0-9.\-]+), ([0-9.\-]+), ([0-9.\-]+)"', template_block)
    if not tmpl_transform:
        fail("模板实体缺少 transform")
    z = tmpl_transform.group(3)

    new_block = template_block.replace(f'name="village_KIN5_1"', f'name="{new_id}"', 1)
    new_block = re.sub(r'<transform position="[^"]*"',
                       f'<transform position="{pos_x:.3f}, {pos_y:.3f}, {z}"', new_block, count=1)

    if f'name="{new_id}"' in scene:
        log(f"目标场景已有 {new_id}（重复运行时跳过插入，直接走校验）")
    else:
        # 插到模板块之后
        insert_at = scene.find("</game_entity>", scene.find(template_block)) + len("</game_entity>")
        scene = scene[:insert_at] + "\n" + new_block + scene[insert_at:]
        write_text(scene_path, scene)
        log(f"已插入实体 {new_id} @ ({pos_x:.3f}, {pos_y:.3f}, {z})")

    # 3) 校验
    errors = []
    if scene.count(f'name="{new_id}"') != 1:
        errors.append(f"{new_id} 实体计数异常: {scene.count(f'name=\"{new_id}\"')}")
    if scene.count('name="village_KIN5_1"') != 1:
        errors.append("template 实体计数异常")
    if scene.count("</game_entity>") != scene.count("<game_entity"):
        errors.append("scene.xscene game_entity 标签不配对（解析失败）")
    expected_transform = f'{pos_x:.3f}, {pos_y:.3f}, {z}'
    if expected_transform not in scene:
        errors.append(f"实体 transform 与 settlements.xml 不一致")

    for fn in ["scene.xscene", "terrain.bin", "flora.bin", "navmesh.bin", "atmosphere.xml", "references.txt"]:
        if not os.path.isfile(os.path.join(TARGET_DIR, fn)):
            errors.append(f"缺少 {fn}")
    if not os.path.isdir(os.path.join(TARGET_DIR, "ShaderCache")):
        errors.append("缺少 ShaderCache/")

    if errors:
        fail("校验未通过:\n" + "\n".join(errors))
    log("校验通过：实体唯一、坐标一致、地形文件齐全")


if __name__ == "__main__":
    main()
