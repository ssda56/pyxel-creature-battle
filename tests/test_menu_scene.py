"""菜单场景测试（批 3 / T5）。

- 菜单用 **push / pop**：关掉后地图位置 / 野外状态 / 刷怪数全部不变；
- 道具使用：伤药回 30 HP（不超上限）、背包 -1；背包空了只提示不报错；
- 复活草：只对倒下的精灵生效；
- 队伍调换：交换第 1、2 只后顺序确实改变；
- 存档菜单项：写入存档并提示「已保存到 存档 1」；
- player 为 None 时菜单不崩。

**所有用例的存档路径都挪到临时目录**（base class 里 patch save_io.SAVE_PATH），
绝不碰仓库里的 saves/save1.json。
"""

from __future__ import annotations

import os
import tempfile
import unittest

from src.core.game import Game
from src.core.input import FakeInput
from src.model import save_io
from src.model.creature import Creature
from src.model.player import Player
from src.scenes.field_scene import wild_state_of
from src.scenes.menu_scene import MenuScene
from tests import field_helpers
from tests import helpers

#: 道具 ID（《数值设定.md》§7.1）
BALL_ID = 1
POTION_ID = 2
BLUE_POTION_ID = 4
REVIVE_ID = 5

#: 主菜单四项的顺序（src.scenes.menu_scene.MAIN_ITEMS）
ITEM_PARTY = 0
ITEM_BAG = 1
ITEM_SAVE = 2
ITEM_BACK = 3


def press(game, action: str) -> None:
    """注入一次按键。

    脚本后面留一帧空档：FakeInput.pressed() 是边沿检测，
    连续两帧按同一个键会被当成「按住」。
    """
    game.input = FakeInput(script=[{action: 1}, {}])
    game.update()
    game.update()


def make_game(map_id: int = 1, x=None, y=None):
    """建一个跑在地图上的游戏，并给一个玩家。"""
    game, scene = field_helpers.make_field(map_id=map_id, x=x, y=y)
    game.player = Player.new_game(1)
    return game, scene


def open_menu(game) -> MenuScene:
    """按 menu 键打开菜单，返回菜单场景。"""
    press(game, "menu")
    scene = game.scenes.current
    assert isinstance(scene, MenuScene)
    return scene


class MenuTestBase(unittest.TestCase):
    """菜单用例的公共设置。

    把存档路径挪到临时目录：任何用例都不会写坏仓库里的 saves/save1.json。
    """

    def setUp(self):
        helpers.ensure_init()
        self.tmp = tempfile.TemporaryDirectory()
        self.old_path = save_io.SAVE_PATH
        save_io.SAVE_PATH = os.path.join(self.tmp.name, "save1.json")

    def tearDown(self):
        save_io.SAVE_PATH = self.old_path
        self.tmp.cleanup()


class MenuPushPopTest(MenuTestBase):
    """菜单必须用 push：关掉之后地图状态一点都不能变。"""

    def test_menu_pushes_and_pops(self):
        game, scene = make_game(map_id=2)
        self.assertEqual(len(game.scenes), 1)

        open_menu(game)
        self.assertEqual(len(game.scenes), 2)
        self.assertIs(game.scenes.stack[0], scene)

        press(game, "cancel")
        self.assertEqual(len(game.scenes), 1)
        self.assertIs(game.scenes.current, scene)

    def test_field_state_is_untouched_after_menu(self):
        game, scene = make_game(map_id=2)

        # 野外 2 的自然刷怪（已达上限，重开地图时不会补新怪）
        states = wild_state_of(game)
        before_state = states[2]
        before_count = len(scene.wanderers)
        before_cell = (scene.gx, scene.gy)
        before_facing = scene.facing
        self.assertGreater(before_count, 0)

        open_menu(game)
        press(game, "cancel")

        self.assertEqual(len(game.scenes), 1)
        self.assertEqual((scene.gx, scene.gy), before_cell)
        self.assertEqual(scene.facing, before_facing)
        self.assertIs(wild_state_of(game)[2], before_state)
        self.assertEqual(len(scene.wanderers), before_count)

    def test_closing_with_return_item_also_pops(self):
        game, scene = make_game()
        menu = open_menu(game)
        for _ in range(ITEM_BACK):          # 精灵 -> 道具 -> 存档 -> 返回
            press(game, "down")
        self.assertEqual(menu.main_index, ITEM_BACK)
        press(game, "confirm")
        self.assertEqual(len(game.scenes), 1)
        self.assertIs(game.scenes.current, scene)


class MenuPartyTest(MenuTestBase):
    """队伍列表与调换顺序。"""

    def test_party_list_shows_creatures(self):
        game, _ = make_game()
        game.player.party.append(Creature(2, level=5))
        menu = open_menu(game)
        press(game, "confirm")       # 精灵
        self.assertEqual(menu.mode, "party")
        labels = [it["label"] for it in menu.party_menu.items]
        self.assertTrue(labels[0].startswith("1. "))
        self.assertIn("小火狮", labels[0])
        self.assertIn("Lv5", labels[0])
        self.assertTrue(labels[1].startswith("2. "))

    def test_swap_two_creatures_changes_order(self):
        game, _ = make_game()
        game.player.party.append(Creature(2, level=5))
        first = game.player.party[0]
        second = game.player.party[1]

        menu = open_menu(game)
        press(game, "confirm")       # 进队伍列表
        press(game, "confirm")       # 选中第 1 只 -> 等待交换
        self.assertEqual(menu.swap_from, 0)
        press(game, "down")
        press(game, "confirm")       # 选第 2 只 -> 交换

        self.assertIsNone(menu.swap_from)
        self.assertIs(game.player.party[0], second)
        self.assertIs(game.player.party[1], first)

    def test_swap_with_itself_is_cancelled(self):
        game, _ = make_game()
        menu = open_menu(game)
        press(game, "confirm")
        press(game, "confirm")
        press(game, "confirm")       # 又选同一只 -> 取消
        self.assertIsNone(menu.swap_from)


