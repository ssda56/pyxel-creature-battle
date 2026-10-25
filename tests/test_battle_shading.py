"""战斗画面的抖动阴影测试（A3 绘制层立体感）。

被测的两块：

- **脚下投影**：密度向外衰减的抖动椭圆（色 3 外圈 + 色 5 核心）；
- **右下侧暗化**：精灵图轮廓朝右下那一侧压暗（返回新图，原图不动）。

铁律
----
- **只影响绘制**：状态机（INTRO -> COMMAND -> ...）一行都没改；
- **必须确定性**：同一画面跑两次像素完全一致（不碰 random / 时间）。
"""

from __future__ import annotations

import unittest

import pyxel

from src.assets_gen import palette, sprite_base
from src.scenes import battle_scene as bs
from src.ui import dither
from tests import battle_helpers as bh
from tests import helpers


class DitherToolTest(unittest.TestCase):
    """src/ui/dither.py：拜耳矩阵、抖动椭圆。"""

    def setUp(self):
        helpers.ensure_init()

    def test_bayer_threshold_is_deterministic(self):
        """同一个坐标永远得到同一个阈值（不碰 random / 时间）。"""
        first = [dither.bayer_threshold(x, y) for y in range(8) for x in range(8)]
        second = [dither.bayer_threshold(x, y) for y in range(8) for x in range(8)]
        self.assertEqual(first, second)
        self.assertTrue(all(0.0 <= v < 1.0 for v in first))

    def test_bayer_matrix_is_complete(self):
        """4x4 拜耳矩阵里 0~15 每个值恰好出现一次。"""
        flat = [v for row in dither.BAYER_4X4 for v in row]
        self.assertEqual(sorted(flat), list(range(16)))

    def test_dither_ellipse_is_deterministic(self):
        """同一位置画两次，像素完全一样。"""
        pyxel.cls(palette.GREEN)
        dither.dither_ellipse(40, 40, 12, 5, palette.DARK_PURPLE)
        first = [pyxel.pget(x, y) for y in range(30, 50) for x in range(25, 55)]
        pyxel.cls(palette.GREEN)
        dither.dither_ellipse(40, 40, 12, 5, palette.DARK_PURPLE)
        second = [pyxel.pget(x, y) for y in range(30, 50) for x in range(25, 55)]
        self.assertEqual(first, second)

    def test_dither_ellipse_leaves_center_denser_than_edge(self):
        """中心比边缘密（密度向外衰减）。"""
        pyxel.cls(palette.GREEN)
        dither.dither_ellipse(40, 40, 12, 6, palette.DARK_PURPLE)
        center = sum(1 for y in range(37, 44) for x in range(37, 44)
                     if pyxel.pget(x, y) == palette.DARK_PURPLE)
        edge = sum(1 for y in range(33, 48) for x in range(27, 54)
                   if pyxel.pget(x, y) == palette.DARK_PURPLE)
        self.assertGreater(center, 0)
        self.assertGreater(edge, center)

    def test_dither_ellipse_zero_radius_draws_nothing(self):
        pyxel.cls(palette.GREEN)
        dither.dither_ellipse(40, 40, 0, 5, palette.DARK_PURPLE)
        dither.dither_ellipse(40, 40, 5, 0, palette.DARK_PURPLE)
        self.assertEqual(pyxel.pget(40, 40), palette.GREEN)


