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
from src.scenes.menu_scene import (
    MODE_BAG,
    MODE_MAIN,
    MODE_PARTY,
    MODE_STORAGE,
    MAIN_ITEMS,
    MenuScene,
)
from tests import field_helpers
from tests import helpers

#: 道具 ID（《数值设定.md》§7.1）
BALL_ID = 1
POTION_ID = 2
BLUE_POTION_ID = 4
REVIVE_ID = 5

#: 主菜单五项的顺序（src.scenes.menu_scene.MAIN_ITEMS）
ITEM_PARTY = 0
ITEM_STORAGE = 1
ITEM_BAG = 2
ITEM_SAVE = 3
ITEM_BACK = 4


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

        press(game, "down")        # 精灵 -> 仓库
        press(game, "down")        # 仓库 -> 道具
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
        press(game, "down")        # 精灵 -> 仓库
        press(game, "down")        # 仓库 -> 道具
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


class MenuMainItemsTest(MenuTestBase):
    """主菜单五项：顺序与光标移动。"""

    def test_main_menu_has_five_items_in_order(self):
        self.assertEqual(len(MAIN_ITEMS), 5)
        self.assertEqual(MAIN_ITEMS, ("精灵", "仓库", "道具", "存档", "返回"))

    def test_menu_shows_five_items(self):
        game, _ = make_game()
        menu = open_menu(game)
        labels = [it["label"] for it in menu.main_menu.items]
        self.assertEqual(labels, ["精灵", "仓库", "道具", "存档", "返回"])

    def test_cursor_moves_through_all_five_items(self):
        game, _ = make_game()
        menu = open_menu(game)
        self.assertEqual(menu.main_index, ITEM_PARTY)
        for expect in (ITEM_STORAGE, ITEM_BAG, ITEM_SAVE, ITEM_BACK):
            press(game, "down")
            self.assertEqual(menu.main_index, expect)

    def test_cursor_wraps_around(self):
        """5 项之间上下移动是循环的（第一项的上面是最后一项）。"""
        game, _ = make_game()
        menu = open_menu(game)
        press(game, "up")
        self.assertEqual(menu.main_index, ITEM_BACK)
        press(game, "down")
        self.assertEqual(menu.main_index, ITEM_PARTY)
        press(game, "down")
        press(game, "down")
        press(game, "down")
        press(game, "down")
        self.assertEqual(menu.main_index, ITEM_BACK)
        press(game, "down")
        self.assertEqual(menu.main_index, ITEM_PARTY)

    def test_storage_item_opens_storage_mode(self):
        game, _ = make_game()
        menu = open_menu(game)
        press(game, "down")            # 精灵 -> 仓库
        press(game, "confirm")
        self.assertEqual(menu.mode, MODE_STORAGE)

    def test_cancel_from_storage_returns_to_main(self):
        game, _ = make_game()
        menu = open_menu(game)
        press(game, "down")
        press(game, "confirm")         # 进仓库
        self.assertEqual(menu.mode, MODE_STORAGE)
        press(game, "cancel")
        self.assertEqual(menu.mode, MODE_MAIN)


