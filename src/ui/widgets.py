"""战斗界面小部件（《数值设定.md》§13.1 / §13.2）。

包含三样东西：

- :func:`draw_bar`：进度条（HP 条 / MP 条），比例自动夹取到 [0, 1]；
- :func:`draw_status_box`：战斗信息框（名称 + 等级 + HP 条 + HP 数字 + MP 条 + MP 数字）；
- :class:`MenuList`：竖排选项菜单（带 ▶ 光标、可置灰）。

中文一律走 :mod:`src.ui.text`；纯数字用 pyxel.text 内置位图字体（更紧凑）。
"""

from __future__ import annotations

import pyxel

from src.assets_gen import palette
from src.ui import text

#: 画面尺寸（与 main.py 锁定值一致）
SCREEN_W = 240
SCREEN_H = 216

# ---------------------------------------------------------------- 信息框（§13.1）
#: 信息框尺寸 116x38
STATUS_BOX_W = 116
STATUS_BOX_H = 38

#: HP 条：宽 100、高 5，色 8 红底 / 色 11 绿
HP_BAR_W = 100
HP_BAR_H = 5
HP_BAR_BACK = palette.RED
HP_BAR_FORE = palette.LIGHT_GREEN

#: MP 条：宽 66、高 4，色 1 深底 / 色 12 浅蓝
MP_BAR_W = 66
MP_BAR_H = 4
MP_BAR_BACK = palette.DEEP_BLUE
MP_BAR_FORE = palette.LIGHT_BLUE

#: 框内留白
BOX_PAD = 4

#: 选项被置灰时使用的颜色（§5.3「颜色用色 5 深紫表示不可用」）
DISABLED_COLOR = palette.DARK_PURPLE

#: 光标颜色（§13.2「色 10 黄」）
CURSOR_COLOR = palette.YELLOW


def draw_bar(x: int, y: int, w: int, h: int, ratio: float,
             back_col: int, fore_col: int) -> None:
    """画一条进度条。

    `ratio` 会被夹取到 `[0, 1]`：小于 0 当 0，大于 1 当 1，
    所以调用方不必自己判断边界。
    """
    x = int(x)
    y = int(y)
    w = max(0, int(w))
    h = max(0, int(h))
    if w <= 0 or h <= 0:
        return
    value = float(ratio)
    if value < 0.0:
        value = 0.0
    elif value > 1.0:
        value = 1.0
    pyxel.rect(x, y, w, h, int(back_col))
    filled = int(w * value)
    if filled > 0:
        pyxel.rect(x, y, filled, h, int(fore_col))


def draw_status_box(x: int, y: int, name: str, level: int,
                    hp: int, hp_max: int, mp: int, mp_max: int) -> None:
    """画战斗信息框（§13.1）。

    框内从上到下：

    1. 名称（左边）+ 等级（右边）
    2. HP 条 100x5
    3. HP 数字
    4. MP 条 66x4
    5. MP 数字
    """
    x = int(x)
    y = int(y)

    # 框体
    pyxel.rect(x, y, STATUS_BOX_W, STATUS_BOX_H, palette.LIGHT_GRAY)
    pyxel.rectb(x, y, STATUS_BOX_W, STATUS_BOX_H, palette.DARK_PURPLE)

    # 名称 + 等级
    text.draw(x + BOX_PAD, y + 1, str(name), palette.BLACK)
    lv = f"Lv{int(level)}"
    text.draw(x + STATUS_BOX_W - BOX_PAD - text.width(lv), y + 1, lv, palette.BLACK)

    # HP 条 + HP 数字
    hp_ratio = (float(hp) / float(hp_max)) if int(hp_max) > 0 else 0.0
    draw_bar(x + 8, y + 13, HP_BAR_W, HP_BAR_H, hp_ratio,
             HP_BAR_BACK, HP_BAR_FORE)
    pyxel.text(x + 8, y + 18, f"{int(hp)}/{int(hp_max)}", palette.BLACK)

    # MP 条 + MP 数字
    mp_ratio = (float(mp) / float(mp_max)) if int(mp_max) > 0 else 0.0
    draw_bar(x + 8, y + 26, MP_BAR_W, MP_BAR_H, mp_ratio,
             MP_BAR_BACK, MP_BAR_FORE)
    pyxel.text(x + 8, y + 30, f"{int(mp)}/{int(mp_max)}", palette.BLACK)