class ShadeLowerRightTest(unittest.TestCase):
    """右下侧暗化。"""

    def setUp(self):
        helpers.ensure_init()

    def test_original_image_is_not_modified(self):
        """**原图一个像素都不能动**（sprite_base 里是全局共享的）。"""
        img = sprite_base.get("creature_3_battle")
        before = [img.pget(x, y) for y in range(32) for x in range(32)]
        dither.shade_lower_right(img)
        after = [img.pget(x, y) for y in range(32) for x in range(32)]
        self.assertEqual(before, after)

    def test_shaded_image_keeps_transparency(self):
        """色 0 是透明键，暗化后仍然是 0（绝不变成可见色）。"""
        img = sprite_base.get("creature_3_battle")
        shaded = dither.shade_lower_right(img)
        for y in range(32):
            for x in range(32):
                if img.pget(x, y) == 0:
                    self.assertEqual(shaded.pget(x, y), 0)

    def test_shaded_image_changes_some_pixels(self):
        """确实压暗了一些像素（不是没生效）。"""
        img = sprite_base.get("creature_3_battle")
        shaded = dither.shade_lower_right(img)
        changed = sum(1 for y in range(32) for x in range(32)
                      if img.pget(x, y) != shaded.pget(x, y))
        self.assertGreater(changed, 20)
        # 但也不能把整只精灵都糊掉
        self.assertLess(changed, 32 * 32 // 2)

    def test_shading_direction_on_a_synthetic_square(self):
        """方向性精确验证：造一个实心方块，只有**右边和下边**被压暗。

        9x9 的图，中间 7x7 实心（x/y = 1..7）：

        - x=7 是最外圈（run=1）-> 跳过；
        - x=6 往右很快到边（run=2）-> 属于右下侧 -> 压暗；
        - x=1 是左外侧（往左 1 步就到边）-> 迎光面 -> 不动；
        - y 同理。
        """
        img = pyxel.Image(9, 9)
        for y in range(1, 8):
            for x in range(1, 8):
                img.pset(x, y, palette.ORANGE)
        shaded = dither.shade_lower_right(img)

        # 左上角 4x4：迎光面，一个像素都不该动
        for y in range(1, 5):
            for x in range(1, 5):
                self.assertEqual(shaded.pget(x, y), palette.ORANGE,
                                 f"左上角 ({x},{y}) 不该暗化")

        # 右下角：背光面，必须被压暗
        self.assertNotEqual(shaded.pget(6, 6), palette.ORANGE, "右下角没暗化")
        right = sum(1 for y in range(1, 8)
                    if shaded.pget(6, y) != palette.ORANGE)
        bottom = sum(1 for x in range(1, 8)
                     if shaded.pget(x, 6) != palette.ORANGE)
        self.assertGreater(right, 0, "右边（背光侧）没有被压暗")
        self.assertGreater(bottom, 0, "下边（背光侧）没有被压暗")

    def test_shading_concentrates_on_lower_right(self):
        """真实精灵：改动像素集中在**右下象限**（左上只是零星）。"""
        img = sprite_base.get("creature_3_battle")
        shaded = dither.shade_lower_right(img)
        quad = {"TL": 0, "TR": 0, "BL": 0, "BR": 0}
        for y in range(32):
            for x in range(32):
                if img.pget(x, y) != shaded.pget(x, y):
                    key = ("T" if y < 16 else "B") + ("L" if x < 16 else "R")
                    quad[key] += 1
        self.assertGreater(quad["BR"], quad["TL"],
                           f"右下应该比左上暗得多，实际 {quad}")
        self.assertGreater(quad["BR"], quad["BL"], f"实际 {quad}")

    def test_shading_is_deterministic(self):
        """同一张图暗化两次结果完全一致。"""
        img = sprite_base.get("creature_1_battle")
        a = dither.shade_lower_right(img)
        b = dither.shade_lower_right(img)
        self.assertEqual([a.pget(x, y) for y in range(32) for x in range(32)],
                         [b.pget(x, y) for y in range(32) for x in range(32)])

    def test_darken_map_only_uses_palette_colors(self):
        """暗化表里的颜色都必须是合法调色板索引（0~15）。"""
        for src, dst in dither.DARKEN_MAP.items():
            self.assertTrue(0 <= int(src) <= 15)
            self.assertTrue(0 <= int(dst) <= 15)
            self.assertNotEqual(int(src), 0, "色 0 是透明键，不能当可见色")
            self.assertNotEqual(int(dst), 0, "色 0 是透明键，不能当可见色")


class FootprintTest(unittest.TestCase):
    """落脚点计算。"""

    def setUp(self):
        helpers.ensure_init()

    def test_footprint_ignores_tail_tip_rows(self):
        """9 雾尾狐最底一行只有 1 个像素（尾巴尖），落脚点不能落在那。"""
        img = sprite_base.get("creature_9_battle")
        info = dither.footprint(img)
        self.assertIsNotNone(info)
        cx, ground, width = info
        self.assertGreaterEqual(width, 6)
        self.assertLessEqual(ground, 30)

    def test_footprint_exists_for_every_creature(self):
        """18 只精灵都能算出落脚点。"""
        from src.data import species_data as sd
        for sid in sorted(sd.SPECIES):
            img = sprite_base.get(f"creature_{sid}_battle")
            info = dither.footprint(img)
            self.assertIsNotNone(info, f"{sid} 号精灵算不出落脚点")
            cx, ground, width = info
            self.assertTrue(0 <= cx <= 31)
            self.assertTrue(0 <= ground <= 31)
            self.assertGreaterEqual(width, 1)


class BattleShadingTest(unittest.TestCase):
    """战斗场景里的阴影（纯绘制层）。"""

    def setUp(self):
        helpers.ensure_init()

    def test_state_machine_is_untouched_by_shading(self):
        """加了阴影之后状态机流转完全不变。"""
        game, scene, enemy = bh.make_battle()
        self.assertEqual(scene.state, bs.BattleScene.INTRO)
        bh.press(game, "confirm")
        self.assertEqual(scene.state, bs.BattleScene.COMMAND)
        bh.press(game, "confirm")
        self.assertEqual(scene.state, bs.BattleScene.SKILL_SELECT)

    def test_shadow_is_drawn_on_screen(self):
        """画面上确实多出了影子像素（脚下有深色）。"""
        game, scene, enemy = bh.make_battle(enemy_species=3)
        for _ in range(20):
            game.update()
            game.draw()
        # 敌方脚下那块（站台中间）应该有深色像素
        found = False
        for y in range(45, 62):
            for x in range(150, 190):
                if pyxel.pget(x, y) in (palette.DARK_PURPLE, palette.DARK_GREEN):
                    found = True
        self.assertTrue(found, "脚下没有画出影子")

    def test_two_runs_are_pixel_identical(self):
        """**确定性**：同一场景跑两次，画面像素完全一致。"""
        def render():
            game, scene, enemy = bh.make_battle(enemy_species=3)
            for _ in range(25):
                game.update()
                game.draw()
            return [pyxel.pget(x, y) for y in range(216) for x in range(240)]

        self.assertEqual(render(), render())

    def test_shading_does_not_change_creature_hp(self):
        """阴影是纯绘制，不能碰任何数值。"""
        game, scene, enemy = bh.make_battle(enemy_species=3)
        hp = enemy.hp
        for _ in range(20):
            game.update()
            game.draw()
        self.assertEqual(enemy.hp, hp)

    def test_shadow_follows_intro_animation(self):
        """影子跟着精灵一起滑入（不留在原地）。"""
        game, scene, enemy = bh.make_battle(enemy_species=3)
        ox, oy = scene.platform_offset("enemy")
        self.assertNotEqual((ox, oy), (0, 0))
        for _ in range(20):
            game.update()
            game.draw()
        self.assertEqual(scene.platform_offset("enemy"), (0, 0))


if __name__ == "__main__":
    unittest.main()
