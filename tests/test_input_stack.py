"""方向键叠键回归测试（A8）。

用户报告的现象
--------------
本来按着 A 往左走，第二步按 W 往上走，全程不松开 A。
松开 W 之后，**A 应该立刻继续触发往左走**（间隔很小）。
但现在松开 W 人会**完全站住**，必须重新按一下方向键才动。

根因
----
FieldScene._read_direction 原来只认「当前朝向」那一个键：

    if inp.held(self.facing):
        return self.facing
    return None

按着 A（facing=left）-> 叠加按 W（facing=up）-> 松开 W：
held("up") 变假 -> 直接返回 None -> A 明明还按着，人却站住了。

这些用例在**修复前是红的**（旧的 _read_direction 返回 None）。
"""

from __future__ import annotations

import unittest

from src.core.input import FakeInput
from src.scenes.field_scene import DIR_ORDER, STEP_FRAMES
from tests import field_helpers

#: 新手村出生点附近的空地（左右上下都可走）
START_X, START_Y = 15, 10


def make_scene(map_id: int = 1, x: int = START_X, y: int = START_Y,
               facing: str = "down", script=None):
    """建一个 FieldScene（配好固定 seed，画面可复现）。"""
    game, scene = field_helpers.make_field(map_id=map_id, x=x, y=y,
                                           facing=facing, seed=1)
    if script is not None:
        game.input = FakeInput(script=script)
    return game, scene


def direction_trace(scene, inp, frames: int):
    """逐帧调用 _read_direction，返回 [(帧号, 方向, 朝向), ...]。

    帧推进顺序和真实游戏一致：先读方向，再 inp.update() 推进到下一帧。
    """
    trace = []
    for f in range(frames):
        d = scene._read_direction(inp)
        trace.append((f, d, scene.facing))
        inp.update()
    return trace


def move_trace(game, scene, frames: int):
    """逐帧跑真实的 update 循环，返回 [(朝向, 是否在走, 格x, 格y), ...]。"""
    trace = []
    for _ in range(frames):
        game.update()
        trace.append((scene.facing, scene.moving, scene.gx, scene.gy))
    return trace


class StackedKeyReleaseTest(unittest.TestCase):
    """核心场景：松开叠加上去的那个键，前一个键立刻接管。"""

    #: 帧 0~9 只按 left；10~14 叠加 up；15 起只按 left（up 被松开）
    SCRIPT = [{"left": 10}, {"left": 10, "up": 5}, {"left": 20}]

    #: 同上，但 left 一直按到最后（60 帧窗口内不会松手）
    LONG_SCRIPT = [{"left": 10}, {"left": 10, "up": 5}, {"left": 60}]

    def test_release_stacked_key_returns_to_previous_key(self):
        """松开 up 的那一帧，_read_direction 必须立刻返回 left。"""
        game, scene = make_scene()
        inp = FakeInput(script=self.SCRIPT)
        trace = direction_trace(scene, inp, 20)

        # 前 10 帧：只有 left
        for f in range(0, 10):
            self.assertEqual(trace[f][1], "left", f"第 {f} 帧应该是 left")
        # 10~14 帧：叠加的 up 接管
        for f in range(10, 15):
            self.assertEqual(trace[f][1], "up", f"第 {f} 帧应该是 up")
            self.assertEqual(trace[f][2], "up", f"第 {f} 帧朝向应该是 up")
        # 第 15 帧（松开 up 的第一帧）：必须立刻回到 left
        self.assertEqual(trace[15][1], "left",
                         "松开 up 之后必须立刻回到 left，不能站住")
        self.assertEqual(trace[15][2], "left", "朝向也必须立刻切回 left")
        for f in range(15, 20):
            self.assertEqual(trace[f][1], "left", f"第 {f} 帧应该继续 left")

    def test_recovery_takes_exactly_one_frame(self):
        """恢复间隔正好 1 帧：中间不允许出现 None 帧。"""
        game, scene = make_scene()
        inp = FakeInput(script=self.SCRIPT)
        trace = direction_trace(scene, inp, 20)

        last_up = max(f for f, d, _ in trace if d == "up")
        first_left_after = min(f for f, d, _ in trace
                               if f > last_up and d == "left")
        self.assertEqual(first_left_after - last_up, 1,
                         f"恢复间隔是 {first_left_after - last_up} 帧，应该正好 1 帧")
        # 整段（松开 up 之后）都不能有空帧
        for f in range(last_up + 1, 20):
            self.assertIsNotNone(trace[f][1],
                                 f"第 {f} 帧返回了 None —— 人在原地站住了")

    def test_player_keeps_walking_after_release(self):
        """集成：松开 up 之后玩家继续走，不会彻底站死。"""
        game, scene = make_scene()
        game.input = FakeInput(script=self.LONG_SCRIPT)
        trace = move_trace(game, scene, 60)

        # 整个过程（left 一直按着）玩家都不该停下来
        stopped = [i for i, (_, moving, _, _) in enumerate(trace)
                   if not moving]
        self.assertEqual(stopped, [],
                         f"玩家在第 {stopped} 帧停住了 —— 松开 up 后应继续走")

    def test_no_stationary_frame_between_tiles(self):
        """一格走完后立刻接上，不留多余的静止帧。"""
        game, scene = make_scene()
        game.input = FakeInput(script=self.LONG_SCRIPT)
        trace = move_trace(game, scene, 60)

        # up 叠加上去的时刻（帧 10）与松开它的时刻（帧 15）
        # 前后都不许出现「这一帧没在走」。
        for f in range(0, 60):
            if f in (10, 11, 12, 13, 14, 15, 16):
                self.assertTrue(trace[f][1],
                                f"第 {f} 帧玩家停住了（叠键切换点附近）")

    def test_tile_after_release_uses_the_previous_key(self):
        """松开 up 之后走完的那一格，方向必须是 left。"""
        game, scene = make_scene()
        game.input = FakeInput(script=self.LONG_SCRIPT)
        move_trace(game, scene, 60)

        # 一直按住 left -> 最后一定停在 left 那一列（起点 x 减若干）
        self.assertEqual(scene.facing, "left")
        self.assertLess(scene.gx, START_X, "应该一直在往左走")


