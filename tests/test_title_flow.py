"""标题 -> 地图 的场景流转测试（批 1）。

- 「新游戏」确认键 -> FieldScene（地图 1 新手村，出生点 15,10）；
- 「继续游戏」确认键 -> 仍停在标题画面（读档由 T5 实现）。
"""

from __future__ import annotations

import unittest

from src.core.game import Game
from src.core.input import FakeInput
from src.data import map_data
from src.scenes.field_scene import FieldScene
from src.scenes.title_scene import TitleScene
from tests import helpers


class TitleFlowTest(unittest.TestCase):
    def setUp(self):
        helpers.ensure_init()

    def test_new_game_enters_field_scene(self):
        game = Game(input=FakeInput(script=[{"confirm": 1}]))
        game.update()
        scene = game.scenes.current
        self.assertIsInstance(scene, FieldScene)
        self.assertEqual(scene.map_id, map_data.START_MAP_ID)
        self.assertEqual((scene.gx, scene.gy), map_data.MAPS[1]["spawn"])

    def test_continue_game_stays_on_title(self):
        game = Game(input=FakeInput(script=[{"down": 1}, {"confirm": 1}]))
        game.update()          # 光标移到「继续游戏」
        game.update()          # 按确认
        self.assertIsInstance(game.scenes.current, TitleScene)

    def test_player_state_defaults(self):
        game = Game()
        self.assertEqual(game.player_state["dollars"], 300)
        self.assertEqual(game.player_state["map_id"], 1)
        self.assertEqual((game.player_state["x"], game.player_state["y"]), (15, 10))
        self.assertEqual(game.player_state["facing"], "down")


if __name__ == "__main__":
    unittest.main()
