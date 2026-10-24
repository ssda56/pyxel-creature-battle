
"""8 只精灵的**占位图**（方案 D 几何拼装）。

每只精灵两张图：
- `creature_{id}_battle` 32x32 战斗图
- `creature_{id}_icon`   16x16 地图图标（**独立简化画**，不是缩小版）

占位方案：属性主色块 + 色 5 描边 + 简单几何形，8 只彼此可辨。
批 4 会重画成正式像素画，届时只要改这里即可。

精灵 id 与《数值设定.md》§1.2 一致：
    1 小火狮 火 / 2 水滴滴 水 / 3 兔小子 草 / 4 小狮鹫 风
    5 独角兽 光 / 6 三头犬 暗 / 7 不死鸟 火 / 8 闪电小子 雷
"""

from __future__ import annotations

from src.assets_gen.sprite_base import Canvas, SpriteMatrix

#: 精灵共用调色板
PALETTE: dict[str, int] = {
    ".": None,   # 透明
    "K": 5,      # 深紫 描边（**不要用色 0 做描边**）
    "S": 6,      # 灰
    "N": 2,      # 深蓝（风）
    "g": 3,      # 深绿
    "G": 4,      # 中绿
    "W": 7,      # 白
    "R": 8,      # 红
    "O": 9,      # 橙（火）
    "Y": 10,     # 黄（雷）
    "L": 11,     # 浅绿（草）
    "B": 12,     # 浅蓝（水）
    "D": 13,     # 棕
    "P": 14,     # 粉（暗）
}


# --------------------------------------------------------------- 1 小火狮（火）
def _fire_lion_battle() -> Canvas:
    c = Canvas(32, 32)
    c.ellipse(16, 14, 9, 8, "Y")            # 鬃毛
    c.triangle((23, 20), (30, 13), (26, 23), "Y")  # 尾焰
    c.ellipse(16, 22, 8, 6, "O")            # 身体
    c.rect(9, 25, 3, 5, "O")                # 腿
    c.rect(13, 26, 3, 5, "O")
    c.rect(18, 26, 3, 5, "O")
    c.rect(21, 25, 3, 5, "O")
    c.ellipse(16, 14, 6, 5, "O")            # 头
    c.triangle((10, 9), (8, 4), (13, 8), "O")   # 耳
    c.triangle((22, 9), (24, 4), (19, 8), "O")
    c.triangle((16, 1), (12, 9), (20, 9), "Y")  # 头顶火焰
    c.triangle((16, 4), (14, 9), (18, 9), "R")
    c.pixel(13, 13, "K")
    c.pixel(19, 13, "K")
    c.pixel(15, 16, "R")
    c.pixel(17, 16, "R")
    return c


def _fire_lion_icon() -> Canvas:
    c = Canvas(16, 16)
    c.ellipse(8, 7, 5, 5, "Y")
    c.ellipse(8, 11, 4, 3, "O")
    c.ellipse(8, 7, 3, 3, "O")
    c.triangle((8, 1), (5, 5), (11, 5), "Y")
    c.pixel(6, 7, "K")
    c.pixel(10, 7, "K")
    return c


# --------------------------------------------------------------- 2 水滴滴（水）
def _water_drop_battle() -> Canvas:
    c = Canvas(32, 32)
    c.triangle((16, 1), (6, 20), (26, 20), "B")
    c.ellipse(16, 21, 10, 8, "B")
    c.ellipse(12, 17, 3, 2, "W")
    c.ellipse(16, 27, 6, 2, "B")
    c.pixel(12, 21, "K")
    c.pixel(20, 21, "K")
    c.pixel(15, 24, "W")
    c.pixel(17, 24, "W")
    return c


def _water_drop_icon() -> Canvas:
    c = Canvas(16, 16)
    c.triangle((8, 1), (3, 10), (13, 10), "B")
    c.ellipse(8, 11, 6, 5, "B")
    c.ellipse(6, 9, 2, 1, "W")
    c.pixel(6, 11, "K")
    c.pixel(10, 11, "K")
    return c


# --------------------------------------------------------------- 3 兔小子（草）
def _grass_rabbit_battle() -> Canvas:
    c = Canvas(32, 32)
    c.ellipse(11, 6, 2, 5, "L")
    c.ellipse(21, 6, 2, 5, "L")
    c.ellipse(11, 6, 1, 3, "P")
    c.ellipse(21, 6, 1, 3, "P")
    c.ellipse(16, 23, 6, 5, "L")
    c.ellipse(16, 15, 6, 5, "L")
    c.ellipse(23, 24, 2, 2, "W")
    c.ellipse(11, 27, 2, 2, "L")
    c.ellipse(21, 27, 2, 2, "L")
    c.pixel(13, 15, "K")
    c.pixel(19, 15, "K")
    c.pixel(16, 17, "P")
    return c


