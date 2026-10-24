"""主角行走图：4 方向 x 2 帧 = 8 张 16x16（批 4 重绘 · 方案 D）。

key 命名：`player_{方向}_{帧号}`，方向为 down / up / left / right。
帧 0 = 站立（两腿并拢），帧 1 = 迈步（两腿大幅分开、中间露出背景）。
field_scene 每 20 帧切一次帧，所以两帧的姿态差异必须够大：
本版四方向的站立/迈步差异分别是 34 / 34 / 27 / 27 个像素（共 256），
而旧版只有 12 个像素，走起来像原地踏步。

画法
----
逐帧手绘字面量字符画（运行期零解析开销）。旧版是"头 8 行 + 8 帧共用
一个 6 行身体 + 2 行腿"拼装，8 张图几乎一模一样，本版改成逐帧独立绘制。

四方向怎么一眼分清
------------------
- `down`：正面。帽檐（色 13 深棕横带）下方是整张脸，
  两只 2x2 的深蓝眼睛分列左右，中间留 2 像素鼻梁。
- `up`：背面。帽檐下面直接接**帽子的后半圈**（整片色 9），
  没有脸、没有眼睛；上半身是背在身后的**棕色小背包**（色 13 + 色 9 肩带）。
- `left` / `right`：侧身。只有**一只** 2x1 的眼睛，并且画在
  **朝向那一侧**（朝左时在左，朝右时在右，左右两帧互为镜像）；
  背包画在**背侧**（朝左时在右，朝右时在左），与正面的背包呼应。

配色约定（见 palette.py）
-------------------------
- `'.'` 恒为透明；**色 0 绝不能出现在画面里**（它是 blt 的透明键，会整块消失）。
- 描边统一 **色 5**，沿整个剪影走一圈（1 像素）。
- 帽檐 / 背包 / 鞋统一用**色 13 深棕**，而不是浅灰：旧版帽檐用的浅灰
  和脸（肤色）同色，两者糊成一团，看上去就是"一个白团"，本版据此修正。
- 瞳孔用**色 1 深蓝**，不用色 5：色 5 是描边色，当瞳孔会变成空心方块，
  眼神全丢（T7a 的精灵也是同样的处理）。
- 四个方向同色系：帽 9 / 帽檐·背包·鞋 13 / 脸与手 15 / 上衣 2 /
  裤子与瞳孔 1 / 描边 5。
"""

from __future__ import annotations

from src.assets_gen.sprite_base import SpriteMatrix

#: 主角共用调色板（**不声明索引 0**：色 0 是透明键）
PALETTE: dict[str, int] = {
    ".": None,   # 透明（不写像素）
    "K": 5,      # 深紫 DARK_PURPLE：描边
    "O": 9,      # 橙 ORANGE：帽子主体
    "D": 13,     # 棕 BROWN：帽檐 / 背包 / 鞋
    "G": 9,      # 橙 ORANGE：背包肩带
    "S": 15,     # 浅灰 LIGHT_GRAY：皮肤（脸与手）
    "E": 1,      # 深蓝 DEEP_BLUE：瞳孔
    "C": 2,      # 蓝 BLUE：上衣
    "P": 1,      # 深蓝 DEEP_BLUE：裤子
}

# ======================================================================
# 正面朝下（down）
# 行 0 留空 / 1~5 帽子与帽檐 / 6~8 脸（眼睛在第 7 行）/ 9~11 上衣
# 12~13 裤子 / 14 腿 / 15 鞋
# ======================================================================
PLAYER_DOWN_0 = SpriteMatrix(
    "player_down_0",
    [
        "................",
        ".....KKKKKK.....",
        "....KOOOOOOK....",
        "...KOOOOOOOOK...",
        "...KOOOOOOOOK...",
        "..KDDDDDDDDDDK..",
        "...KSSSSSSSSK...",
        "...KSEESSEESK...",
        "...KSSSSSSSSK...",
        "..KSSCCCCCCSSK..",
        "..KSCCCCCCCCSK..",
        "...KCCCCCCCCK...",
        "...KPPPPPPPPK...",
        "...KPPPPPPPPK...",
        "...KPPKKKKPPK...",
        "...KDDKKKKDDK...",
    ],
    PALETTE,
)

PLAYER_DOWN_1 = SpriteMatrix(
    "player_down_1",
    [
        "................",
        ".....KKKKKK.....",
        "....KOOOOOOK....",
        "...KOOOOOOOOK...",
        "...KOOOOOOOOK...",
        "..KDDDDDDDDDDK..",
        "...KSSSSSSSSK...",
        "...KSEESSEESK...",
        "...KSSSSSSSSK...",
        "..KSSCCCCCCSSK..",
        "..KSCCCCCCCCSK..",
        "...KCCCCCCCCK...",
        "...KPPPPPPPPK...",
        "..KPPKKKKKKPPK..",
        ".KPPPK....KPPPK.",
        ".KDDDK....KDDDK.",
    ],
    PALETTE,
)

