"""地形细节：图块变体碎屑 + 边缘自动拼接（A6）。

本模块只做两件事，都是**纯函数**（同一输入永远同一输出，不碰 random / 时间）：

1. variant_index —— 按格坐标哈希给「可走地面」挑一个变体。
2. edge_signature / edge_family —— 判断这一格是不是某种地形的边缘，
   以及缺哪几条边，绘制时据此挑一张预先烘焙好的过渡图块。
3. blit_rect / blit_source —— 全屏绘制用的矩形裁剪（纯数学，可单测）。

为什么哈希而不是 random
-----------------------
项目有几十张截图当视觉回归证据。哈希 (gx, gy) 保证同一格永远同一种碎屑，
两次运行、两台机器画出来的地图完全一致；random 会让截图每次都不一样。

为什么边缘过渡不用调色板色 0
---------------------------
色 0（#0b0b12）是 pyxel.blt(colkey=0) 的透明键。如果把过渡图块的「被啃掉」
部分留成色 0，blt 时会直接透出屏幕底色（黑），而不是下面的地形。
所以每个过渡图块都用**被覆盖地形的颜色**把整块填满，再在上面画过渡形态。
"""

from __future__ import annotations

import zlib

#: 图块边长（像素）。与 map_data.TILE_SIZE 一致，这里不 import 数据层，
#: 让本模块保持「零依赖、可单独单测」。
TILE = 16

# ======================================================================
# 一、地面变体（只是碎屑，不影响可通行性）
# ======================================================================
#: 每种图块的变体数量（变体 0 就是原图块本身）
#: 注意：**洞窟地面（11）与岩壁（7）刻意没有变体**。
#: 这是用户在实拍之后明确要求回退的（洞窟保持原样的"干净石头"观感），
#: 不是漏做。tests/test_terrain_detail.py 里有反向断言钉住这一点，
#: 谁再给洞窟加碎屑会立刻被测试拦住。
VARIANT_COUNT: dict[int, int] = {
    0: 4,   # 草地：草叶 / 小花 / 石子 / 纯草
    4: 4,   # 道路（土）：石子 / 车辙痕 / 沙粒 / 纯土
    3: 4,   # 水面：浪花条纹 16 像素一循环，错位后波纹不再排成斜线
}

#: 哪些图块属于「可走地面」
GROUND_TILES: frozenset[int] = frozenset({0, 4})

#: 做边缘自动拼接的地形族。
#: key 是族名，value 是族内所有图块 ID —— 族内相邻不画过渡（草地挨着花丛
#: 仍然是草地，不该出现土边），只有**跨族**交界才画。
#: 洞窟地面（11）**不在**这里：洞窟不做边缘拼接（用户明确不要）。
EDGE_FAMILIES: dict[str, tuple[int, ...]] = {
    "grass": (0, 1, 9),   # 草地 / 草丛 / 花丛
    "soil": (4,),         # 道路（土黄）
}

#: 图块 ID -> 族名（反查表）
_TILE_FAMILY: dict[int, str] = {
    t: fam for fam, tiles in EDGE_FAMILIES.items() for t in tiles
}

#: 每个地形族对**哪些邻格图块**画过渡带（显式白名单）。
#:
#: 这是最关键的取舍，两条经验都是看截图改出来的：
#:
#: 1. **只对别的「地面」画带，不对障碍画。** 一开始的写法是「邻居只要不
#:    同族就画」，结果每栋房子、每片树林四周都多出一圈深绿描边，整张图
#:    像"每格都加了框"——正是最容易翻车的棋盘感。
#: 2. **交界带只画在一侧。** 草地对道路如果两边都画，中间会出现一条
#:    两倍宽的深色线；现在统一让「后铺上去的地形」负责画边
#:    （路压草 = 路画边），视觉上就像一条有明确边缘的小径。
EDGE_TRIGGERS: dict[str, frozenset[int]] = {
    "grass": frozenset({3}),            # 草地只在**水**边压湿边
    "soil": frozenset({0, 1, 3, 9}),    # 道路压草地族与水
}


def triggers_for(tile_id: int) -> frozenset[int]:
    """该图块触发过渡的邻格图块集合（空集合 = 不画过渡）。"""
    fam = _TILE_FAMILY.get(tile_id)
    if fam is None:
        return frozenset()
    return EDGE_TRIGGERS[fam]


def variant_count(tile_id: int) -> int:
    """该图块有几个变体（没有碎屑的返回 1）。"""
    return VARIANT_COUNT.get(tile_id, 1)


def has_variants(tile_id: int) -> bool:
    """该图块有没有碎屑变体。"""
    return VARIANT_COUNT.get(tile_id, 1) > 1


def variant_index(gx: int, gy: int, tile_id: int, count: int) -> int:
    """按格坐标哈希给 (gx, gy) 选一个变体下标，范围 0..count-1。

    哈希用 zlib.crc32：对整数坐标是纯函数、跨进程稳定
    （Python 内置 hash() 受 PYTHONHASHSEED 影响，跨进程不稳定，不能用）。
    """
    if count <= 1:
        return 0
    mixed = ((gx & 0xFFFF) << 16) ^ (gy & 0xFFFF) ^ ((tile_id + 1) * 0x9E3779B1)
    return zlib.crc32(mixed.to_bytes(8, "little", signed=False)) % count