def _grass_rabbit_icon() -> Canvas:
    c = Canvas(16, 16)
    c.ellipse(5, 4, 1, 3, "L")
    c.ellipse(11, 4, 1, 3, "L")
    c.ellipse(8, 10, 5, 4, "L")
    c.ellipse(8, 9, 3, 3, "L")
    c.pixel(6, 9, "K")
    c.pixel(10, 9, "K")
    return c


# --------------------------------------------------------------- 4 小狮鹫（风）
def _wind_griffin_battle() -> Canvas:
    c = Canvas(32, 32)
    c.triangle((1, 7), (14, 13), (14, 23), "N")
    c.triangle((30, 7), (18, 13), (18, 23), "N")
    c.ellipse(16, 19, 6, 7, "N")
    c.triangle((16, 24), (11, 31), (21, 31), "N")
    c.ellipse(16, 10, 4, 4, "N")
    c.triangle((16, 1), (13, 7), (19, 7), "Y")
    c.triangle((16, 9), (19, 12), (13, 12), "Y")
    c.pixel(14, 9, "W")
    c.pixel(18, 9, "W")
    c.line(14, 26, 13, 30, "Y")
    c.line(18, 26, 19, 30, "Y")
    return c


def _wind_griffin_icon() -> Canvas:
    c = Canvas(16, 16)
    c.triangle((1, 4), (7, 7), (7, 12), "N")
    c.triangle((14, 4), (9, 7), (9, 12), "N")
    c.ellipse(8, 9, 3, 4, "N")
    c.ellipse(8, 4, 3, 3, "N")
    c.pixel(6, 4, "W")
    c.pixel(10, 4, "W")
    return c


# --------------------------------------------------------------- 5 独角兽（光）
def _light_unicorn_battle() -> Canvas:
    c = Canvas(32, 32)
    c.ellipse(16, 12, 8, 7, "P")
    c.triangle((24, 18), (31, 11), (28, 23), "P")
    c.ellipse(16, 21, 8, 6, "W")
    c.rect(10, 25, 2, 6, "W")
    c.rect(14, 26, 2, 5, "W")
    c.rect(18, 26, 2, 5, "W")
    c.rect(21, 25, 2, 6, "W")
    c.ellipse(16, 12, 5, 4, "W")
    c.triangle((16, 1), (13, 8), (19, 8), "Y")
    c.pixel(14, 12, "K")
    c.pixel(18, 12, "K")
    return c


def _light_unicorn_icon() -> Canvas:
    c = Canvas(16, 16)
    c.ellipse(8, 8, 5, 5, "P")
    c.ellipse(8, 11, 4, 3, "W")
    c.ellipse(8, 7, 3, 3, "W")
    c.triangle((8, 1), (6, 4), (10, 4), "Y")
    c.pixel(6, 7, "K")
    c.pixel(10, 7, "K")
    return c


# --------------------------------------------------------------- 6 三头犬（暗）
def _dark_cerberus_battle() -> Canvas:
    c = Canvas(32, 32)
    c.ellipse(16, 22, 10, 6, "P")
    c.rect(8, 26, 3, 5, "P")
    c.rect(12, 27, 3, 4, "P")
    c.rect(18, 27, 3, 4, "P")
    c.rect(22, 26, 3, 5, "P")
    for hx, hy in ((8, 13), (16, 10), (24, 13)):
        c.triangle((hx - 3, hy - 3), (hx - 5, hy - 8), (hx, hy - 5), "P")
        c.triangle((hx + 3, hy - 3), (hx + 5, hy - 8), (hx, hy - 5), "P")
        c.ellipse(hx, hy, 4, 4, "P")
        c.pixel(hx - 2, hy, "K")
        c.pixel(hx + 2, hy, "K")
    return c


def _dark_cerberus_icon() -> Canvas:
    c = Canvas(16, 16)
    c.ellipse(8, 11, 6, 4, "P")
    c.ellipse(4, 6, 2, 2, "P")
    c.ellipse(8, 4, 2, 2, "P")
    c.ellipse(12, 6, 2, 2, "P")
    c.pixel(3, 6, "K")
    c.pixel(5, 6, "K")
    c.pixel(7, 4, "K")
    c.pixel(9, 4, "K")
    c.pixel(11, 6, "K")
    c.pixel(13, 6, "K")
    return c


