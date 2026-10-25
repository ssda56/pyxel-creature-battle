"""伤害飘字（《数值设定.md》§13.3）。

规格
----
- 圆圈：pyxel.circ(x, y, 9, 底色) + pyxel.circb(x, y, 9, 边色)，内部 pyxel.text 画数字；
- 我方受伤：底 8（红）/ 边 15（白）/ 数字 7（白）；
- 敌方受伤：底 15（白）/ 边 7（白）/ 数字 0（黑）；
- 上移 24 px、持续 60 帧（@60fps = 1 秒）、最后 20 帧闪烁消失。

**数字走 pyxel.text（内置 8px 位图字体）**：里面只有阿拉伯数字，
没有中文字形，所以不走 :mod:`src.ui.text`（那里只负责中文）。

描边
----
圆圈数字外面套一圈 **1px 深色描边**（色 5 深紫），在浅色的天空 / 草地背景上
能清楚地分出圆圈的轮廓。描边色选 **色 5** 而不是色 0 的原因见
:data:`OUTLINE_COLOR`。

**描边加在"圆圈"上而不是"数字笔画"上**：Pyxel 内置位图字体一个字符只有
4x6 像素（字形 3x5），如果给笔画本身描 1px 边，"8 / 0 / 6 / 9" 的字洞
会被描边色填死，数字直接变成一团黑块。圆圈外框既解决了浅色背景上的
可读性，又不会毁掉数字本身。
"""

from __future__ import annotations

import pyxel

from src.assets_gen import palette

#: 圆圈半径（§13.3）
CIRCLE_RADIUS = 9

#: 飘字总时长（帧，§13.3「持续 30 帧」@30fps -> 60 帧 @60fps = 1 秒）
LIFETIME = 60

#: 飘字上移距离（像素，§13.3「上移 24 px」）
RISE = 24

#: 最后多少帧开始闪烁（§13.3「最后 10 帧」@30fps -> 20 帧 @60fps = 333ms）
BLINK_FRAMES = 20

# ---------------------------------------------------------------- 配色
#: 敌方受伤：底 15（白）/ 边 7（白）/ 字 0（黑）
ENEMY_BACK = 15
ENEMY_EDGE = 7
ENEMY_TEXT = 0

#: 我方受伤：底 8（红）/ 边 15（白）/ 字 7（白）
PLAYER_BACK = 8
PLAYER_EDGE = 15
PLAYER_TEXT = 7

#: 圆圈数字的描边色 = **色 5 深紫**。
#:
#: 为什么不选色 0（黑）：
#:
#: - 色 0 是本项目 `pyxel.blt(colkey=0)` 的**透明键**，语义上被保留；
#: - 敌方飘字的字色**本身就是色 0**，用色 0 描边等于没描边；
#: - 色 0 是纯黑，在深色背景（红圆圈色 8）上会糊成一片。
#:
#: 色 5（深紫）在调色板文档里本来就是「精灵描边专用色」，
#: 在浅蓝天空（色 12）、浅绿草地（色 4）、浅灰圆圈（色 15）上都能压出边缘。
OUTLINE_COLOR = palette.DARK_PURPLE

#: 描边宽度（像素）：圆圈外再套一圈 1px 的深色
OUTLINE_WIDTH = 1


