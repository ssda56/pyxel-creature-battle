"""标题画面（批 3 / T5）。

画面
----
- 深蓝底（色 1）
- 标题「精灵对战」居中，色 10（黄）
- 菜单两项「新游戏」「继续游戏」，黄色三角光标（色 10）
- 底部小字「Pyxel 2.9.9 · 240x216」，色 5（深紫）

光标用 `pyxel.tri()` 画的小三角形而不是 "▶" 字符，
因为字体里的 ▶ 字形不保证存在（《数值设定.md》§13.2 允许这两种做法）。

「新游戏」按确认键 -> 开局三选一（StarterScene，挑初始精灵）；
「继续游戏」按确认键 -> 读档（save_io.load_game）：

- "ok"          -> 进入 FieldScene（地图 / 坐标 / 朝向都来自存档）；
- "no_file"     -> 标题下方显示「没有找到存档」120 帧（2 秒）；
- "bad_version" -> 显示「存档版本不兼容」；
- "corrupt"     -> 显示「存档已损坏」。

三种失败都**不崩溃**、**不改写原存档**。
"""

from __future__ import annotations

import pyxel

from src.assets_gen import palette
from src.data import map_data
from src.model import save_io
from src.scenes.field_scene import FieldScene
from src.scenes.scene_base import Scene
from src.scenes.starter_scene import StarterScene
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
#: 读档失败提示的 y 坐标与持续帧数
#: HINT_FRAMES = 120 帧 @60fps = 2 秒，与 60 帧 @30fps 一致
HINT_Y = 150
HINT_FRAMES = 120

#: 读档结果码 -> 提示文字
LOAD_ERROR_HINTS: dict[str, str] = {
    save_io.RESULT_NO_FILE: "没有找到存档",
    save_io.RESULT_BAD_VERSION: "存档版本不兼容",
    save_io.RESULT_CORRUPT: "存档已损坏",
}


class TitleScene(Scene):
    """标题画面。"""

    def __init__(self, game):
        super().__init__(game)
        self.index = 0
        #: 读档失败提示（空串 = 不显示）
        self.hint: str = ""
        self.hint_timer: int = 0

    # ------------------------------------------------------------ 生命周期
    def enter(self, **kwargs) -> None:
        """进入标题画面：光标回到第一项，提示清空。"""
        self.index = 0
        self.hint = ""
        self.hint_timer = 0

    # ------------------------------------------------------------ 每帧
    def update(self, inp) -> None:
        """上下键移动光标，确认键执行对应菜单项。"""
        if inp.pressed("up"):
            self.index = (self.index - 1) % len(MENU_ITEMS)
        if inp.pressed("down"):
            self.index = (self.index + 1) % len(MENU_ITEMS)
        if self.hint_timer > 0:
            self.hint_timer -= 1
            if self.hint_timer <= 0:
                self.hint_timer = 0
                self.hint = ""
        if inp.pressed("confirm"):
            if self.index == 0:
                # 新游戏：开局三选一（挑初始精灵）
                self.game.scenes.replace(StarterScene(self.game))
            else:
                # 继续游戏：读档
                self._continue_game()

    def _continue_game(self) -> None:
        """读档：成功进地图，失败在标题下方给一行提示。"""
        result = save_io.load_game(self.game)
        if result == save_io.RESULT_OK:
            state = getattr(self.game, "player_state", None) or {}
            self.game.scenes.replace(
                FieldScene(self.game),
                map_id=state.get("map_id", map_data.START_MAP_ID),
                x=state.get("x"),
                y=state.get("y"),
                facing=state.get("facing"),
            )
            return
        self.hint = LOAD_ERROR_HINTS.get(result, "读档失败")
        self.hint_timer = HINT_FRAMES

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

        if self.hint:
            text.draw_center(TITLE_X, HINT_Y, self.hint, palette.YELLOW)

        text.draw_center(TITLE_X, FOOTER_Y, FOOTER_TEXT, palette.DARK_PURPLE)