class MenuList:
    """竖排选项菜单（§13.2 五指令、战斗里的技能 / 精灵 / 道具列表）。

    `items` 是 `list[dict]`，每项至少含：

    - "label"：显示文字（中文，走 text.draw）；
    - "enabled"：是否可选（False = 置灰，色 5）。

    可选键：

    - "x" / "y"：该项的绝对屏幕坐标（给了就用，没给按网格算）；
    - "col" / "row"：多列布局里的列号 / 行号（用于上下左右移动）。
    """

    def __init__(self, x: int, y: int, items, line_h: int = 14, cols: int = 1,
                 col_w: int = 116):
        self.x = int(x)
        self.y = int(y)
        self.items: list[dict] = [dict(it) for it in (items or [])]
        self.line_h = max(1, int(line_h))
        self.cols = max(1, int(cols))
        self.col_w = int(col_w)
        #: 当前光标位置（items 的下标）
        self.index = 0

    # ------------------------------------------------------------ 查询
    @property
    def selected(self) -> dict:
        """当前选中的项（没有项时返回空 dict）。"""
        if not self.items:
            return {}
        return self.items[self.index]

    @property
    def selected_index(self) -> int:
        """当前选中的下标。"""
        return self.index

    @property
    def count(self) -> int:
        """选项个数。"""
        return len(self.items)

    def is_enabled(self, index: int | None = None) -> bool:
        """某一项是否可选（默认查当前项）。"""
        i = self.index if index is None else int(index)
        if i < 0 or i >= len(self.items):
            return False
        return bool(self.items[i].get("enabled", True))

    # ------------------------------------------------------------ 移动
    def _col_of(self, i: int) -> int:
        item = self.items[i]
        col = item.get("col")
        if col is None:
            col = i % self.cols
        return int(col)

    def _row_of(self, i: int) -> int:
        item = self.items[i]
        row = item.get("row")
        if row is not None:
            return int(row)
        col = self._col_of(i)
        same = [j for j in range(len(self.items)) if self._col_of(j) == col]
        return same.index(i)

    def _members(self, col: int) -> list[int]:
        """某一列里的下标（按行号排序）。"""
        same = [j for j in range(len(self.items)) if self._col_of(j) == col]
        return sorted(same, key=self._row_of)

    def move(self, delta: int) -> int:
        """上下移动光标（在同一列内移动，单列时就是整列）。

        返回移动后的下标。
        """
        if not self.items:
            return self.index
        if self.cols == 1:
            self.index = (self.index + int(delta)) % len(self.items)
            return self.index
        col = self._col_of(self.index)
        members = self._members(col)
        if not members:
            return self.index
        pos = members.index(self.index) if self.index in members else 0
        pos = (pos + int(delta)) % len(members)
        self.index = members[pos]
        return self.index

    def move_h(self, delta: int) -> int:
        """左右移动光标（换列；单列时不动）。"""
        if not self.items or self.cols <= 1:
            return self.index
        col = self._col_of(self.index)
        new_col = col + int(delta)
        if new_col < 0 or new_col >= self.cols:
            return self.index
        candidates = self._members(new_col)
        if not candidates:
            return self.index
        row = self._row_of(self.index)
        best = min(candidates, key=lambda i: abs(self._row_of(i) - row))
        self.index = best
        return self.index

    # ------------------------------------------------------------ 确认
    def confirm(self) -> bool:
        """确认当前项。

        返回 True 表示**确实执行**了；
        返回 False 表示当前项被置灰（MP 不足等），确认键无效。
        """
        if not self.items:
            return False
        if not self.is_enabled():
            return False
        return True

    # ------------------------------------------------------------ 绘制
    def item_pos(self, index: int) -> tuple[int, int]:
        """某一项的绘制坐标（绝对屏幕坐标）。"""
        item = self.items[index]
        if "x" in item and "y" in item:
            return int(item["x"]), int(item["y"])
        col = self._col_of(index)
        row = self._row_of(index)
        return self.x + col * self.col_w, self.y + row * self.line_h

    def draw(self) -> None:
        """画所有选项 + 光标。"""
        for i in range(len(self.items)):
            item = self.items[i]
            px, py = self.item_pos(i)
            if py < 0 or py >= SCREEN_H or px < 0 or px >= SCREEN_W:
                continue
            enabled = bool(item.get("enabled", True))
            color = palette.BLACK if enabled else DISABLED_COLOR
            text.draw(px, py, str(item.get("label", "")), color)
            if i == self.index:
                # 光标：黄色小三角（§13.2 允许 pyxel.tri）
                pyxel.tri(px - 9, py + 1, px - 9, py + 11, px - 2, py + 6,
                          CURSOR_COLOR)
