"""开局三选一 + 继续游戏流程测试（批 3 / T5）。

- 三选一：选水滴滴 -> 队伍里是水滴滴 Lv5、金币 300、背包 {1:5, 2:2, 4:1}；
- 左右键移动光标，取消回标题；
- 继续游戏：存档 -> 新建 Game（模拟重启）-> 标题选「继续游戏」-> 进地图，
  坐标 / 朝向 / 队伍 / 金币 与存档一致；
- 读档失败：没有存档 / 版本不对 / 文件损坏都只提示，不崩溃。
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from src.core.game import Game
from src.core.input import FakeInput
from src.data import map_data
from src.model import save_io
from src.model.player import Player
from src.scenes.field_scene import FieldScene
from src.scenes.starter_scene import StarterScene
from src.scenes.title_scene import TitleScene
from tests import helpers


def press(game, action: str) -> None:
    """注入一次按键（后跟一帧空档，避免被当成「按住」）。"""
    game.input = FakeInput(script=[{action: 1}, {}])
    game.update()
    game.update()


class StarterSceneTest(unittest.TestCase):
    def setUp(self):
        helpers.ensure_init()

    def _open_starter(self) -> Game:
        game = Game()
        press(game, "confirm")        # 新游戏 -> 三选一
        return game

    def test_new_game_opens_starter_scene(self):
        game = Game()
        press(game, "confirm")
        self.assertIsInstance(game.scenes.current, StarterScene)

    def test_left_right_moves_cursor(self):
        game = self._open_starter()
        scene = game.scenes.current
        self.assertEqual(scene.index, 0)
        press(game, "right")
        self.assertEqual(scene.index, 1)
        press(game, "right")
        self.assertEqual(scene.index, 2)
        press(game, "left")
        self.assertEqual(scene.index, 1)

    def test_choose_water_drop(self):
        """选水滴滴 -> 队伍 / 等级 / 金币 / 背包。"""
        game = self._open_starter()
        press(game, "right")          # 水滴滴
        press(game, "confirm")

        scene = game.scenes.current
        self.assertIsInstance(scene, FieldScene)
        self.assertIsNotNone(game.player)
        self.assertEqual(game.player.party[0].species_id, 2)
        self.assertEqual(game.player.party[0].level, 5)
        self.assertEqual(game.player.dollars, 300)
        self.assertEqual(game.player.bag, {1: 5, 2: 2, 4: 1})
        self.assertEqual(scene.map_id, map_data.START_MAP_ID)

    def test_choose_rabbit(self):
        game = self._open_starter()
        press(game, "right")
        press(game, "right")          # 兔小子
        press(game, "confirm")
        self.assertEqual(game.player.party[0].species_id, 3)

    def test_cancel_returns_to_title(self):
        game = self._open_starter()
        press(game, "cancel")
        self.assertIsInstance(game.scenes.current, TitleScene)
        self.assertIsNone(game.player)

    def test_starter_draw_runs(self):
        game = self._open_starter()
        helpers.run_frames(game.update, game.draw, 3)


class ContinueGameTest(unittest.TestCase):
    """继续游戏（读档）流程。"""

    def setUp(self):
        helpers.ensure_init()
        self.tmp = tempfile.TemporaryDirectory()
        self.old_path = save_io.SAVE_PATH
        save_io.SAVE_PATH = os.path.join(self.tmp.name, "save1.json")

    def tearDown(self):
        save_io.SAVE_PATH = self.old_path
        self.tmp.cleanup()

    def _saved_game(self) -> Game:
        game = Game()
        game.player = Player.new_game(2)
        game.player.dollars = 456
        game.player_state.update({"map_id": 1, "x": 16, "y": 10, "facing": "left"})
        self.assertTrue(save_io.save_game(game))
        return game

    def test_continue_restores_state(self):
        saved = self._saved_game()

        # 模拟重启：全新一个 Game
        game = Game()
        press(game, "down")           # 光标移到「继续游戏」
        press(game, "confirm")

        scene = game.scenes.current
        self.assertIsInstance(scene, FieldScene)
        self.assertEqual(scene.map_id, 1)
        self.assertEqual((scene.gx, scene.gy), (16, 10))
        self.assertEqual(scene.facing, "left")
        self.assertEqual(game.player.party[0].species_id, 2)
        self.assertEqual(game.player.dollars, 456)
        self.assertEqual(game.player.bag, saved.player.bag)

    def test_continue_without_save_shows_hint(self):
        game = Game()
        press(game, "down")
        press(game, "confirm")
        self.assertIsInstance(game.scenes.current, TitleScene)
        self.assertEqual(game.scenes.current.hint, "没有找到存档")

    def test_continue_with_bad_version_shows_hint(self):
        payload = {
            "save_version": 999, "timestamp": "x", "play_seconds": 0,
            "dollars": 1, "player": {"map_id": 1, "x": 15, "y": 10, "facing": "down"},
            "party": [], "storage": [], "bag": {},
        }
        with open(save_io.SAVE_PATH, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

        game = Game()
        press(game, "down")
        press(game, "confirm")
        self.assertIsInstance(game.scenes.current, TitleScene)
        self.assertEqual(game.scenes.current.hint, "存档版本不兼容")

    def test_continue_with_corrupt_file_shows_hint(self):
        with open(save_io.SAVE_PATH, "w", encoding="utf-8") as fh:
            fh.write("{坏了")

        game = Game()
        press(game, "down")
        press(game, "confirm")
        self.assertIsInstance(game.scenes.current, TitleScene)
        self.assertEqual(game.scenes.current.hint, "存档已损坏")


if __name__ == "__main__":
    unittest.main()
