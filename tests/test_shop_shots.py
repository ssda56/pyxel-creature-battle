"""批 3 商店 / 治疗截图（docs/shots/batch3_shop_buy.png 等三张）。

- batch3_shop_buy.png  买入列表（每行有买入价与持有数，金币不够的行置灰）；
- batch3_shop_sell.png 卖出列表（只列持有数量 > 0 的道具）；
- batch3_heal.png      治疗演出的**闪光**画面（整屏棋盘白闪 + 治疗中提示条）。
"""

from __future__ import annotations

import os
import unittest

import pyxel

from src.assets_gen import palette
from src.core.input import FakeInput
from src.data import map_data
from src.model.creature import Creature
from src.model.player import Player
from src.scenes.shop_scene import ShopScene
from tests import field_helpers
from tests import helpers

#: 截图输出目录
SHOTS_DIR = os.path.join(helpers.PROJECT_ROOT, "docs", "shots")

#: 护士（精灵中心）位置 / 玩家站位
NURSE_FRONT = (10, 9)


def tap(game, action: str) -> None:
    """注入**一次**按键（只跑一帧）。"""
    game.input = FakeInput(script=[{action: 1}])
    game.update()


def shot_path(name: str) -> str:
    """docs/shots 下的截图路径。"""
    return os.path.join(SHOTS_DIR, name)


def count_pixels(color: int) -> int:
    """数一下当前画面里有多少个指定颜色的像素。"""
    total = 0
    for y in range(helpers.SCREEN_HEIGHT):
        for x in range(helpers.SCREEN_WIDTH):
            if pyxel.screen.pget(x, y) == color:
                total += 1
    return total


class ShopShotTest(unittest.TestCase):
    """三张截图。"""

    def setUp(self):
        helpers.ensure_init()

    def _game(self):
        game, scene = field_helpers.make_field(map_id=1)
        game.player = Player.new_game(1)
        game.player.bag = {1: 5, 2: 2, 4: 1}
        return game, scene

    def _shop(self, game):
        npc = [n for n in map_data.MAPS[1]["npcs"] if n["kind"] == "shop"][0]
        shop = ShopScene(game, npc)
        game.scenes.push(shop)
        return shop

    def _shoot(self, game, name: str) -> str:
        path = shot_path(name)
        helpers.run_frames(game.update, game.draw, 2, shot_path=path, scale=2)
        self.assertTrue(os.path.exists(path), f"{name} 没有生成")
        self.assertEqual(helpers.png_size(path), (480, 432))
        return path

    # ------------------------------------------------------------ 买入
    def test_shot_shop_buy(self):
        """买入列表：每行有买入价与持有数；金币不够的行置灰。"""
        game, _ = self._game()
        game.player.dollars = 200          # 复活草 300 -> 买不动（置灰）
        shop = self._shop(game)
        tap(game, "confirm")               # 主菜单 -> 买入
        self.assertEqual(shop.mode, "buy")

        self._shoot(game, "batch3_shop_buy.png")

    # ------------------------------------------------------------ 卖出
    def test_shot_shop_sell(self):
        """卖出列表：只列持有数量 > 0 的道具。"""
        game, _ = self._game()
        game.player.bag = {1: 5, 2: 2, 4: 1}
        shop = self._shop(game)
        tap(game, "down")
        tap(game, "confirm")               # 主菜单 -> 卖出
        self.assertEqual(shop.mode, "sell")
        self.assertEqual(shop.sell_ids(), [1, 2, 4])

        self._shoot(game, "batch3_shop_sell.png")

    # ------------------------------------------------------------ 治疗
    def test_shot_heal_flash(self):
        """治疗演出：画面上有明显的整屏闪光。"""
        game, scene = field_helpers.make_field(
            map_id=1, x=NURSE_FRONT[0], y=NURSE_FRONT[1], facing="up")
        player = Player.new_game(1)
        player.party[0].hp = 0             # 倒下
        player.party[0].mp = 0
        player.party.append(Creature(2, level=6, hp=3, mp=1))
        game.player = player

        tap(game, "confirm")               # 打开对话
        tap(game, "confirm")               # 翻页
        tap(game, "confirm")               # 读完 -> 开始治疗演出
        self.assertGreater(scene.heal_timer, 0)

        # 跑一帧后截图：此刻正在闪光
        path = shot_path("batch3_heal.png")
        helpers.run_frames(game.update, game.draw, 1, shot_path=path, scale=2)
        self.assertTrue(os.path.exists(path))
        self.assertEqual(helpers.png_size(path), (480, 432))

        # 闪光 = 整屏棋盘格白块，白像素应该非常多
        white = count_pixels(palette.WHITE)
        self.assertGreater(white, 5000,
                           f"画面里白色像素只有 {white} 个，看不出闪光")

    # ------------------------------------------------------------ 三张都在
    def test_zz_all_three_screenshots_exist(self):
        """放在最后跑：上面几个用例已经把三张图生成好了。"""
        for name in ("batch3_shop_buy.png", "batch3_shop_sell.png",
                     "batch3_heal.png"):
            path = shot_path(name)
            self.assertTrue(os.path.exists(path), f"{name} 不存在")
            self.assertGreater(os.path.getsize(path), 1000)


if __name__ == "__main__":
    unittest.main()