class MultiKeyTest(unittest.TestCase):
    """多键同时按住。"""

    def test_two_keys_held_then_one_released(self):
        """up + left 同时按住，松开 up 之后走 left。"""
        game, scene = make_scene()
        # 帧 0~9：up 和 left 同时按住；帧 10 起：只剩 left
        inp = FakeInput(script=[{"up": 10, "left": 10}, {"left": 20}])
        trace = direction_trace(scene, inp, 20)

        for f in range(0, 10):
            self.assertEqual(trace[f][1], "up", f"第 {f} 帧应该保持 up")
        self.assertEqual(trace[10][1], "left",
                         "松开 up 的那一帧必须立刻切到 left")

    def test_diagonal_uses_dir_order_and_is_deterministic(self):
        """斜向同时按下：按 DIR_ORDER 的顺序，且可复现。"""
        order = DIR_ORDER.index("up")
        self.assertLess(order, DIR_ORDER.index("left"),
                        "DIR_ORDER 里 up 优先于 left")

        runs = []
        for _ in range(2):
            game, scene = make_scene()
            inp = FakeInput(script=[{"up": 5, "left": 5}])
            trace = direction_trace(scene, inp, 5)
            runs.append([d for _, d, _ in trace])
        self.assertEqual(runs[0], runs[1], "同样的按键序列必须给出同样的结果")
        self.assertEqual(runs[0][0], "up", "同时按下时按 DIR_ORDER 决定")


class StopTest(unittest.TestCase):
    """全部松开之后确实停住（防止「永远返回上一个方向」的过度修复）。"""

    def test_all_keys_released_stops(self):
        game, scene = make_scene()
        # 帧 0~9：left；帧 10~14：只剩 up；帧 15 起：什么都不按
        inp = FakeInput(script=[{"left": 10}, {"up": 5}])
        trace = direction_trace(scene, inp, 20)

        for f in range(0, 10):
            self.assertEqual(trace[f][1], "left")
        for f in range(10, 15):
            self.assertEqual(trace[f][1], "up")
        for f in range(15, 20):
            self.assertIsNone(trace[f][1],
                              f"第 {f} 帧什么都没按，应该返回 None")

    def test_player_stops_when_all_keys_released(self):
        game, scene = make_scene()
        game.input = FakeInput(script=[{"left": 10}, {"up": 5}, {"right": 0}])
        move_trace(game, scene, 80)
        self.assertFalse(scene.moving, "松开所有键之后玩家应该停下")


class SingleKeyTest(unittest.TestCase):
    """只按一个方向：行为必须和改动前完全一致。"""

    def test_single_direction_never_returns_none(self):
        game, scene = make_scene()
        inp = FakeInput(script=[{"right": 30}])
        trace = direction_trace(scene, inp, 30)
        for f, (frame, d, facing) in enumerate(trace):
            self.assertEqual(d, "right", f"第 {f} 帧应该是 right")
            self.assertEqual(facing, "right")

    def test_single_direction_walks_at_the_same_speed(self):
        """移动速度没变：一格还是 STEP_FRAMES 帧。"""
        game, scene = make_scene()
        game.input = FakeInput(script=[{"right": 60}])
        trace = move_trace(game, scene, STEP_FRAMES * 2)

        # 第 19 帧还在路上，第 20 帧落格
        self.assertTrue(trace[STEP_FRAMES - 2][1])
        self.assertEqual(trace[STEP_FRAMES - 1][2], START_X + 1)
        self.assertEqual(trace[STEP_FRAMES * 2 - 1][2], START_X + 2)


if __name__ == "__main__":
    unittest.main()
