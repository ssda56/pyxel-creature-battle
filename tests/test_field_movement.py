"""地图移动测试（src/scenes/field_scene.py）。

覆盖：
- 走一格正好 20 帧（第 19 帧还没落格，第 20 帧落格）；
- 移动是像素级插值（不是瞬移）；
- 撞墙不动，但朝向会变；
- 越界不动；
- 按住方向键连续走两格。
"""

from __future__ import annotations

import unittest

from src.data import map_data
from src.scenes.field_scene import STEP_FRAMES
from tests import field_helpers


class StepTimingTest(unittest.TestCase):
    """一格 20 帧。"""

    def test_one_tile_takes_exactly_20_frames(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"right": 60}], x=15, y=10)
        self.assertEqual((scene.gx, scene.gy), (15, 10))

        field_helpers.run(game, STEP_FRAMES - 1)
        # 第 19 帧：还在路上，没落格
        self.assertEqual(scene.gx, 15)
        self.assertTrue(scene.moving)

        field_helpers.run(game, 1)
        # 第 20 帧：正好落格
        self.assertEqual(scene.gx, 16)
        self.assertEqual(scene.gy, 10)

    def test_movement_is_pixel_smooth(self):
        """走的过程中像素坐标是连续插值的，不是瞬移。"""
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"right": 60}], x=15, y=10)
        start_px = scene.px

        field_helpers.run(game, STEP_FRAMES // 2)
        self.assertGreater(scene.px, start_px)      # 已经动了一点
        self.assertLess(scene.px, start_px + 16)    # 但还没走完一格
        self.assertEqual(scene.gx, 15)              # 格坐标还没变

        field_helpers.run(game, STEP_FRAMES // 2)
        # 正好走完一格（并已开始下一格）
        self.assertEqual(scene.gx, 16)
        self.assertGreaterEqual(scene.px, start_px + 16)
        self.assertLess(scene.px, start_px + 32)

    def test_hold_direction_walks_two_tiles(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"right": 60}], x=15, y=10)
        field_helpers.run(game, STEP_FRAMES * 2)
        self.assertEqual(scene.gx, 17)
        self.assertEqual(scene.gy, 10)

    def test_walk_animation_switches_frame(self):
        """移动中每 20 帧切一帧；静止时用帧 0。"""
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"right": 60}], x=15, y=10)
        field_helpers.run(game, STEP_FRAMES * 2 - 2)
        self.assertEqual(scene.anim, 1)
        # 再跑 60 帧（= 原来的 30 帧 @30fps，同样是 1 秒）：
        # 脚本（按住 right 共 60 帧）用完、当前这一步也走完 -> 玩家真的停下
        field_helpers.run(game, 60)
        self.assertFalse(scene.moving, "脚本用完后玩家应该停下")
        self.assertEqual(scene.anim, 0)   # 停下后回到站立帧


class CollisionTest(unittest.TestCase):
    """碰撞与越界。"""

    def test_wall_blocks_movement_but_changes_facing(self):
        """面向房屋墙：位置不动，朝向变成 up。"""
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"up": 30}], x=7, y=8, facing="down")
        # (7,7) 是房屋墙
        self.assertEqual(map_data.tile_at(1, 7, 7), 5)

        field_helpers.run(game, 20)
        self.assertEqual((scene.gx, scene.gy), (7, 8))
        self.assertEqual(scene.facing, "up")

    def test_door_is_walkable(self):
        """门（6）可走：面向门能走进去。"""
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"up": 30}], x=9, y=8, facing="down")
        self.assertEqual(map_data.tile_at(1, 9, 7), 6)

        field_helpers.run(game, STEP_FRAMES)
        self.assertEqual((scene.gx, scene.gy), (9, 7))

    def test_map_border_blocks_movement(self):
        """边界是树：撞边界不动。"""
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"left": 30}], x=1, y=10, facing="right")
        self.assertEqual(map_data.tile_at(1, 0, 10), 2)

        field_helpers.run(game, 20)
        self.assertEqual((scene.gx, scene.gy), (1, 10))

    def test_out_of_bounds_is_not_walkable(self):
        """越界格一律不可走。"""
        self.assertFalse(map_data.is_walkable(1, -1, 0))
        self.assertFalse(map_data.is_walkable(1, 0, -1))
        self.assertFalse(map_data.is_walkable(1, 30, 0))
        self.assertFalse(map_data.is_walkable(1, 0, 20))
        self.assertFalse(map_data.is_walkable(2, 40, 0))
        self.assertFalse(map_data.is_walkable(2, 0, 30))

    def test_water_and_tree_block(self):
        """水（3）/ 树（2）不可走。"""
        self.assertFalse(map_data.is_walkable(2, 27, 6))   # 湖面
        self.assertFalse(map_data.is_walkable(2, 20, 3))   # 树

    def test_facing_changes_when_blocked(self):
        """(11,8) 上方是房屋墙：撞墙不动，但朝向变成 up。"""
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"up": 30}], x=11, y=8, facing="down")
        self.assertEqual(map_data.tile_at(1, 11, 7), 5)
        field_helpers.run(game, 20)
        self.assertEqual(scene.facing, "up")
        self.assertEqual((scene.gx, scene.gy), (11, 8))


class StateSyncTest(unittest.TestCase):
    """位置写回 player_state（存档系统要用）。"""

    def test_player_state_is_updated(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"right": 60}], x=15, y=10)
        field_helpers.run(game, STEP_FRAMES)
        self.assertEqual(game.player_state["map_id"], 1)
        self.assertEqual(game.player_state["x"], 16)
        self.assertEqual(game.player_state["y"], 10)
        self.assertEqual(game.player_state["facing"], "right")
        self.assertEqual(game.player_state["dollars"], 300)


if __name__ == "__main__":
    unittest.main()
