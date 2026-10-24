"""标题 -> 场景 的流转测试（批 3 / T5）。

- 「新游戏」确认键 -> 开局三选一（StarterScene），再确认 -> FieldScene；
- 「继续游戏」确认键 -> 读档：没有存档时停在标题并提示「没有找到存档」。

注意：读档路径在测试里被临时改到临时目录（save_io.SAVE_PATH），
**不会**碰到仓库里的 saves/save1.json。
"""

from __future__ import annotations

import os
import tempfile
import unittest

from src.core.game import Game
from src.core.input import FakeInput
from src.data import map_data
from src.model import save_io
from src.scenes.field_scene import FieldScene
from src.scenes.starter_scene import StarterScene
from src.scenes.title_scene import TitleScene
from tests import helpers


class TitleFlowTest(unittest.TestCase):
    def setUp(self):
        helpers.ensure_init()
        # 读档路径挪到临时目录，避免污染仓库里的 saves/save1.json
        self._tmp = tempfile.TemporaryDirectory()
        self._old_path = save_io.SAVE_PATH
        save_io.SAVE_PATH = os.path.join(self._tmp.name, "save1.json")

    def tearDown(self):
        save_io.SAVE_PATH = self._old_path
        self._tmp.cleanup()

    def test_new_game_enters_starter_scene(self):
        """「新游戏」先进三选一，而不是直接进地图。"""
        game = Game(input=FakeInput(script=[{"confirm": 1}]))
        game.update()
        self.assertIsInstance(game.scenes.current, StarterScene)

    def test_starter_confirm_enters_field_scene(self):
        """三选一确认 -> 地图 1 新手村。"""
        # 两段 confirm 之间留一帧空档：FakeInput.pressed() 是「边沿」，
        # 连续两帧按同一个键会被当成「按住」，第二次不会触发 pressed。
        game = Game(input=FakeInput(script=[{"confirm": 1}, {}, {"confirm": 1}]))
        game.update()          # 新游戏 -> 三选一
        game.update()          # 空档
        game.update()          # 确认 -> 地图
        scene = game.scenes.current
        self.assertIsInstance(scene, FieldScene)
        self.assertEqual(scene.map_id, map_data.START_MAP_ID)
        self.assertEqual((scene.gx, scene.gy), map_data.MAPS[1]["spawn"])
        self.assertIsNotNone(game.player)
        self.assertEqual(game.player.party[0].species_id, 1)

    def test_continue_game_stays_on_title(self):
        """没有存档时，「继续游戏」停在标题并给提示。"""
        game = Game(input=FakeInput(script=[{"down": 1}, {"confirm": 1}]))
        game.update()          # 光标移到「继续游戏」
        game.update()          # 按确认
        self.assertIsInstance(game.scenes.current, TitleScene)
        self.assertEqual(game.scenes.current.hint, "没有找到存档")

    def test_hint_disappears_after_60_frames(self):
        """提示 60 帧后自动消失。"""
        game = Game(input=FakeInput(script=[{"down": 1}, {"confirm": 1}]))
        game.update()
        game.update()
        self.assertTrue(game.scenes.current.hint)
        for _ in range(60):
            game.update()
        self.assertEqual(game.scenes.current.hint, "")

    def test_player_state_defaults(self):
        game = Game()
        self.assertEqual(game.player_state["dollars"], 300)
        self.assertEqual(game.player_state["map_id"], 1)
        self.assertEqual((game.player_state["x"], game.player_state["y"]), (15, 10))
        self.assertEqual(game.player_state["facing"], "down")


if __name__ == "__main__":
    unittest.main()