# --------------------------------------------------------------- 7 不死鸟（火）
def _phoenix_battle() -> Canvas:
    c = Canvas(32, 32)
    c.triangle((16, 21), (7, 31), (25, 31), "Y")
    c.triangle((16, 24), (12, 31), (20, 31), "R")
    c.triangle((11, 15), (1, 5), (4, 20), "Y")
    c.triangle((21, 15), (30, 5), (28, 20), "Y")
    c.triangle((11, 17), (5, 10), (8, 19), "R")
    c.triangle((21, 17), (27, 10), (24, 19), "R")
    c.ellipse(16, 18, 5, 7, "O")
    c.ellipse(16, 9, 4, 4, "O")
    c.triangle((16, 1), (12, 7), (20, 7), "Y")
    c.triangle((16, 3), (14, 7), (18, 7), "R")
    c.triangle((16, 9), (19, 12), (13, 12), "Y")
    c.pixel(14, 9, "K")
    c.pixel(18, 9, "K")
    return c


def _phoenix_icon() -> Canvas:
    c = Canvas(16, 16)
    c.triangle((8, 7), (0, 2), (3, 12), "Y")
    c.triangle((8, 7), (15, 2), (12, 12), "Y")
    c.ellipse(8, 9, 3, 5, "O")
    c.ellipse(8, 4, 3, 3, "O")
    c.triangle((8, 1), (6, 4), (10, 4), "Y")
    c.pixel(6, 4, "K")
    c.pixel(10, 4, "K")
    return c


# --------------------------------------------------------------- 8 闪电小子（雷）
def _thunder_kid_battle() -> Canvas:
    c = Canvas(32, 32)
    c.ellipse(16, 8, 5, 5, "D")
    c.ellipse(16, 10, 4, 4, "Y")
    c.rect(9, 16, 2, 7, "Y")
    c.rect(21, 16, 2, 7, "Y")
    c.ellipse(16, 20, 5, 6, "Y")
    c.triangle((16, 11), (11, 21), (15, 21), "W")
    c.triangle((15, 19), (12, 28), (19, 18), "W")
    c.rect(12, 25, 3, 6, "Y")
    c.rect(17, 25, 3, 6, "Y")
    c.pixel(14, 10, "K")
    c.pixel(18, 10, "K")
    return c


def _thunder_kid_icon() -> Canvas:
    c = Canvas(16, 16)
    c.ellipse(8, 5, 4, 4, "D")
    c.ellipse(8, 6, 3, 3, "Y")
    c.ellipse(8, 11, 4, 4, "Y")
    c.triangle((8, 7), (6, 12), (9, 12), "W")
    c.pixel(6, 6, "K")
    c.pixel(10, 6, "K")
    return c


#: 精灵 id -> (战斗图画布工厂, 图标画布工厂)
_CREATURES = [
    (1, "小火狮", "火", _fire_lion_battle, _fire_lion_icon),
    (2, "水滴滴", "水", _water_drop_battle, _water_drop_icon),
    (3, "兔小子", "草", _grass_rabbit_battle, _grass_rabbit_icon),
    (4, "小狮鹫", "风", _wind_griffin_battle, _wind_griffin_icon),
    (5, "独角兽", "光", _light_unicorn_battle, _light_unicorn_icon),
    (6, "三头犬", "暗", _dark_cerberus_battle, _dark_cerberus_icon),
    (7, "不死鸟", "火", _phoenix_battle, _phoenix_icon),
    (8, "闪电小子", "雷", _thunder_kid_battle, _thunder_kid_icon),
]


def _build(factory) -> SpriteMatrix:
    """把画布画成 SpriteMatrix（自动加色 5 描边）。"""
    canvas = factory()
    canvas.outline("K")
    return canvas.rows()


#: 精灵 id -> 战斗图 SpriteMatrix
CREATURE_BATTLE: dict[int, SpriteMatrix] = {}
#: 精灵 id -> 图标 SpriteMatrix
CREATURE_ICON: dict[int, SpriteMatrix] = {}
#: 精灵 id -> (名称, 属性)
CREATURE_INFO: dict[int, tuple[str, str]] = {}

SPRITES: list[SpriteMatrix] = []

for _sid, _name, _type, _battle, _icon in _CREATURES:
    _battle_sprite = SpriteMatrix(f"creature_{_sid}_battle", _build(_battle), PALETTE)
    _icon_sprite = SpriteMatrix(f"creature_{_sid}_icon", _build(_icon), PALETTE)
    CREATURE_BATTLE[_sid] = _battle_sprite
    CREATURE_ICON[_sid] = _icon_sprite
    CREATURE_INFO[_sid] = (_name, _type)
    SPRITES.append(_battle_sprite)
    SPRITES.append(_icon_sprite)
