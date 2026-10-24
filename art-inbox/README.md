# 生图投放目录

把外部生图模型产出的 PNG 放到这里，文件名严格照 `docs/美术生图提示词.md` §4/§5 的表：

- 精灵战斗图：`creature_1_battle.png` … `creature_8_battle.png`（512×512）
- 精灵地图图标：`creature_1_icon.png` … `creature_8_icon.png`（256×256）

**建议先只放 `creature_1_battle.png` 一张**，确认转换效果与风格后再批量出其余。

转换由 `tools/art_import.py` 完成（需系统 Python，带 Pillow）：

    C:\Users\1\AppData\Local\Programs\Python\Python312\python.exe tools\art_import.py art-inbox\creature_1_battle.png

输出：
- `art-inbox/_converted/<name>.txt` —— 字符画矩阵（直接可粘进 src/assets_gen/sprites/）
- `art-inbox/_converted/<name>_preview.png` —— 8 倍放大预览，肉眼验收用
- 终端打印：颜色数、检测到的块尺寸、量化平均误差、是否通过 §8 验收
