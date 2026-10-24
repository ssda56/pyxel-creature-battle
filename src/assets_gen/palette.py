"""全局唯一配色来源（规划文档 §9.4）。

本模块是**全项目唯一的调色板定义处**：任何地方都不允许再写裸色号。
所有语义常量（BLACK / ORANGE / YELLOW ...）都是 0~15 的调色板索引。

关于索引的说明
----------------
Pyxel 2.9.9 的 `pyxel.init()` 不接受 palette 参数（内置 16 色写死在扩展里），
因此本项目在 `pyxel.init()` **之后**用 `pyxel.colors[:] = PALETTE_RGB`
把默认调色板整体换成本项目的语义调色板（见 `apply()`）。

索引与语义色的对应关系沿用《数值设定.md》§13 的 UI 规格：
    8  = 红   HP 条底色
    11 = 绿   HP 条渐变
    12 = 浅蓝 MP 条
    1  = 深底 MP 条深底 / 标题背景
    10 = 黄   光标 / 高亮
    5  = 深紫 **精灵描边专用色**
    7  = 白   文字 / 高光

重要约束
---------
1. 索引 0 同时是 `pyxel.blt(colkey=0)` 的透明键，**精灵图里不能出现色 0**
   （否则整块变透明），描边一律用色 5。
2. 色 5 保留给描边，所以"暗"属性的主色改用 14（粉），避免描边与主体同色而消失。
"""

from __future__ import annotations

import pyxel

# ---------------------------------------------------------------- 语义色常量
BLACK = 0        # 纯黑：UI 文字；精灵禁用（透明键）
DEEP_BLUE = 1    # 深蓝：标题画面底色、MP 条深底、夜景
BLUE = 2         # 蓝：风属性主色、水面暗部
DARK_GREEN = 3   # 深绿：草丛、树冠暗部
GREEN = 4        # 中绿：草地地面
DARK_PURPLE = 5  # 深紫：**精灵描边专用色**，不可用作属性主色
GRAY = 6         # 灰：岩壁、不可用选项
WHITE = 7        # 纯白：正文、高光、敌方信息框底
RED = 8          # 红：HP 条底、危险提示
ORANGE = 9       # 橙：火属性主色、道路 / 屋顶
YELLOW = 10      # 黄：雷属性主色、标题、UI 高亮、光标
LIGHT_GREEN = 11 # 浅绿：草属性主色、HP 条渐变
LIGHT_BLUE = 12  # 浅蓝：水属性主色、MP 条
BROWN = 13       # 棕：树干、房屋墙、岩壁暗部
PINK = 14        # 粉：暗属性主色
LIGHT_GRAY = 15  # 浅灰：对话框底、UI 边框

#: 16 色的 24bit RGB 值，顺序与上面的索引一一对应
PALETTE_RGB: tuple[int, ...] = (
    0x0B0B12,  # 0  BLACK
    0x16213E,  # 1  DEEP_BLUE
    0x3E7BD6,  # 2  BLUE
    0x1F6B2E,  # 3  DARK_GREEN
    0x4FA845,  # 4  GREEN
    0x5B3A8E,  # 5  DARK_PURPLE
    0x8A8A96,  # 6  GRAY
    0xFFFFFF,  # 7  WHITE
    0xD84848,  # 8  RED
    0xE07B39,  # 9  ORANGE
    0xF5E050,  # 10 YELLOW
    0x9BD45B,  # 11 LIGHT_GREEN
    0x5AC8E8,  # 12 LIGHT_BLUE
    0x8A5A3C,  # 13 BROWN
    0xF2789A,  # 14 PINK
    0xD8D8E0,  # 15 LIGHT_GRAY
)

#: 索引 -> 语义名（调试 / 截图标注用）
COLOR_NAMES: dict[int, str] = {
    BLACK: "BLACK",
    DEEP_BLUE: "DEEP_BLUE",
    BLUE: "BLUE",
    DARK_GREEN: "DARK_GREEN",
    GREEN: "GREEN",
    DARK_PURPLE: "DARK_PURPLE",
    GRAY: "GRAY",
    WHITE: "WHITE",
    RED: "RED",
    ORANGE: "ORANGE",
    YELLOW: "YELLOW",
    LIGHT_GREEN: "LIGHT_GREEN",
    LIGHT_BLUE: "LIGHT_BLUE",
    BROWN: "BROWN",
    PINK: "PINK",
    LIGHT_GRAY: "LIGHT_GRAY",
}

#: 属性 -> 主色。属性名与《数值设定.md》§1.2 / §2 完全一致。
#: "无" 是内部属性（通用招式），克制系数恒为 1.0。
TYPE_COLORS: dict[str, int] = {
    "火": ORANGE,
    "水": LIGHT_BLUE,
    "草": LIGHT_GREEN,
    "风": BLUE,
    "光": WHITE,
    "暗": PINK,
    "雷": YELLOW,
    "无": GRAY,
}

#: ELEMENT_COLORS 是 TYPE_COLORS 的别名，便于按"元素"叫法引用
ELEMENT_COLORS = TYPE_COLORS


def apply() -> None:
    """把本调色板写入 Pyxel。必须在 `pyxel.init()` 之后调用。"""
    pyxel.colors[:] = PALETTE_RGB


def color_of(type_name: str) -> int:
    """按属性名取主色；未知属性回退到 GRAY。"""
    return TYPE_COLORS.get(type_name, GRAY)
