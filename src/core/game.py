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

from src.assets_gen import sprite_base
from src.core.input import Input, RealInput
from src.core.scene_manager import SceneManager
from src.data import map_data
from src.data import species_data as sd
from src.model import Player
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

        #: 玩家状态（队伍 / 金币 / 背包）。
        #: **临时**：T5 会换成「开局三选一」流程（现在固定用御三家第一只）。
        self.player: Player = Player.new_game(sd.STARTER_IDS[0])

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