# ======================================================================
# 二、边缘自动拼接（四邻接，9 种形态）
# ======================================================================
#: 单边形态：上 / 右 / 下 / 左
EDGE_TOP = 1
EDGE_RIGHT = 2
EDGE_BOTTOM = 3
EDGE_LEFT = 4
#: 两邻边同时缺时的角形态
EDGE_TOP_LEFT = 5
EDGE_TOP_RIGHT = 6
EDGE_BOTTOM_LEFT = 7
EDGE_BOTTOM_RIGHT = 8
#: 相对的边同时缺（一格宽的窄道），以及三面以上都缺（孤立小地块）：
#: 四周压一圈边。
EDGE_RING = 9

#: 形态总数（含「无过渡」的第 0 种）
EDGE_SHAPES = 10

#: 方向下标 -> (dx, dy)：0 上 / 1 右 / 2 下 / 3 左
_NEIGHBORS: tuple[tuple[int, int], ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))


def edge_family(tile_id: int) -> str | None:
    """该图块属于哪个地形族；不做过渡的图块返回 None。"""
    return _TILE_FAMILY.get(tile_id)


def is_edge_material(tile_id: int) -> bool:
    """该图块是不是「可以当边缘内侧」的地面族成员。"""
    return tile_id in _TILE_FAMILY


def edge_signature(tile_id: int, gx: int, gy: int, tile_at) -> int:
    """判断这一格要画哪种边缘过渡，返回 0..EDGE_SHAPES-1 的形态号。

    :param tile_id: 当前格的图块 ID
    :param gx, gy: 当前格格坐标
    :param tile_at: (gx, gy) -> int | None，取邻格图块的回调（越界返回 None）

    规则：

    - 当前格不触发过渡 -> 0（不画过渡）
    - 邻居**在触发白名单里**（水 / 另一族地面 / 岩壁）-> 该侧缺边
    - 只有一侧缺边 -> 单边形态；相邻两侧 -> 角形态
    - 相对两侧或三侧以上（窄道 / 孤立小块）-> 一圈形态
    """
    trigger = triggers_for(tile_id)
    if not trigger:
        return 0

    missing = []
    for i, (dx, dy) in enumerate(_NEIGHBORS):
        n = tile_at(gx + dx, gy + dy)
        if n is not None and n in trigger:
            missing.append(i)

    if not missing:
        return 0
    if len(missing) == 1:
        return missing[0] + 1
    if len(missing) == 2:
        corners = {
            (0, 1): EDGE_TOP_RIGHT,
            (0, 3): EDGE_TOP_LEFT,
            (1, 2): EDGE_BOTTOM_RIGHT,
            (2, 3): EDGE_BOTTOM_LEFT,
        }
        # 相对的两条边（上+下 / 左+右）没有角形态 -> 四周压一圈边
        return corners.get(tuple(sorted(missing)), EDGE_RING)
    # 三面或四面都缺：孤立的一小块地面，四周压一圈边
    return EDGE_RING


def edge_kind_name(shape: int) -> str:
    """形态号 -> 可读名字（调试 / 单测报错用）。"""
    return {
        0: "none",
        EDGE_TOP: "top",
        EDGE_RIGHT: "right",
        EDGE_BOTTOM: "bottom",
        EDGE_LEFT: "left",
        EDGE_TOP_LEFT: "top_left",
        EDGE_TOP_RIGHT: "top_right",
        EDGE_BOTTOM_LEFT: "bottom_left",
        EDGE_BOTTOM_RIGHT: "bottom_right",
        EDGE_RING: "ring",
    }.get(shape, "?")


# ======================================================================
# 三、绘制用的矩形裁剪（纯数学）
# ======================================================================
def blit_rect(
    dx: int, dy: int, size: int, screen_w: int, screen_h: int
) -> tuple[int, int, int, int] | None:
    """把「格子左上角在屏幕上的位置」裁到屏幕内，返回 (dx, dy, w, h)。

    完全在屏幕外时返回 None（调用方直接跳过，省一次 blt）。
    视口边缘那一列 / 行格子只有一部分可见，必须裁。
    """
    w = size
    h = size
    if dx < 0:
        w += dx
        dx = 0
    if dy < 0:
        h += dy
        dy = 0
    if dx + w > screen_w:
        w = screen_w - dx
    if dy + h > screen_h:
        h = screen_h - dy
    if w <= 0 or h <= 0:
        return None
    return dx, dy, w, h


def blit_source(dx: int, dy: int, size: int) -> tuple[int, int, int, int]:
    """与 blit_rect 配套的**源**矩形 (sx, sy, w, h)。

    源矩形的起点不能是负数：格子跑到屏幕外时，要从图块里「被裁掉的那部分」
    开始取像素，否则会把图块的上 / 左边界重复画出来。
    """
    sx = -dx if dx < 0 else 0
    sy = -dy if dy < 0 else 0
    return sx, sy, size - sx, size - sy
