"""商店场景测试（批 3 / T6）。

覆盖：

1. 商店入口：面对 kind="shop" 的 NPC 读完对话 -> 当前场景是 ShopScene、栈深 2；
2. 买入成功 / 金币不足；
3. 卖出成功 / 卖出列表过滤 / 没有可卖的东西；
4. 商店 push / pop：关掉后地图状态一点不变。
"""

from __future__ import annotations

import unittest

from src.core.input import FakeInput
from src.data import item_data, map_data
from src.model.player import Player
from src.scenes.shop_scene import (
    MODE_BUY,
    MODE_MAIN,
    MODE_SELL,
    NO_MONEY_TEXT,
    ShopScene,
)
from tests import field_helpers

#: 店员（商店）在新手村的位置
SHOP_NPC = (22, 8)
#: 玩家站在店员正下方、面向他时的位置
SHOP_FRONT = (22, 9)


def tap(game, action: str) -> None:
    """注入**一次**按键（只跑一帧，按键按下后立刻松开）。"""
    game.input = FakeInput(script=[{action: 1}])
    game.update()


def idle(game, frames: int = 1) -> None:
    """跑若干帧（不按任何键）。"""
    game.input = FakeInput(script=[])
    for _ in range(frames):
        game.update()


def make_game(map_id: int = 1, x=None, y=None, facing=None):
    """建一个跑在 FieldScene 上、并且已经开局的游戏。"""
    game, scene = field_helpers.make_field(map_id=map_id, x=x, y=y, facing=facing)
    game.player = Player.new_game(1)
    return game, scene


def shop_npc() -> dict:
    """地图 1 里的店员 NPC。"""
    return [n for n in map_data.MAPS[1]["npcs"] if n["kind"] == "shop"][0]


def open_shop(game) -> ShopScene:
    """直接压栈一个商店界面（不做 NPC 对话）。"""
    shop = ShopScene(game, shop_npc())
    game.scenes.push(shop)
    return shop


class ShopEntryTest(unittest.TestCase):
    """商店入口。"""

    def test_reading_dialogue_opens_shop_scene(self):
        """面对店员按确认并读完对话 -> 进入商店界面，栈深 2。"""
        game, scene = make_game(x=SHOP_FRONT[0], y=SHOP_FRONT[1], facing="up")

        tap(game, "confirm")
        self.assertIsNotNone(scene.dialogue, "面向店员按确认键应该打开对话")

        # 店员有 2 句台词：确认 -> 翻页 -> 确认 -> 读完
        tap(game, "confirm")
        self.assertIsNotNone(scene.dialogue)
        tap(game, "confirm")

        self.assertIsInstance(game.scenes.current, ShopScene)
        self.assertEqual(len(game.scenes), 2)
        # 地图场景还在栈里（压栈，不是替换）
        self.assertIs(game.scenes.stack[0], scene)
        self.assertIsNone(scene.dialogue, "读完对话后对话框应该关闭")

    def test_end_to_end_buy_through_npc(self):
        """端到端：面对店员读完对话 -> 买 1 个精灵球 -> 关商店回原地。"""
        game, scene = make_game(x=SHOP_FRONT[0], y=SHOP_FRONT[1], facing="up")

        tap(game, "confirm")       # 打开对话
        tap(game, "confirm")       # 翻页
        tap(game, "confirm")       # 读完 -> 商店界面
        shop = game.scenes.current
        self.assertIsInstance(shop, ShopScene)

        tap(game, "confirm")       # 主菜单 -> 买入
        tap(game, "confirm")       # 买精灵球
        self.assertEqual(game.player.dollars, 250)
        self.assertEqual(game.player.item_count(1), 6)

        tap(game, "cancel")        # 列表 -> 主菜单
        tap(game, "cancel")        # 主菜单 -> 关闭商店
        self.assertEqual(len(game.scenes), 1)
        self.assertIs(game.scenes.current, scene)
        self.assertEqual((scene.gx, scene.gy), SHOP_FRONT)

    def test_shop_scene_has_three_modes(self):
        game, _ = make_game()
        shop = open_shop(game)
        self.assertEqual(shop.mode, MODE_MAIN)

        tap(game, "confirm")           # 买入
        self.assertEqual(shop.mode, MODE_BUY)

        tap(game, "cancel")            # 列表 -> 主菜单
        self.assertEqual(shop.mode, MODE_MAIN)

        tap(game, "down")
        tap(game, "confirm")           # 卖出
        self.assertEqual(shop.mode, MODE_SELL)


