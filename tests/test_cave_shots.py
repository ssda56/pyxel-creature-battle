"""批 6 洞窟截图（批 6 / T8a）。

产出四张图，方便肉眼核对：

- `batch6_cave.png`          洞窟入口洞室实景：洞窟地面、岩壁、传送阵 + 野生精灵图标
- `batch6_cave_deep.png`     洞窟最深处洞室：能看到**不死鸟**的图标
- `batch6_cave_entrance.png` 野外东南高地上的传送阵（从 map2 看）
- `batch6_cave_battle.png`   与洞窟精灵（三头犬）的战斗第一帧
"""

from __future__ import annotations

import os
import unittest

from src.data import map_data
from src.scenes.battle_scene import BattleScene
from tests import field_helpers, helpers

CAVE_SHOT = field_helpers.shot_path("batch6_cave.png")
CAVE_DEEP_SHOT = field_helpers.shot_path("batch6_cave_deep.png")
CAVE_ENTRANCE_SHOT = field_helpers.shot_path("batch6_cave_entrance.png")
CAVE_BATTLE_SHOT = field_helpers.shot_path("batch6_cave_battle.png")

#: 洞窟地图 ID
CAVE_MAP = 3

#: 野外地图 ID
FIELD_MAP = 2


def _wanderer(species_id: int, level: int, gx: int, gy: int,
              spawn_index: int = 0) -> dict:
    """造一只野生精灵状态（形状和 _spawn_wanderer 造出来的一样）。"""
    return {
        "species_id": int(species_id),
        "level": int(level),
        "gx": int(gx),
        "gy": int(gy),
        "alive": True,
        "move_timer": 99999,      # 截图前不要游走
        "spawn_index": int(spawn_index),
    }


class CaveShotTest(unittest.TestCase):
    """无窗口跑几帧并截图。"""

    def setUp(self):
        helpers.ensure_init()

    def _check(self, path: str) -> None:
        self.assertTrue(os.path.exists(path), "截图没有生成：" + path)
        self.assertGreater(os.path.getsize(path), 1000)
        self.assertEqual(helpers.png_size(path), (480, 432))

    def test_cave_screenshot(self):
        """洞窟入口洞室：地面 / 岩壁 / 传送阵 / 野生精灵图标。"""
        game, scene = field_helpers.make_field(map_id=CAVE_MAP, x=5, y=21,
                                               facing="right", seed=1)
        wanderers = scene.wild_state["wanderers"]
        wanderers.clear()
        wanderers.append(_wanderer(6, 10, 7, 21))     # 三头犬
        wanderers.append(_wanderer(5, 11, 4, 24))     # 独角兽
        helpers.run_frames(game.update, game.draw, 4,
                           shot_path=CAVE_SHOT, scale=2)
        self._check(CAVE_SHOT)

    def test_cave_deep_screenshot(self):
        """最深处洞室：能看到不死鸟的图标。"""
        game, scene = field_helpers.make_field(map_id=CAVE_MAP, x=29, y=4,
                                               facing="right", seed=2)
        wanderers = scene.wild_state["wanderers"]
        wanderers.clear()
        wanderers.append(_wanderer(7, 16, 32, 3))     # 不死鸟
        wanderers.append(_wanderer(7, 17, 29, 6))     # 不死鸟
        helpers.run_frames(game.update, game.draw, 4,
                           shot_path=CAVE_DEEP_SHOT, scale=2)
        self._check(CAVE_DEEP_SHOT)

    def test_cave_entrance_screenshot(self):
        """野外东南高地上的传送阵（站在旁边一格，整个法阵看得见）。"""
        portal = [p for p in map_data.MAPS[FIELD_MAP]["portals"]
                  if p["to_map"] == CAVE_MAP][0]
        game, scene = field_helpers.make_field(
            map_id=FIELD_MAP, x=portal["x"] - 1, y=portal["y"] + 1,
            facing="up", seed=3)
        self.assertEqual((scene.gx, scene.gy), (portal["x"] - 1,
                                                portal["y"] + 1))
        helpers.run_frames(game.update, game.draw, 4,
                           shot_path=CAVE_ENTRANCE_SHOT, scale=2)
        self._check(CAVE_ENTRANCE_SHOT)

    def test_cave_battle_screenshot(self):
        """与洞窟三头犬的战斗第一帧。"""
        from src.model import Player

        game, scene = field_helpers.make_field(map_id=CAVE_MAP, x=5, y=21, seed=4)
        game.player = Player.new_game(1)
        wanderers = scene.wild_state["wanderers"]
        wanderers.clear()
        wanderers.append(_wanderer(6, 10, 5, 21))     # 三头犬踩在玩家格上
        helpers.run_frames(game.update, game.draw, 1)
        self.assertIsInstance(game.scenes.current, BattleScene)
        self.assertEqual(game.scenes.current.enemy.species_id, 6)
        helpers.run_frames(game.update, game.draw, 1,
                           shot_path=CAVE_BATTLE_SHOT, scale=2)
        self._check(CAVE_BATTLE_SHOT)


if __name__ == "__main__":
    unittest.main()
