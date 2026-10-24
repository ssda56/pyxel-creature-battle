"""按键映射测试：WASD 与方向键都必须可用，且动作集合完整。"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyxel  # noqa: E402

from src.core.input import ACTIONS, KEY_MAP, keys_of  # noqa: E402


class KeyMapTest(unittest.TestCase):
    """按键映射。"""

    def test_all_actions_have_keys(self) -> None:
        for action in ACTIONS:
            self.assertIn(action, KEY_MAP, f"动作 {action} 没有配置按键")
            self.assertGreaterEqual(len(KEY_MAP[action]), 1, f"动作 {action} 按键为空")

    def test_wasd_moves(self) -> None:
        self.assertIn(pyxel.KEY_W, keys_of("up"))
        self.assertIn(pyxel.KEY_S, keys_of("down"))
        self.assertIn(pyxel.KEY_A, keys_of("left"))
        self.assertIn(pyxel.KEY_D, keys_of("right"))

    def test_arrow_keys_still_work(self) -> None:
        self.assertIn(pyxel.KEY_UP, keys_of("up"))
        self.assertIn(pyxel.KEY_DOWN, keys_of("down"))
        self.assertIn(pyxel.KEY_LEFT, keys_of("left"))
        self.assertIn(pyxel.KEY_RIGHT, keys_of("right"))

    def test_confirm_and_cancel(self) -> None:
        self.assertIn(pyxel.KEY_Z, keys_of("confirm"))
        self.assertIn(pyxel.KEY_RETURN, keys_of("confirm"))
        self.assertIn(pyxel.KEY_X, keys_of("cancel"))
        self.assertIn(pyxel.KEY_BACKSPACE, keys_of("cancel"))

    def test_no_key_bound_to_two_direction_actions(self) -> None:
        """同一个键不能同时绑到两个方向，否则会同时触发。"""
        seen: dict[int, str] = {}
        for action in ("up", "down", "left", "right"):
            for key in keys_of(action):
                self.assertNotIn(key, seen, f"键 {key} 同时绑到 {seen.get(key)} 与 {action}")
                seen[key] = action

    def test_unknown_action_raises(self) -> None:
        with self.assertRaises(KeyError):
            keys_of("jump")


if __name__ == "__main__":
    unittest.main()