class ShopBuyTest(unittest.TestCase):
    """买入。"""

    def test_buy_success(self):
        """金币 300 买精灵球(50) -> 金币 250、背包 +1。"""
        game, _ = make_game()
        game.player.dollars = 300
        shop = open_shop(game)

        tap(game, "confirm")           # 买入
        tap(game, "confirm")           # 买第 1 行（精灵球 50）

        self.assertEqual(game.player.dollars, 250)
        self.assertEqual(game.player.item_count(1), 6)
        self.assertEqual(game.player_state["dollars"], 250)
        self.assertIn("精灵球", shop.message)

    def test_buy_uses_item_data_price(self):
        """买入价一律取 item_data.price（场景里不硬编码）。"""
        game, _ = make_game()
        game.player.dollars = 1000
        shop = open_shop(game)
        tap(game, "confirm")           # 买入
        for _ in range(4):             # 移到第 5 行（复活草）
            tap(game, "down")
        tap(game, "confirm")
        self.assertEqual(game.player.dollars,
                         1000 - item_data.get_item(5).price)
        self.assertEqual(game.player.item_count(5), 1)

    def test_not_enough_money_does_not_buy(self):
        """金币 10 买精灵球 -> 金币与背包都不变，并提示「金币不足」。"""
        game, _ = make_game()
        game.player.dollars = 10
        shop = open_shop(game)

        tap(game, "confirm")           # 买入
        tap(game, "confirm")           # 买第 1 行（精灵球 50，买不起）

        self.assertEqual(game.player.dollars, 10)
        self.assertEqual(game.player.item_count(1), 5)
        self.assertIn(NO_MONEY_TEXT, shop.message)
        # 买不动的行整行置灰
        self.assertFalse(shop.item_menu.items[0]["enabled"])

    def test_buy_row_is_grey_when_too_expensive(self):
        """金币不够的行 enabled=False（画出来是色 5 置灰）。"""
        game, _ = make_game()
        game.player.dollars = 200
        shop = open_shop(game)
        tap(game, "confirm")           # 买入
        labels = {it["label"]: it["enabled"] for it in shop.item_menu.items}
        # 复活草 300 > 200 -> 置灰；精灵球 50 -> 可买
        self.assertFalse(labels["复活草  300 金币  持有 0"])
        self.assertTrue(labels["精灵球  50 金币  持有 5"])