# ======================================================================
# 背面朝上（up）—— 帽子后半圈 + 背包，**没有任何脸部元素**
# ======================================================================
PLAYER_UP_0 = SpriteMatrix(
    "player_up_0",
    [
        "................",
        ".....KKKKKK.....",
        "....KOOOOOOK....",
        "...KOOOOOOOOK...",
        "...KOOOOOOOOK...",
        "..KDDDDDDDDDDK..",
        "...KOOOOOOOOK...",
        "...KOOOOOOOOK...",
        "...KOOOOOOOOK...",
        "..KSSDDDDDDSSK..",
        "..KSSGGGGGGSSK..",
        "..KSSDDDDDDSSK..",
        "...KPPPPPPPPK...",
        "...KPPPPPPPPK...",
        "...KPPKKKKPPK...",
        "...KDDKKKKDDK...",
    ],
    PALETTE,
)

PLAYER_UP_1 = SpriteMatrix(
    "player_up_1",
    [
        "................",
        ".....KKKKKK.....",
        "....KOOOOOOK....",
        "...KOOOOOOOOK...",
        "...KOOOOOOOOK...",
        "..KDDDDDDDDDDK..",
        "...KOOOOOOOOK...",
        "...KOOOOOOOOK...",
        "...KOOOOOOOOK...",
        "..KSSDDDDDDSSK..",
        "..KSSGGGGGGSSK..",
        "..KSSDDDDDDSSK..",
        "...KPPPPPPPPK...",
        "..KPPKKKKKKPPK..",
        ".KPPPK....KPPPK.",
        ".KDDDK....KDDDK.",
    ],
    PALETTE,
)

# ======================================================================
# 侧身朝左（left）—— 脸/眼睛/帽檐朝左，背包挂在**右侧**（背侧）
# ======================================================================
PLAYER_LEFT_0 = SpriteMatrix(
    "player_left_0",
    [
        "................",
        ".....KKKKK......",
        "....KOOOOOK.....",
        "...KOOOOOOOK....",
        "...KOOOOOOOK....",
        ".KDDDDDDDDDDK...",
        "...KSSSSSSK.....",
        "...KEESSSSK.....",
        "...KSSSSSSK.....",
        "..KSSCCCCCKDDK..",
        "..KSCCCCCCKDDK..",
        "..KCCCCCCCKDDK..",
        "..KPPPPPPPK.....",
        "..KPPPPPPPK.....",
        "..KPPKKKPPK.....",
        "..KDDKKKDDK.....",
    ],
    PALETTE,
)

PLAYER_LEFT_1 = SpriteMatrix(
    "player_left_1",
    [
        "................",
        ".....KKKKK......",
        "....KOOOOOK.....",
        "...KOOOOOOOK....",
        "...KOOOOOOOK....",
        ".KDDDDDDDDDDK...",
        "...KSSSSSSK.....",
        "...KEESSSSK.....",
        "...KSSSSSSK.....",
        "..KSSCCCCCKDDK..",
        "..KSCCCCCCKDDK..",
        "..KCCCCCCCKDDK..",
        "..KPPPPPPPK.....",
        ".KPPKKKKKPPK....",
        ".KPPP...KPPPK...",
        ".KDDD...KDDDK...",
    ],
    PALETTE,
)

# ======================================================================
# 侧身朝右（right）—— 左向帧的镜像：眼睛朝右，背包在左
# ======================================================================
PLAYER_RIGHT_0 = SpriteMatrix(
    "player_right_0",
    [
        "................",
        "......KKKKK.....",
        ".....KOOOOOK....",
        "....KOOOOOOOK...",
        "....KOOOOOOOK...",
        "...KDDDDDDDDDDK.",
        ".....KSSSSSSK...",
        ".....KSSSSEEK...",
        ".....KSSSSSSK...",
        "..KDDKCCCCCSSK..",
        "..KDDKCCCCCCSK..",
        "..KDDKCCCCCCCK..",
        ".....KPPPPPPPK..",
        ".....KPPPPPPPK..",
        ".....KPPKKKPPK..",
        ".....KDDKKKDDK..",
    ],
    PALETTE,
)

PLAYER_RIGHT_1 = SpriteMatrix(
    "player_right_1",
    [
        "................",
        "......KKKKK.....",
        ".....KOOOOOK....",
        "....KOOOOOOOK...",
        "....KOOOOOOOK...",
        "...KDDDDDDDDDDK.",
        ".....KSSSSSSK...",
        ".....KSSSSEEK...",
        ".....KSSSSSSK...",
        "..KDDKCCCCCSSK..",
        "..KDDKCCCCCCSK..",
        "..KDDKCCCCCCCK..",
        ".....KPPPPPPPK..",
        "....KPPKKKKKPPK.",
        "...KPPPK...PPPK.",
        "...KDDDK...DDDK.",
    ],
    PALETTE,
)

#: 全部主角帧（烘焙顺序）
SPRITES: list[SpriteMatrix] = [
    PLAYER_DOWN_0,
    PLAYER_DOWN_1,
    PLAYER_UP_0,
    PLAYER_UP_1,
    PLAYER_LEFT_0,
    PLAYER_LEFT_1,
    PLAYER_RIGHT_0,
    PLAYER_RIGHT_1,
]

#: (方向, 帧号) -> SpriteMatrix
PLAYER_FRAMES: dict[tuple[str, int], SpriteMatrix] = {
    ("down", 0): PLAYER_DOWN_0,
    ("down", 1): PLAYER_DOWN_1,
    ("up", 0): PLAYER_UP_0,
    ("up", 1): PLAYER_UP_1,
    ("left", 0): PLAYER_LEFT_0,
    ("left", 1): PLAYER_LEFT_1,
    ("right", 0): PLAYER_RIGHT_0,
    ("right", 1): PLAYER_RIGHT_1,
}
