"""明雷遇敌截图（T4）。

- ``docs/shots/batch2_field_wanderers.png``：野外地图上能看到多只精灵图标；
- ``docs/shots/batch2_field_battle.png``：碰撞触发后的战斗画面第一帧。
"""

from __future__ import annotations

import os
import unittest

from src.data import map_data
from src.scenes.battle_scene import BattleScene
from tests import helpers
from tests.test_wild_encounter import FIELD_MAP, make_field, run

WANDERERS_SHOT = os.path.join(helpers.PROJECT_ROOT, "docs", "shots",
                              "batch2_field_wanderers.png")
BATTLE_SHOT = os.path.join(helpers.PROJECT_ROOT, "docs", "shots",
                            "batch2_field_battle.png")


class WildShotTest(unittest.TestCase):
    """无窗口跑一遍明雷遇敌并截图。"""

    def setUp(self):
        helpers.ensure_init()

    def test_wanderers_screenshot(self):
        """野外地图截图：草丛上有多只野生精灵图标。"""
        # 固定种子：让 3 只精灵同时落在镜头里的草丛上，方便肉眼核对
        game, scene = make_field(map_id=FIELD_MAP, seed=8, x=2, y=21)
        run(game, 4)
        self.assertTrue(scene.wanderers, "野外应该刷出精灵")
        self.assertGreaterEqual(len(scene.wanderers), 3)
        helpers.run_frames(game.update, game.draw, 2,
                           shot_path=WANDERERS_SHOT, scale=2)
        self.assertTrue(os.path.exists(WANDERERS_SHOT))
        self.assertGreater(os.path.getsize(WANDERERS_SHOT), 1000)
        self.assertEqual(helpers.png_size(WANDERERS_SHOT), (480, 432))

    def test_battle_screenshot(self):
        """碰撞触发战斗后的第一帧。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=8, x=2, y=21)
        run(game, 4)
        wanderers = scene.wanderers
        self.assertTrue(wanderers)
        target = wanderers[0]

        # 把玩家挪到精灵所在格 -> 触发明雷遇敌
        scene.gx = target["gx"]
        scene.gy = target["gy"]
        scene.px = float(scene.gx * map_data.TILE_SIZE)
        scene.py = float(scene.gy * map_data.TILE_SIZE)
        scene.sync_state()
        run(game, 1)

        self.assertIsInstance(game.scenes.current, BattleScene)
        helpers.run_frames(game.update, game.draw, 1,
                           shot_path=BATTLE_SHOT, scale=2)
        self.assertTrue(os.path.exists(BATTLE_SHOT))
        self.assertGreater(os.path.getsize(BATTLE_SHOT), 1000)
        self.assertEqual(helpers.png_size(BATTLE_SHOT), (480, 432))


if __name__ == "__main__":
    unittest.main()