class DamageNumber:
    """一个正在飘出的伤害数字。

    参数
    ----
    x, y
        圆圈中心的**初始**屏幕坐标（会随时间向上移动）。
    value
        显示的数字（伤害值）。
    kind
        "enemy"（敌方受伤）或 "player"（我方受伤），决定配色。
    """

    def __init__(self, x: int, y: int, value: int, kind: str = "enemy"):
        self.x = int(x)
        self.y = int(y)
        self.value = int(value)
        self.kind = "player" if str(kind) == "player" else "enemy"
        #: 已经过的帧数
        self.age = 0
        self._done = False

    # ------------------------------------------------------------ 状态
    @property
    def done(self) -> bool:
        """是否已经消失（生命周期结束）。"""
        return self._done

    @property
    def colors(self) -> tuple[int, int, int]:
        """(底色, 边色, 字色)。"""
        if self.kind == "player":
            return (PLAYER_BACK, PLAYER_EDGE, PLAYER_TEXT)
        return (ENEMY_BACK, ENEMY_EDGE, ENEMY_TEXT)

    @property
    def offset_y(self) -> int:
        """已经上移的像素数（0 ~ RISE）。"""
        if self.age <= 0:
            return 0
        return int(RISE * self.age / LIFETIME)

    @property
    def visible(self) -> bool:
        """本帧是否要画（最后 20 帧闪烁）。"""
        if self._done:
            return False
        if self.age >= LIFETIME - BLINK_FRAMES:
            return (self.age % 2) == 0
        return True

    # ------------------------------------------------------------ 每帧
    def update(self) -> bool:
        """推进一帧。

        返回
        ----
        bool
            True 表示还在飘；False 表示这个数字已经消失（该被回收了）。
        """
        if self._done:
            return False
        self.age += 1
        if self.age >= LIFETIME:
            self._done = True
            return False
        return True

    def draw(self, offset: tuple[int, int] = (0, 0)) -> None:
        """画这个圆圈数字（闪烁帧自动跳过）。

        参数
        ----
        offset
            额外的屏幕偏移（震屏用）。默认 (0, 0) 表示不偏移。
        """
        if not self.visible:
            return
        ox = int(offset[0]) if offset else 0
        oy = int(offset[1]) if offset else 0
        cx = self.x + ox
        cy = self.y - self.offset_y + oy
        back, edge, fg = self.colors
        # ⑥ 1px 深色描边：先画一圈大一号的深色圆当外框，再压上原来的圆圈
        pyxel.circ(cx, cy, CIRCLE_RADIUS + OUTLINE_WIDTH, OUTLINE_COLOR)
        pyxel.circ(cx, cy, CIRCLE_RADIUS, back)
        pyxel.circb(cx, cy, CIRCLE_RADIUS, edge)
        label = str(self.value)
        # Pyxel 2.9.9 没有 text_width()，内置字体每个字符固定 FONT_WIDTH 宽
        width = len(label) * pyxel.FONT_WIDTH
        pyxel.text(cx - width // 2, cy - 4, label, fg)


class DamageNumberGroup:
    """管理多个同时飘出的数字。

    用法::

        group = DamageNumberGroup()
        group.add(166, 36, 12, "enemy")
        group.update()   # 每帧调一次
        group.draw()
    """

    def __init__(self):
        #: 正在飘的数字
        self.numbers: list[DamageNumber] = []

    # ------------------------------------------------------------ 增删
    def add(self, x: int, y: int, value: int, kind: str = "enemy") -> DamageNumber:
        """新增一个飘字，返回它。"""
        number = DamageNumber(x, y, value, kind)
        self.numbers.append(number)
        return number

    def clear(self) -> None:
        """清空所有飘字。"""
        self.numbers.clear()

    # ------------------------------------------------------------ 每帧
    def update(self) -> None:
        """推进一帧，回收已经消失的数字。"""
        alive: list[DamageNumber] = []
        for number in self.numbers:
            if number.update():
                alive.append(number)
        self.numbers = alive

    def draw(self, offset: tuple[int, int] = (0, 0)) -> None:
        """画出所有还在飘的数字。

        参数
        ----
        offset
            额外的屏幕偏移（震屏用）。默认 (0, 0) 表示不偏移。
        """
        for number in self.numbers:
            number.draw(offset)

    # ------------------------------------------------------------ 查询
    @property
    def count(self) -> int:
        """当前还在飘的数字个数。"""
        return len(self.numbers)

    def __len__(self) -> int:
        return len(self.numbers)