class MenuStorageExchangeTest(MenuTestBase):
    """仓库界面：队伍 <-> 仓库 互换。"""

    def _game_with(self, party_size: int = 1, storage_size: int = 0):
        """造一个队伍 party_size 只、仓库 storage_size 只的游戏。"""
        game, _ = make_game()
        while len(game.player.party) < party_size:
            game.player.party.append(Creature(2, level=5))
        while len(game.player.storage) < storage_size:
            game.player.storage.append(Creature(3, level=4))
        return game

    def _open_storage(self, game):
        """打开菜单 -> 进仓库界面。"""
        menu = open_menu(game)
        press(game, "down")            # 精灵 -> 仓库
        press(game, "confirm")
        self.assertEqual(menu.mode, MODE_STORAGE)
        return menu

    def _to_storage_tab(self, game):
        """在仓库界面里切到「仓库」页签。"""
        press(game, "right")

    # ---------------------------------------------------- 仓库 -> 队伍
    def test_storage_to_party_succeeds(self):
        """队伍未满时，仓库 -> 队伍成功，两边数量正确。"""
        game = self._game_with(party_size=2, storage_size=2)
        creature = game.player.storage[0]
        menu = self._open_storage(game)

        self._to_storage_tab(game)
        press(game, "confirm")

        self.assertEqual(len(game.player.party), 3)
        self.assertEqual(len(game.player.storage), 1)
        self.assertIs(game.player.party[-1], creature)
        self.assertIn("队伍", menu.message)

    def test_storage_to_party_rejected_when_party_full(self):
        """队伍已满 6 只时，仓库 -> 队伍被拒绝，数量不变。"""
        game = self._game_with(party_size=6, storage_size=2)
        menu = self._open_storage(game)

        self._to_storage_tab(game)
        press(game, "confirm")

        self.assertEqual(len(game.player.party), 6)
        self.assertEqual(len(game.player.storage), 2)
        self.assertIn("队伍已满", menu.message)

    # ---------------------------------------------------- 队伍 -> 仓库
    def test_party_to_storage_succeeds(self):
        """队伍多于 1 只时，队伍 -> 仓库成功。"""
        game = self._game_with(party_size=3, storage_size=1)
        creature = game.player.party[1]
        menu = self._open_storage(game)

        press(game, "down")            # 选中第 2 只
        press(game, "confirm")

        self.assertEqual(len(game.player.party), 2)
        self.assertEqual(len(game.player.storage), 2)
        self.assertIs(game.player.storage[-1], creature)
        self.assertIn("仓库", menu.message)

    def test_party_to_storage_rejected_when_only_one_left(self):
        """队伍只剩 1 只时，队伍 -> 仓库被拒绝，数量不变。"""
        game = self._game_with(party_size=1, storage_size=2)
        menu = self._open_storage(game)

        press(game, "confirm")

        self.assertEqual(len(game.player.party), 1)
        self.assertEqual(len(game.player.storage), 2)
        self.assertIn("至少要保留一只", menu.message)

    # ---------------------------------------------------- 空状态
    def test_empty_storage_tab_does_not_crash(self):
        """仓库为空时进仓库页签不崩溃，有提示。"""
        game = self._game_with(party_size=1, storage_size=0)
        menu = self._open_storage(game)

        self._to_storage_tab(game)
        press(game, "confirm")

        self.assertIn("空", menu.message)
        helpers.run_frames(game.update, game.draw, 3)   # 画几帧也不崩

    def test_empty_party_tab_does_not_crash(self):
        """队伍为空时进队伍页签不崩溃。"""
        game = self._game_with(party_size=1, storage_size=0)
        game.player.party.clear()
        menu = self._open_storage(game)

        press(game, "confirm")

        self.assertIn("没有精灵", menu.message)
        helpers.run_frames(game.update, game.draw, 3)

    # ---------------------------------------------------- 光标边界
    def test_cursor_stays_in_range_for_empty_list(self):
        """空列表：光标不会越界。"""
        game = self._game_with(party_size=1, storage_size=0)
        menu = self._open_storage(game)

        self._to_storage_tab(game)
        for _ in range(3):
            press(game, "down")
            press(game, "up")
        self.assertEqual(menu.storage_index, 0)
        self.assertEqual(len(game.player.storage), 0)

    def test_cursor_stays_in_range_for_single_item(self):
        """只有一条时：光标始终是 0。"""
        game = self._game_with(party_size=1, storage_size=1)
        menu = self._open_storage(game)

        self._to_storage_tab(game)
        for _ in range(3):
            press(game, "down")
            self.assertEqual(menu.storage_index, 0)
            press(game, "up")
            self.assertEqual(menu.storage_index, 0)

    def test_cursor_stays_in_range_for_many_items(self):
        """多条时：光标在 0..n-1 之间移动，不会越界。"""
        game = self._game_with(party_size=1, storage_size=5)
        menu = self._open_storage(game)

        self._to_storage_tab(game)
        seen = set()
        for _ in range(12):
            press(game, "down")
            self.assertTrue(0 <= menu.storage_index < 5)
            seen.add(menu.storage_index)
        self.assertEqual(seen, {0, 1, 2, 3, 4})
        for _ in range(12):
            press(game, "up")
            self.assertTrue(0 <= menu.storage_index < 5)

    def test_cursor_clamped_after_removal(self):
        """移走最后一只后光标要夹回范围内。"""
        game = self._game_with(party_size=2, storage_size=1)
        menu = self._open_storage(game)

        press(game, "down")            # 队伍第 2 只
        press(game, "confirm")         # 移到仓库
        self.assertEqual(len(game.player.party), 1)
        self.assertTrue(0 <= menu.storage_index < 1)

    # ---------------------------------------------------- 页签切换
    def test_left_right_switch_tabs(self):
        """←→ 在两个页签之间切换。"""
        game = self._game_with(party_size=2, storage_size=2)
        menu = self._open_storage(game)

        self.assertEqual(menu.storage_tab, "party")
        press(game, "right")
        self.assertEqual(menu.storage_tab, "store")
        press(game, "left")
        self.assertEqual(menu.storage_tab, "party")

    def test_tabs_keep_separate_cursors(self):
        """两个页签各记各的光标。"""
        game = self._game_with(party_size=3, storage_size=3)
        menu = self._open_storage(game)

        press(game, "down")
        press(game, "down")            # 队伍光标 = 2
        self.assertEqual(menu.storage_index, 2)
        press(game, "right")
        self.assertEqual(menu.storage_index, 0)

    # ---------------------------------------------------- 存档往返
    def test_save_round_trip_after_exchange(self):
        """移动后存档往返：队伍与仓库内容一致。"""
        game = self._game_with(party_size=3, storage_size=2)
        menu = self._open_storage(game)

        press(game, "down")
        press(game, "confirm")         # 队伍 -> 仓库
        self._to_storage_tab(game)
        press(game, "confirm")         # 仓库 -> 队伍

        before = game.player.to_dict()
        restored = Player.from_dict(before)

        self.assertEqual(len(restored.party), len(game.player.party))
        self.assertEqual(len(restored.storage), len(game.player.storage))
        self.assertEqual([c.species_id for c in restored.party],
                         [c.species_id for c in game.player.party])
        self.assertEqual([c.species_id for c in restored.storage],
                         [c.species_id for c in game.player.storage])


class MenuRobustnessTest(MenuTestBase):
    """player 为 None 时菜单不能崩。"""

    def test_menu_works_without_player(self):
        game, _ = make_game()
        game.player = None
        menu = open_menu(game)

        press(game, "confirm")     # 精灵（空队伍）
        self.assertEqual(menu.mode, "party")
        press(game, "cancel")      # 回主菜单
        press(game, "down")        # 精灵 -> 仓库
        press(game, "down")        # 仓库 -> 道具
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
