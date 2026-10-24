"""帧率时长不变性测试（T9：帧率 30 -> 60）。

背景
----
帧率从 30fps 提到 60fps 时，**所有时长（秒）必须完全不变**，
否则手感会被破坏（走一格从 333ms 变 167ms、重生从 6s 变 3s……）。
做法就是：FPS 翻倍的同时，所有"帧"常量同步翻倍。

本模块把这条不变量**写死成测试**：每个时长常量除以当前 FPS，
必须等于帧率翻倍**之前**的秒数（容差 0）。

以后任何人再改帧率或者改常量，这个文件会立刻报错。
"""

from __future__ import annotations

import unittest

from src.data import map_data
from src.model import save_io
from src.scenes import battle_scene, field_scene, menu_scene, shop_scene, title_scene
from src.ui import damage_number, transition


#: 项目当前帧率（main.py / tests/helpers.py / save_io.py 三处必须一致）
FPS = 60

#: 帧率翻倍之前的帧率（用来算"原始秒数"）
OLD_FPS = 30


class FpsConsistencyTest(unittest.TestCase):
    """三处 FPS 定义必须一致。"""

    def test_all_fps_definitions_match(self):
        import main
        from tests import helpers

        self.assertEqual(main.FPS, FPS, "main.py 的 FPS 不对")
        self.assertEqual(helpers.FPS, FPS, "tests/helpers.py 的 FPS 不对")
        self.assertEqual(save_io.FPS, FPS, "src/model/save_io.py 的 FPS 不对")

    def test_transition_max_steps_is_black_levels_not_frames(self):
        """Fade.MAX_STEPS 是黑度档数（不是帧数），翻倍帧率时**不该**动。"""
        self.assertEqual(transition.MAX_STEPS, 16)

    def test_damage_number_rise_is_pixels_not_frames(self):
        """RISE = 24 是像素位移（不是帧数），翻倍帧率时**不该**动。"""
        self.assertEqual(damage_number.RISE, 24)

    def test_damage_number_circle_radius_is_pixels(self):
        """CIRCLE_RADIUS = 9 是像素半径（不是帧数），翻倍帧率时**不该**动。"""
        self.assertEqual(damage_number.CIRCLE_RADIUS, 9)


class DurationInvariantTest(unittest.TestCase):
    """每个时长常量 / FPS 必须等于改动前的秒数（容差 0）。"""

    #: (说明, 新常量, 旧常量)
    #: 新常量 / 60fps 必须精确等于 旧常量 / 30fps
    CASES = [
        ("走一格", field_scene.STEP_FRAMES, 10),
        ("转场淡入淡出", field_scene.FADE_FRAMES, 15),
        ("治疗演出总长", field_scene.HEAL_FRAMES, 50),
        ("治疗纯白收尾", field_scene.HEAL_SOLID_FRAMES, 2),
        ("治疗闪光半周期", field_scene.HEAL_FLASH_STEP, 6),
        ("战败淡出", battle_scene.DEFEAT_FADE_FRAMES, 30),
        ("菜单提示", menu_scene.MESSAGE_FRAMES, 120),
        ("商店提示", shop_scene.MESSAGE_FRAMES, 120),
        ("标题读档失败提示", title_scene.HINT_FRAMES, 60),
        ("飘字总时长", damage_number.LIFETIME, 30),
        ("飘字最后闪烁", damage_number.BLINK_FRAMES, 10),
    ]

    def test_all_durations_unchanged(self):
        for name, new_value, old_value in self.CASES:
            with self.subTest(时长=name):
                self.assertEqual(
                    new_value / FPS,
                    old_value / OLD_FPS,
                    f"{name}：{new_value}/{FPS}s != 原来的 {old_value}/{OLD_FPS}s",
                )

    def test_wander_parameters_unchanged(self):
        """野外游走 / 重生参数（map2）时长不变。"""
        enc = map_data.encounters_of(2)
        self.assertEqual(enc["respawn_frames"] / FPS, 180 / OLD_FPS)
        self.assertEqual(enc["move_min"] / FPS, 40 / OLD_FPS)
        self.assertEqual(enc["move_max"] / FPS, 70 / OLD_FPS)

    def test_fade_default_frames_unchanged(self):
        """Fade.start_out / start_in 的默认帧数时长不变。"""
        import inspect

        for name in ("start_out", "start_in"):
            with self.subTest(方法=name):
                sig = inspect.signature(getattr(transition.Fade, name))
                default = sig.parameters["frames"].default
                self.assertEqual(default / FPS, 15 / OLD_FPS)

    def test_damage_number_blink_duty_cycle_unchanged(self):
        """飘字最后闪烁窗口的占空比仍是 50%（亮/暗各一半）。"""
        window = range(damage_number.LIFETIME - damage_number.BLINK_FRAMES,
                       damage_number.LIFETIME)
        visible = sum(1 for age in window if age % 2 == 0)
        self.assertEqual(visible * 2, damage_number.BLINK_FRAMES)

    def test_heal_flash_half_cycles_unchanged(self):
        """治疗演出的棋盘闪光次数不变（8 个半周期 = 4 次完整闪光）。"""
        self.assertEqual(field_scene.HEAL_FRAMES // field_scene.HEAL_FLASH_STEP, 8)


if __name__ == "__main__":
    unittest.main()
