"""App 主类：update / draw 分发到当前场景（规划文档 §二 core/game.py）。

职责
----
- 启动时加载字体、烘焙全部素材；
- 持有场景栈（SceneManager）与输入（Input）；
- 每帧把 update / draw 分发给当前场景。

`self.input` 默认是 `RealInput()`，测试时可以直接替换成 `FakeInput`：

    game = Game()
    game.input = FakeInput(script=[{"confirm": 3}])
"""

from __future__ import annotations

import pyxel

from src.assets_gen import sprite_base
from src.core.input import ACTIONS, Input, RealInput
from src.core.scene_manager import SceneManager
from src.data import map_data
from src.scenes.title_scene import TitleScene
from src.ui import text


class Game:
    """游戏主对象。"""

    def __init__(self, input: Input | None = None):
        # 字体与素材必须先准备好，后面任何一帧绘制都要用
        text.init_font()
        sprite_base.bake_all()

        #: 输入源，测试可替换
        self.input: Input = input if input is not None else RealInput()
        #: 场景栈
        self.scenes = SceneManager()
        #: 玩家状态（存档 / HUD 读它；后续批次继续扩字段）
        # 初始金币 300（《数值设定.md》§7.1），起始地图 1 新手村
        # （出生点 15, 10，与 §11 存档格式里的 player 字段一致）。
        self.player_state: dict = {
            "dollars": 300,
            "map_id": map_data.START_MAP_ID,
            "x": 15,
            "y": 10,
            "facing": "down",
        }

        self.scenes.push(TitleScene(self))

    # ------------------------------------------------------------ 每帧
    def update(self) -> None:
        """分发一帧逻辑更新。

        顺序：先跑场景逻辑，再让输入推进到下一帧
        （这样第 N 帧的场景看到的就是第 N 帧的输入状态）。
        """
        scene = self.scenes.current
        if scene is not None:
            scene.update(self.input)
        self.input.update()

    def draw(self) -> None:
        """分发一帧绘制。"""
        scene = self.scenes.current
        if scene is not None:
            scene.draw()
        if RealInput.DEBUG:
            self._draw_debug_overlay()

    # ------------------------------------------------------------ 诊断
    def _draw_debug_overlay(self) -> None:
        """把输入与场景状态画在屏幕上（`--debug-input` 时启用）。

        用来在不看终端的情况下判断：按键到底有没有被收到（held/prs 两行），
        以及场景卡在什么状态（fade / moving / facing）。
        """
        held = [a for a in ACTIONS if self.input.held(a)]
        pressed = [a for a in ACTIONS if self.input.pressed(a)]
        cur = self.scenes.current
        rows = [
            f"scn {type(cur).__name__ if cur else 'None'}",
            f"held {','.join(held) if held else '-'}",
            f"prs  {','.join(pressed) if pressed else '-'}",
        ]
        if isinstance(self.input, RealInput):
            last = self.input.last_action or "-"
            rows.append(f"seen={self.input.seen_count} last={last}@{self.input.last_frame}")
        head = []
        for attr in ("facing", "moving"):
            if cur is not None and hasattr(cur, attr):
                head.append(f"{attr}={getattr(cur, attr)}")
        tail = []
        for attr in ("gx", "gy", "map_id"):
            if cur is not None and hasattr(cur, attr):
                tail.append(f"{attr}={getattr(cur, attr)}")
        fade = getattr(cur, "fade", None) if cur is not None else None
        if fade is not None:
            tail.append(f"fade={int(fade.is_active)}|{fade.level}")
        if head:
            rows.append(" ".join(head))
        if tail:
            rows.append(" ".join(tail))

        y = 2
        for row in rows:
            pyxel.rect(0, y - 1, 240, 12, 0)
            text.draw(2, y, row, 7)
            y += 12
