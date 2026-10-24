"""战斗 UI 小部件测试（T3b）：进度条 / 信息框 / 菜单 / 飘字。"""

from __future__ import annotations

import unittest

import pyxel

from src.assets_gen import palette
from src.ui.damage_number import (
    BLINK_FRAMES,
    CIRCLE_RADIUS,
    LIFETIME,
    RISE,
    DamageNumber,
    DamageNumberGroup,
)
from src.ui.widgets import MenuList, draw_bar, draw_status_box
from tests import helpers


class DrawBarTest(unittest.TestCase):
    """13.1：HP 条 / MP 条（比例自动夹取）。"""

    def setUp(self):
        helpers.ensure_init()
        pyxel.cls(0)

    def test_ratio_zero_shows_only_background(self):
        draw_bar(10, 10, 100, 5, 0.0, palette.RED, palette.LIGHT_GREEN)
        self.assertEqual(pyxel.pget(10, 10), palette.RED)
        self.assertEqual(pyxel.pget(60, 10), palette.RED)

    def test_ratio_one_fills_whole_bar(self):
        draw_bar(10, 10, 100, 5, 1.0, palette.RED, palette.LIGHT_GREEN)
        self.assertEqual(pyxel.pget(10, 10), palette.LIGHT_GREEN)
        self.assertEqual(pyxel.pget(109, 10), palette.LIGHT_GREEN)

    def test_half_ratio_length(self):
        draw_bar(10, 10, 100, 5, 0.5, palette.RED, palette.LIGHT_GREEN)
        self.assertEqual(pyxel.pget(10, 10), palette.LIGHT_GREEN)
        self.assertEqual(pyxel.pget(59, 10), palette.LIGHT_GREEN)
        self.assertEqual(pyxel.pget(60, 10), palette.RED)

    def test_ratio_above_one_is_clamped(self):
        draw_bar(10, 10, 100, 5, 3.0, palette.RED, palette.LIGHT_GREEN)
        self.assertEqual(pyxel.pget(60, 10), palette.LIGHT_GREEN)

    def test_ratio_below_zero_is_clamped(self):
        draw_bar(10, 20, 100, 5, -2.0, palette.RED, palette.LIGHT_GREEN)
        self.assertEqual(pyxel.pget(10, 20), palette.RED)
        self.assertEqual(pyxel.pget(60, 20), palette.RED)

    def test_zero_size_bar_does_not_crash(self):
        draw_bar(0, 0, 0, 5, 1.0, palette.RED, palette.LIGHT_GREEN)
        draw_bar(0, 0, 10, 0, 1.0, palette.RED, palette.LIGHT_GREEN)


class StatusBoxTest(unittest.TestCase):
    """13.1：116x38 信息框 + 双条。"""

    def setUp(self):
        helpers.ensure_init()
        pyxel.cls(0)

    def test_box_is_116x38_with_border(self):
        draw_status_box(4, 4, "小火狮", 5, 30, 34, 12, 16)
        self.assertEqual(pyxel.pget(4, 4), palette.DARK_PURPLE)
        self.assertEqual(pyxel.pget(119, 4), palette.DARK_PURPLE)
        self.assertEqual(pyxel.pget(4, 41), palette.DARK_PURPLE)

    def test_hp_and_mp_bars_are_drawn(self):
        draw_status_box(4, 4, "小火狮", 5, 17, 34, 8, 16)
        # HP 条：x=12, y=17，半血 -> 前 50 像素是绿色
        self.assertEqual(pyxel.pget(12, 17), palette.LIGHT_GREEN)
        self.assertEqual(pyxel.pget(61, 17), palette.LIGHT_GREEN)
        self.assertEqual(pyxel.pget(62, 17), palette.RED)
        # MP 条：x=12, y=30，一半 -> 前 33 像素是浅蓝
        self.assertEqual(pyxel.pget(12, 30), palette.LIGHT_BLUE)
        self.assertEqual(pyxel.pget(44, 30), palette.LIGHT_BLUE)
        self.assertEqual(pyxel.pget(45, 30), palette.DEEP_BLUE)

    def test_zero_max_does_not_crash(self):
        draw_status_box(4, 4, "?", 0, 0, 0, 0, 0)


class MenuListTest(unittest.TestCase):
    """5.3 / 13.2：菜单光标与置灰。"""

    def _menu(self):
        return MenuList(0, 0, [
            {"label": "A", "enabled": True},
            {"label": "B", "enabled": False},
            {"label": "C", "enabled": True},
        ])

    def test_move_wraps_around(self):
        menu = self._menu()
        self.assertEqual(menu.index, 0)
        menu.move(1)
        self.assertEqual(menu.index, 1)
        menu.move(1)
        self.assertEqual(menu.index, 2)
        menu.move(1)
        self.assertEqual(menu.index, 0)
        menu.move(-1)
        self.assertEqual(menu.index, 2)

    def test_disabled_item_cannot_be_confirmed(self):
        menu = self._menu()
        menu.move(1)
        self.assertFalse(menu.is_enabled())
        self.assertFalse(menu.confirm())
        menu.move(1)
        self.assertTrue(menu.confirm())

    def test_selected_returns_item(self):
        menu = self._menu()
        self.assertEqual(menu.selected["label"], "A")

    def test_two_column_navigation(self):
        menu = MenuList(0, 0, [
            {"label": "左0", "col": 0, "row": 0},
            {"label": "右0", "col": 1, "row": 0},
            {"label": "左1", "col": 0, "row": 1},
            {"label": "右1", "col": 1, "row": 1},
        ], cols=2)
        menu.move_h(1)
        self.assertEqual(menu.selected["label"], "右0")
        menu.move(1)
        self.assertEqual(menu.selected["label"], "右1")
        menu.move_h(-1)
        self.assertEqual(menu.selected["label"], "左1")


class DamageNumberUnitTest(unittest.TestCase):
    """13.3：圆圈飘字的生命周期与配色。"""

    def test_lifetime_is_60_frames(self):
        number = DamageNumber(100, 100, 12, "enemy")
        for _ in range(LIFETIME - 1):
            self.assertTrue(number.update())
        self.assertFalse(number.update())
        self.assertTrue(number.done)

    def test_rise_is_24_px(self):
        number = DamageNumber(0, 100, 1, "enemy")
        number.age = LIFETIME
        self.assertEqual(number.offset_y, RISE)
        self.assertEqual(RISE, 24)

    def test_colors_match_spec(self):
        self.assertEqual(DamageNumber(0, 0, 1, "enemy").colors, (15, 7, 0))
        self.assertEqual(DamageNumber(0, 0, 1, "player").colors, (8, 15, 7))

    def test_group_add_update_clear(self):
        group = DamageNumberGroup()
        group.add(10, 10, 5, "enemy")
        self.assertEqual(group.count, 1)
        for _ in range(LIFETIME):
            group.update()
        self.assertEqual(group.count, 0)
        group.add(1, 1, 1, "player")
        group.clear()
        self.assertEqual(group.count, 0)

    def test_blink_window(self):
        number = DamageNumber(0, 0, 1, "enemy")
        number.age = LIFETIME - BLINK_FRAMES
        self.assertEqual(number.visible, True)
        number.age = LIFETIME - BLINK_FRAMES + 1
        self.assertEqual(number.visible, False)

    def test_circle_radius_is_9(self):
        self.assertEqual(CIRCLE_RADIUS, 9)
