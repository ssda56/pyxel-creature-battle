"""地图图块集：10 种 16x16 图块。

key 与《数值设定.md》§10.2 的图块 ID 一一对应：

    tile_0_grass     草地   可走
    tile_1_tallgrass 草丛   可走（明雷遇敌区）
    tile_2_tree      树     障碍
    tile_3_water     水     障碍
    tile_4_road      道路   可走（村庄地面）
    tile_5_wall      房屋墙 障碍
    tile_6_door      门/洞口 可走（传送点）
    tile_7_rock      岩壁   障碍
    tile_8_highland  高地   可走
    tile_9_flower    花丛   可走（装饰）

本批是**占位图**，但要求一眼能分辨（批 4 会重画）。
"""

from __future__ import annotations

from src.assets_gen.sprite_base import SpriteMatrix

#: 图块共用调色板（字符 -> 调色板索引）
PALETTE: dict[str, int] = {
    ".": None,   # 透明
    "K": 5,      # 深紫 描边
    "G": 4,      # 中绿 草地
    "g": 3,      # 深绿 草丛 / 树冠暗部
    "s": 4,      # 中绿 树冠主体
    "l": 11,     # 浅绿 高光
    "B": 12,     # 浅蓝 水
    "b": 2,      # 深蓝 门洞
    "Y": 10,     # 黄
    "O": 9,      # 橙 道路 / 屋顶
    "D": 13,     # 棕 树干 / 墙 / 岩壁暗部
    "d": 6,      # 灰 岩壁主体
    "L": 15,     # 浅灰 高光
    "W": 7,      # 白 泡沫 / 花瓣
    "R": 8,      # 红 花
    "P": 14,     # 粉 花
}

TILE_0_GRASS = SpriteMatrix(
    "tile_0_grass",
    [
        "lGGgGGGGlGGGGGGg",
        "GGGGgGGGlGGGGGGG",
        "gGGlGGGGGGGlGGGG",
        "GGGGGGGgGGGlGGGG",
        "GGgGGGlGGGGGGGGG",
        "GGGGGGGGgGGGlGGG",
        "lGGGGGGGlGGgGGGG",
        "GGgGGGgGGGGGGGGG",
        "GGGgGGGGGGgGGlGG",
        "GGGGGGgGGGGGGGGG",
        "gGGlGGGGGGGlGGGG",
        "GGGGGGGgGGGlGGGG",
        "GGgGGGlGGGGGGGGG",
        "GGGGGGGGgGGGlGGG",
        "lGGGGGGGlGGgGGGG",
        "GGgGGGgGGGGGGGGG",
    ],
    PALETTE,
)

TILE_1_TALLGRASS = SpriteMatrix(
    "tile_1_tallgrass",
    [
        "gGlgggglGGgggggg",
        "gGlgggglGGgggggg",
        "gGlgggglGGgggggg",
        "gglgggggGGgggggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "ggGlgggggggGgggg",
        "ggGlgggggggGgggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "gGgggggGlggggggg",
        "gGgggggGlggggggg",
        "gggggggggggggggg",
        "gggggggggggggggg",
        "gGlgggglGGgggggg",
        "gGlgggglGGgggggg",
    ],
    PALETTE,
)

TILE_2_TREE = SpriteMatrix(
    "tile_2_tree",
    [
        ".....gggggg.....",
        "...gGllGGGGGg...",
        "..gGGssssggGGg..",
        ".gGGssssssssGGg.",
        ".gGsssssssssgGg.",
        "gGGsssssssssGGg.",
        "gGsssssssssssGg.",
        "gGsssssssssssGg.",
        "gGsssssssssssGg.",
        "gGGsssssssssGGg.",
        ".gGGssssssssGGg.",
        "..gGGggggggGGg..",
        "...gGGGGGGGGg...",
        "......DD........",
        "......DD........",
        "......DD........",
    ],
    PALETTE,
)

TILE_3_WATER = SpriteMatrix(
    "tile_3_water",
    [
        "BBBBBBBBBBBBBBBB",
        "BBWWBBBBBBWWBBBB",
        "BBBBBBBBBBBBBBBB",
        "WWBBBBBBWWBBBBBB",
        "BBBBBBBBBBBBBBBB",
        "BBBBWWBBBBBBWWBB",
        "BBBBBBBBBBBBBBBB",
        "BBWWBBBBBBWWBBBB",
        "BBBBBBBBBBBBBBBB",
        "WWBBBBBBWWBBBBBB",
        "BBBBBBBBBBBBBBBB",
        "BBBBWWBBBBBBWWBB",
        "BBBBBBBBBBBBBBBB",
        "BBWWBBBBBBWWBBBB",
        "BBBBBBBBBBBBBBBB",
        "WWBBBBBBWWBBBBBB",
    ],
    PALETTE,
)

