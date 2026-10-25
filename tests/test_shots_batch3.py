"""批 3 截图：菜单 / 精灵 / 背包 / 三选一 / 存档完成（docs/shots/batch3_*.png）。"""

from __future__ import annotations

import os
import tempfile
import unittest

from src.core.game import Game
from src.core.input import FakeInput
from src.model import save_io
from src.model.creature import Creature
from src.model.player import Player
from src.scenes.menu_scene import MAIN_ITEMS, MenuScene
from tests import field_helpers
from tests import helpers

#: 截图输出目录
SHOTS_DIR = os.path.join(helpers.PROJECT_ROOT, "docs", "shots")


def press(game, action: str) -> None:
    """注入一次按键（后跟一帧空档，避免被当成「按住」）。"""
    game.input = FakeInput(script=[{action: 1}, {}])
    game.update()
    game.update()


def goto_main_item(game, label: str) -> None:
    """按名字导航到主菜单的某一项。

    不要用「按几次 down」写死下标——菜单项一增删下标全错（T12 加「仓库」时
    就是这么踩的，两个截图用例静默走错项）。按名字查位置，菜单怎么变都对。
    """
    for _ in range(MAIN_ITEMS.index(label)):
        press(game, "down")


def shot_path(name: str) -> str:
    return os.path.join(SHOTS_DIR, name)


class Batch3ShotTest(unittest.TestCase):
    def setUp(self):
        helpers.ensure_init()

    def _menu_game(self):
        """一个跑在地图上、带着两只精灵与道具背包的游戏。"""
        game, scene = field_helpers.make_field(map_id=1)
        game.player = Player.new_game(1)
        game.player.party.append(Creature(2, level=6, hp=30, mp=9))
        game.player.bag[5] = 1
        return game, scene

    def _shoot(self, game, name: str) -> str:
        path = shot_path(name)
        helpers.run_frames(game.update, game.draw, 2, shot_path=path, scale=2)
        self.assertTrue(os.path.exists(path), f"{name} 没有生成")
        self.assertEqual(helpers.png_size(path), (480, 432))
        return path

    # ------------------------------------------------------------ 五张截图
    def test_shot_main_menu(self):
        game, _ = self._menu_game()
        press(game, "menu")
        self.assertIsInstance(game.scenes.current, MenuScene)
        self._shoot(game, "batch3_menu.png")

    def test_shot_party(self):
        game, _ = self._menu_game()
        press(game, "menu")
        press(game, "confirm")          # 精灵
        self._shoot(game, "batch3_party.png")

    def test_shot_bag(self):
        game, _ = self._menu_game()
        press(game, "menu")
        goto_main_item(game, "道具")
        press(game, "confirm")          # 道具
        self._shoot(game, "batch3_bag.png")

    def test_shot_starter(self):
        game = Game()
        press(game, "confirm")          # 新游戏 -> 三选一
        self._shoot(game, "batch3_starter.png")

    def test_shot_save_done(self):
        tmp = tempfile.TemporaryDirectory()
        old_path = save_io.SAVE_PATH
        save_io.SAVE_PATH = os.path.join(tmp.name, "save1.json")
        try:
            game, _ = self._menu_game()
            press(game, "menu")
            goto_main_item(game, "存档")
            press(game, "confirm")      # 存档
            menu = game.scenes.current
            self.assertEqual(menu.message, "已保存到 存档 1")
            self._shoot(game, "batch3_save_done.png")
        finally:
            save_io.SAVE_PATH = old_path
            tmp.cleanup()

    # ------------------------------------------------------------ 五张都在
    def test_zz_all_five_screenshots_exist(self):
        """放在最后跑：上面几个用例已经把五张图生成好了。"""
        for name in ("batch3_menu.png", "batch3_party.png", "batch3_bag.png",
                     "batch3_starter.png", "batch3_save_done.png"):
            path = shot_path(name)
            self.assertTrue(os.path.exists(path), f"{name} 不存在")
            self.assertGreater(os.path.getsize(path), 1000)


if __name__ == "__main__":
    unittest.main()
