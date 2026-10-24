"""场景栈语义测试：push / pop / replace 与 enter / exit / resume 的调用顺序。"""

import unittest

from src.core.scene_manager import SceneManager
from src.scenes.scene_base import Scene


class Recorder(Scene):
    """记录生命周期调用的假场景。"""

    def __init__(self, game, log, name):
        super().__init__(game)
        self.log = log
        self.name = name

    def enter(self, **kwargs):
        self.log.append(f"{self.name}.enter")

    def resume(self):
        self.log.append(f"{self.name}.resume")

    def exit(self):
        self.log.append(f"{self.name}.exit")


class SceneManagerTest(unittest.TestCase):
    def setUp(self):
        self.log = []
        self.sm = SceneManager()

    def _scene(self, name):
        return Recorder(None, self.log, name)

    # ------------------------------------------------------------ 基本
    def test_empty_stack_has_no_current(self):
        self.assertIsNone(self.sm.current)
        self.assertEqual(len(self.sm), 0)

    def test_push_calls_enter_and_sets_current(self):
        a = self._scene("A")
        self.sm.push(a)
        self.assertIs(self.sm.current, a)
        self.assertEqual(self.log, ["A.enter"])

    def test_pop_on_empty_stack_returns_none(self):
        self.assertIsNone(self.sm.pop())

    # ------------------------------------------------------------ pop
    def test_pop_exits_top_then_resumes_below(self):
        a = self._scene("A")
        b = self._scene("B")
        self.sm.push(a)
        self.sm.push(b)
        self.log.clear()

        popped = self.sm.pop()

        self.assertIs(popped, b)
        self.assertIs(self.sm.current, a)
        self.assertEqual(self.log, ["B.exit", "A.resume"])

    def test_pop_last_scene_leaves_no_current(self):
        a = self._scene("A")
        self.sm.push(a)
        self.sm.pop()
        self.assertIsNone(self.sm.current)
        self.assertEqual(self.log, ["A.enter", "A.exit"])

    # ------------------------------------------------------------ replace
    def test_replace_exits_old_and_enters_new(self):
        a = self._scene("A")
        b = self._scene("B")
        self.sm.push(a)
        self.log.clear()

        self.sm.replace(b)

        self.assertEqual(self.log, ["A.exit", "B.enter"])
        self.assertIs(self.sm.current, b)
        self.assertEqual(len(self.sm), 1)

    def test_replace_on_empty_stack_acts_like_push(self):
        a = self._scene("A")
        self.sm.replace(a)
        self.assertIs(self.sm.current, a)
        self.assertEqual(self.log, ["A.enter"])

    # ------------------------------------------------------------ 栈顺序
    def test_stack_is_bottom_to_top(self):
        a = self._scene("A")
        b = self._scene("B")
        c = self._scene("C")
        self.sm.push(a)
        self.sm.push(b)
        self.sm.push(c)
        self.assertEqual(self.sm.stack, [a, b, c])
        self.assertIs(self.sm.current, c)


class SceneBaseTest(unittest.TestCase):
    """Scene 基类的默认实现应该都是安全的空操作。"""

    def test_default_lifecycle_does_nothing(self):
        scene = Scene(game=None)
        self.assertIsNone(scene.enter())
        self.assertIsNone(scene.resume())
        self.assertIsNone(scene.exit())
        self.assertIsNone(scene.update(None))
        self.assertIsNone(scene.draw())
        self.assertIsNone(scene.game)


if __name__ == "__main__":
    unittest.main()
