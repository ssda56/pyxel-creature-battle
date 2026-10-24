"""场景栈（Scene Stack）。

调用语义（后续批次照此写）
--------------------------
- `push(scene)`   场景入栈，并调用 `scene.enter()`。
- `pop()`         弹出栈顶：先 `scene.exit()`，再让**下层场景** `resume()`。
- `replace(scene)` 用新场景替换栈顶：旧场景 `exit()`，新场景 `enter()`。

`resume()` 的语义是"重新回到前台"：恢复被暂停的动画 / 计时器，
**不重置**场景已有的状态（重置请放在 `enter()` 里）。
"""

from __future__ import annotations


class SceneManager:
    """场景栈管理器。"""

    def __init__(self):
        self._stack: list = []

    # ------------------------------------------------------------ 查询
    @property
    def current(self):
        """当前（栈顶）场景；空栈时为 None。"""
        return self._stack[-1] if self._stack else None

    @property
    def stack(self) -> list:
        """栈快照（从底到顶的副本）。"""
        return list(self._stack)

    def __len__(self) -> int:
        return len(self._stack)

    # ------------------------------------------------------------ 操作
    def push(self, scene, **kwargs):
        """入栈并调用 scene.enter()。"""
        self._stack.append(scene)
        scene.enter(**kwargs)
        return scene

    def pop(self):
        """弹出栈顶；返回被弹出的场景（空栈时返回 None）。"""
        if not self._stack:
            return None
        scene = self._stack.pop()
        scene.exit()
        if self._stack:
            self._stack[-1].resume()
        return scene

    def replace(self, scene, **kwargs):
        """用 scene 替换栈顶（空栈时等同于 push）。"""
        if self._stack:
            old = self._stack.pop()
            old.exit()
        self._stack.append(scene)
        scene.enter(**kwargs)
        return scene