TILE_4_ROAD = SpriteMatrix(
    "tile_4_road",
    [
        "OOOOOOOOOOOOOOOO",
        "OOOOOOOOOOOOOOOO",
        "OODOOOOOOOOOOdOO",
        "OOOOOOOOOOOOOOOO",
        "OOOOOOOOOOOOOOOO",
        "dOOOOOOOOOOOOdOO",
        "OOOOOOOOOOOOOOOO",
        "OOOOOOOOOOOOOOOO",
        "OODOOOOOOOOOOdOO",
        "OOOOOOOOOOOOOOOO",
        "OOOOOOOOOOOOOOOO",
        "dOOOOOOOOOOOOdOO",
        "OOOOOOOOOOOOOOOO",
        "OOOOOOOOOOOOOOOO",
        "OODOOOOOOOOOOdOO",
        "OOOOOOOOOOOOOOOO",
    ],
    PALETTE,
)

TILE_5_WALL = SpriteMatrix(
    "tile_5_wall",
    [
        "OOOOOOOOOOOOOOOO",
        "OOOOOOOOOOOOOOOO",
        "DDDDDDDDDDDDDDDD",
        "DDDDDDDDDDDDDDDD",
        "dddddddddddddddd",
        "DDdDDDDDDDDDDDdD",
        "DDdDDDDDDDDDDDdD",
        "DDdDDDDDDDDDDDdD",
        "dddddddddddddddd",
        "DDDDdDDDDDDDDDDd",
        "DDDDdDDDDDDDDDDd",
        "DDDDdDDDDDDDDDDd",
        "dddddddddddddddd",
        "DDDDDDDDDDDDDDDD",
        "DDDDDDDDDDDDDDDD",
        "dddddddddddddddd",
    ],
    PALETTE,
)

TILE_6_DOOR = SpriteMatrix(
    "tile_6_door",
    [
        "..DDDDDDDDDDDD..",
        "..DDDDDDDDDDDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDbbbbbbbbDD..",
        "..DDDDDDDDDDDD..",
        "..DDDDDDDDDDDD..",
    ],
    PALETTE,
)

TILE_7_ROCK = SpriteMatrix(
    "tile_7_rock",
    [
        "dddddddddddddddd",
        "dDDdddddddddddDd",
        "dDDDDdddddDDdDdD",
        "ddddddddddddddDd",
        "dDdDDDdddddDDdDd",
        "dDdDDDdddddDDdDd",
        "dddddddddddddddD",
        "dddddddddddddddD",
        "dDDdddDDDddddddd",
        "dDDdddDDDddddddd",
        "dddddddddddddddd",
        "dDdDDdddDDDddDdD",
        "dDdDDdddDDDddDdD",
        "ddddddddddddddDd",
        "dDDdddDDdddddDDd",
        "dddddddddddddddd",
    ],
    PALETTE,
)

TILE_8_HIGHLAND = SpriteMatrix(
    "tile_8_highland",
    [
        "DDDDDDDDDDDDDDDD",
        "DDDDDDDDDDDDDDDD",
        "DDDDDDDDDDDDDDDD",
        "DDDDDDDDDDDDDDDD",
        "lDDGGDDDDDDGGDDl",
        "lDDGGDDDDDDGGDDl",
        "DDDDDDDDDDDDDDDD",
        "DDdDDDDDDDDDDdDD",
        "DDDDDDDDDDDDDDDD",
        "DDdDDDDDDDDDDdDD",
        "DDDDDDDDDDDDDDDD",
        "DDDDDDDDDDDDDDDD",
        "DDDDDDddDDDDDDdD",
        "DDDDDDDDDDDDDDDD",
        "DDDDDDDDDDDDDDDD",
        "DDDDDDDDDDDDDDDD",
    ],
    PALETTE,
)

TILE_9_FLOWER = SpriteMatrix(
    "tile_9_flower",
    [
        "GGGGgGGGGGGGGGGG",
        "GGGGGGGGGGGGgGGG",
        "GGGGGGGGGGGPPPGG",
        "GRRRGGGGGGGPYPGG",
        "GRYRGGGGGGGPPPGG",
        "GRRRGGGGGGGGgGGG",
        "GGgGGGGGGGGGGGGG",
        "GGGGGGWWWGGGGGGG",
        "GGGGGGWYWGGGGGGG",
        "GGGGGGWWWGGGGGGG",
        "GGGGGGGgGGGGGGGG",
        "GGGGgGGGGGGGGGGG",
        "GGGGGGGGGGGGgGGG",
        "GGgGGGGGGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "gGGGGGGGGGGGGGGG",
    ],
    PALETTE,
)

#: 全部图块（烘焙顺序 = 绘制顺序）
SPRITES: list[SpriteMatrix] = [
    TILE_0_GRASS,
    TILE_1_TALLGRASS,
    TILE_2_TREE,
    TILE_3_WATER,
    TILE_4_ROAD,
    TILE_5_WALL,
    TILE_6_DOOR,
    TILE_7_ROCK,
    TILE_8_HIGHLAND,
    TILE_9_FLOWER,
]

#: 图块 ID（§10.2）-> SpriteMatrix
TILES_BY_ID: dict[int, SpriteMatrix] = {i: sprite for i, sprite in enumerate(SPRITES)}
