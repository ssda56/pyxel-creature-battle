"""标题画面（本批占位版）。

画面
----
- 深蓝底（色 1）
- 标题「精灵对战」居中，色 10（黄）
- 菜单两项「新游戏」「继续游戏」，黄色三角光标（色 10）
- 底部小字「Pyxel 2.9.9 · 240x216」，色 5（深紫）

光标用 `pyxel.tri()` 画的小三角形而不是 "▶" 字符，
因为字体里的 ▶ 字形不保证存在（《数值设定.md》§13.2 允许这两种做法）。

「新游戏」按确认键 -> 进入 FieldScene（地图 1 新手村）；
「继续游戏」本批仍只打印一行日志（读档由 T5 实现）。
"""

from __future__ import annotations

import pyxel

from src.assets_gen import palette
from src.data import map_data
from src.scenes.field_scene import FieldScene
from src.scenes.scene_base import Scene
from src.ui import text

TITLE_TEXT = "精灵对战"
MENU_ITEMS: tuple[str, ...] = ("新游戏", "继续游戏")
FOOTER_TEXT = "Pyxel 2.9.9 · 240x216"

#: 画面布局
TITLE_X = 120
TITLE_Y = 42
MENU_X = 92
MENU_Y = 100
MENU_STEP = 22
CURSOR_X = 78
FOOTER_Y = 196


class TitleScene(Scene):
    """标题画面。"""

    def __init__(self, game):
        super().__init__(game)
        self.index = 0

    # ------------------------------------------------------------ 生命周期
    def enter(self, **kwargs) -> None:
        """进入标题画面：光标回到第一项。"""
        self.index = 0

    # ------------------------------------------------------------ 每帧
    def update(self, inp) -> None:
        """上下键移动光标，确认键执行对应菜单项。"""
        if inp.pressed("up"):
            self.index = (self.index - 1) % len(MENU_ITEMS)
        if inp.pressed("down"):
            self.index = (self.index + 1) % len(MENU_ITEMS)
        if inp.pressed("confirm"):
            item = MENU_ITEMS[self.index]
            if self.index == 0:
                # 新游戏：直接进地图探索（起始地图 1 新手村）
                self.game.scenes.replace(
                    FieldScene(self.game), map_id=map_data.START_MAP_ID
                )
            else:
                # 继续游戏：读档由 T5 实现
                print(f"[TitleScene] 选择：{item}（读档由 T5 实现，本批只打印）", flush=True)

    def draw(self) -> None:
        """绘制标题画面。"""
        pyxel.cls(palette.DEEP_BLUE)

        text.draw_center(TITLE_X, TITLE_Y, TITLE_TEXT, palette.YELLOW)

        for i, item in enumerate(MENU_ITEMS):
            y = MENU_Y + i * MENU_STEP
            text.draw(MENU_X, y, item, palette.WHITE)
            if i == self.index:
                # 光标：小三角形（色 10 黄）
                pyxel.tri(
                    CURSOR_X, y + 1,
                    CURSOR_X, y + 11,
                    CURSOR_X + 8, y + 6,
                    palette.YELLOW,
                )

        text.draw_center(TITLE_X, FOOTER_Y, FOOTER_TEXT, palette.DARK_PURPLE)