class ShopSellTest(unittest.TestCase):
    """卖出。"""

    def test_sell_success(self):
        """背包精灵球 x5 -> 卖 1 个 -> 金币 +25、背包剩 4。"""
        game, _ = make_game()
        game.player.dollars = 0
        game.player.bag[1] = 5
        shop = open_shop(game)

        tap(game, "down")              # 主菜单移到「卖出」
        tap(game, "confirm")           # 卖出列表
        tap(game, "confirm")           # 卖第 1 行（精灵球）

        self.assertEqual(game.player.dollars, item_data.get_item(1).sell)
        self.assertEqual(game.player.item_count(1), 4)
        self.assertIn("精灵球", shop.message)

    def test_sell_price_is_half_of_buy_price(self):
        """卖出价 = item_data.sell（= 买入价 50%），不是场景里写死的。"""
        for item_id, item in item_data.ITEMS.items():
            self.assertEqual(item.sell, item.price // 2)

    def test_sell_list_only_shows_owned_items(self):
        """数量为 0 的道具不出现在卖出列表。"""
        game, _ = make_game()
        game.player.bag = {1: 5, 3: 1}
        shop = open_shop(game)

        tap(game, "down")
        tap(game, "confirm")

        self.assertEqual(shop.sell_ids(), [1, 3])
        labels = [it["label"] for it in shop.item_menu.items]
        self.assertEqual(len(labels), 2)
        self.assertIn("精灵球", labels[0])
        self.assertIn("好伤药", labels[1])
        self.assertFalse(any("复活草" in s for s in labels))
        self.assertFalse(any("蓝药水" in s for s in labels))

    def test_row_disappears_when_last_one_sold(self):
        """卖光之后那一行从卖出列表消失。"""
        game, _ = make_game()
        game.player.bag = {1: 1}
        shop = open_shop(game)

        tap(game, "down")
        tap(game, "confirm")
        self.assertEqual(shop.item_menu.count, 1)

        tap(game, "confirm")           # 卖掉唯一的一个
        self.assertEqual(shop.item_menu.count, 0)
        self.assertEqual(shop.sell_ids(), [])

    def test_nothing_to_sell(self):
        """背包空 -> 卖出列表为空并显示提示，确认键不崩。"""
        game, _ = make_game()
        game.player.bag = {}
        shop = open_shop(game)

        tap(game, "down")
        tap(game, "confirm")
        self.assertEqual(shop.mode, MODE_SELL)
        self.assertEqual(shop.item_menu.count, 0)

        tap(game, "confirm")           # 空列表按确认 -> 只提示，不崩
        self.assertIn("没有可以卖的东西", shop.message)
        self.assertEqual(game.player.dollars, 300)


class ShopAcceptanceTest(unittest.TestCase):
    """验收脚本：连买 / 卖光 / 边界。"""

    def test_buy_balls_until_broke(self):
        """金币 300 连买精灵球（50/个）：金币不会变负，买不动的会被拒绝。

        300 = 50 x 6，所以正好能买 6 个，第 7 个买不动
        （余额 0 < 50，提示「金币不足」，金币保持 0，不会变负）。
        """
        game, _ = make_game()
        game.player.dollars = 300
        bag_before = game.player.item_count(1)
        shop = open_shop(game)

        tap(game, "confirm")           # 买入列表
        bought = 0
        for _ in range(7):
            tap(game, "confirm")
            self.assertGreaterEqual(game.player.dollars, 0, "金币不能变负")
            if shop.message.startswith("购买了"):
                bought += 1
            else:
                self.assertIn(NO_MONEY_TEXT, shop.message)
        self.assertEqual(bought, 6)
        self.assertEqual(game.player.dollars, 0)
        self.assertEqual(game.player.item_count(1), bag_before + 6)

    def test_sell_everything(self):
        """卖光背包：金币 = 300 + 回收价总和，背包全空。"""
        game, _ = make_game()
        game.player.dollars = 300
        shop = open_shop(game)

        total = 0
        while shop.sell_ids():
            if shop.mode != MODE_SELL:
                tap(game, "down")       # 主菜单 -> 卖出
                tap(game, "confirm")
            tap(game, "confirm")       # 卖掉当前选中的那一个
            total += 1
            self.assertLessEqual(total, 20)
        self.assertEqual(total, 8)     # 5 精灵球 + 2 伤药 + 1 蓝药水

        expected = 300 + sum(
            item_data.get_item(i).sell * n
            for i, n in ((1, 5), (2, 2), (4, 1))
        )
        self.assertEqual(game.player.dollars, expected)
        self.assertTrue(all(v == 0 for v in game.player.bag.values()))
        self.assertEqual(game.player.bag, {})


class ShopStackTest(unittest.TestCase):
    """商店的压栈 / 弹栈语义。"""

    def test_close_shop_keeps_map_state(self):
        """开商店再关掉：栈深 1、坐标不变、wild_state 不变、wanderers 数量不变。"""
        game, scene = field_helpers.make_field(map_id=2)   # 野外：有野生精灵
        game.player = Player.new_game(1)

        wild_map_state = scene.wild_state
        wild_states = game.wild_state
        wanderers_before = len(wild_map_state["wanderers"])
        pos_before = (scene.gx, scene.gy)
        self.assertGreater(wanderers_before, 0, "野外应该已经刷了野生精灵")

        shop = open_shop(game)
        self.assertEqual(len(game.scenes), 2)

        tap(game, "cancel")            # 主菜单 -> 关闭商店（pop）

        self.assertEqual(len(game.scenes), 1)
        self.assertIs(game.scenes.current, scene)
        self.assertEqual((scene.gx, scene.gy), pos_before)
        self.assertIs(scene.wild_state, wild_map_state)
        self.assertIs(game.wild_state, wild_states)
        self.assertEqual(len(wild_map_state["wanderers"]), wanderers_before)

    def test_cancel_goes_list_to_main_to_close(self):
        """取消键逐级返回：列表 -> 主菜单 -> 关闭商店。"""
        game, _ = make_game()
        shop = open_shop(game)
        self.assertEqual(len(game.scenes), 2)

        tap(game, "confirm")           # 买入列表
        self.assertEqual(shop.mode, MODE_BUY)

        tap(game, "cancel")            # -> 主菜单
        self.assertEqual(shop.mode, MODE_MAIN)
        self.assertEqual(len(game.scenes), 2)

        tap(game, "cancel")            # -> 关闭商店
        self.assertEqual(len(game.scenes), 1)


if __name__ == "__main__":
    unittest.main()