class MenuItemTest(MenuTestBase):
    """背包与道具使用。"""

    def setUp(self):
        super().setUp()
        self.game, _ = make_game()
        self.game.player.bag[REVIVE_ID] = 1

    def test_potion_heals_30_hp_without_overflow(self):
        creature = self.game.player.party[0]
        creature.hp = 4
        before = self.game.player.item_count(POTION_ID)

        menu = MenuScene(self.game)
        msg = menu.use_item(POTION_ID, 0)

        self.assertEqual(creature.hp, creature.hp_max)   # 4 + 30 超过上限 -> 夹到上限
        self.assertEqual(self.game.player.item_count(POTION_ID), before - 1)
        self.assertIn("HP", msg)

    def test_potion_heals_exactly_30_when_below_max(self):
        game = self.game
        game.player.party[0] = Creature(2, level=5)      # HP 上限 41
        creature = game.player.party[0]
        creature.hp = 1
        menu = MenuScene(game)
        menu.use_item(POTION_ID, 0)
        self.assertEqual(creature.hp, 31)                 # 1 + 30

    def test_empty_bag_gives_message_and_does_not_crash(self):
        game = self.game
        game.player.bag.clear()
        menu = MenuScene(game)
        msg = menu.use_item(POTION_ID, 0)
        self.assertIn("没有", msg)
        self.assertEqual(game.player.party[0].hp, game.player.party[0].hp_max)

    def test_revive_works_on_fainted_creature(self):
        game = self.game
        game.player.party.append(Creature(2, level=5))
        fallen = game.player.party[1]
        fallen.hp = 0
        self.assertTrue(fallen.fainted)

        menu = MenuScene(game)
        msg = menu.use_item(REVIVE_ID, 1)

        self.assertFalse(fallen.fainted)
        self.assertGreater(fallen.hp, 0)
        self.assertEqual(game.player.item_count(REVIVE_ID), 0)
        self.assertIn("复活", msg)

    def test_revive_on_living_creature_is_rejected(self):
        game = self.game
        alive = game.player.party[0]
        hp_before = alive.hp
        menu = MenuScene(game)
        msg = menu.use_item(REVIVE_ID, 0)
        self.assertEqual(msg, "现在不能使用")
        self.assertEqual(alive.hp, hp_before)
        self.assertEqual(game.player.item_count(REVIVE_ID), 1)

    def test_ball_cannot_be_used_out_of_battle(self):
        game = self.game
        menu = MenuScene(game)
        msg = menu.use_item(BALL_ID, 0)
        self.assertEqual(msg, "现在不能使用")
        self.assertEqual(game.player.item_count(BALL_ID), 5)

    def test_use_item_via_ui(self):
        """走 UI：道具 -> 选精灵 -> 确认。"""
        game = self.game
        game.player.party[0].hp = 4
        menu = open_menu(game)

        press(game, "down")        # 精灵 -> 道具
        press(game, "confirm")     # 进背包
        self.assertEqual(menu.mode, "bag")
        labels = [it["label"] for it in menu.bag_menu.items]
        self.assertIn("精灵球 x5", labels)
        self.assertIn("伤药 x2", labels)

        press(game, "down")        # 精灵球 -> 伤药
        press(game, "confirm")     # 进选精灵界面
        self.assertEqual(menu.mode, "target")
        press(game, "confirm")     # 对第 1 只使用

        self.assertEqual(menu.mode, "bag")
        self.assertEqual(game.player.party[0].hp, game.player.party[0].hp_max)
        self.assertEqual(game.player.item_count(POTION_ID), 1)

    def test_ball_in_ui_shows_cannot_use_now(self):
        game = self.game
        menu = open_menu(game)
        press(game, "down")        # 精灵 -> 道具
        press(game, "confirm")     # 进背包（光标在精灵球）
        press(game, "confirm")     # 用精灵球
        self.assertEqual(menu.mode, "bag")
        self.assertEqual(menu.message, "现在不能使用")
        self.assertEqual(game.player.item_count(BALL_ID), 5)


class MenuSaveTest(MenuTestBase):
    """存档菜单项。"""

    def test_save_item_writes_file_and_shows_message(self):
        game, _ = make_game()
        menu = open_menu(game)
        for _ in range(ITEM_SAVE):        # 精灵 -> 道具 -> 存档
            press(game, "down")
        self.assertEqual(menu.main_index, ITEM_SAVE)
        press(game, "confirm")             # 写存档

        self.assertTrue(save_io.has_save())
        self.assertEqual(menu.message, "已保存到 存档 1")
        self.assertIn("已保存", menu.message)


class MenuRobustnessTest(MenuTestBase):
    """player 为 None 时菜单不能崩。"""

    def test_menu_works_without_player(self):
        game, _ = make_game()
        game.player = None
        menu = open_menu(game)

        press(game, "confirm")     # 精灵（空队伍）
        self.assertEqual(menu.mode, "party")
        press(game, "cancel")      # 回主菜单
        press(game, "down")        # 精灵 -> 道具
        press(game, "confirm")     # 道具（空背包）
        self.assertEqual(menu.mode, "bag")
        press(game, "cancel")      # 回主菜单
        press(game, "cancel")      # 关闭菜单

        helpers.run_frames(game.update, game.draw, 3)
        self.assertEqual(len(game.scenes), 1)

    def test_game_without_player_runs_frames(self):
        game = Game()
        self.assertIsNone(game.player)
        helpers.run_frames(game.update, game.draw, 5)


if __name__ == "__main__":
    unittest.main()
