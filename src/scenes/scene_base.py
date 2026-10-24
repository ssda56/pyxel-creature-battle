"""场景基类。

生命周期
--------
    enter(**kwargs)  场景入栈时被调用：初始化 / 重置场景状态
    resume()         被 pop() 揭示、重新回到前台时被调用：恢复动画与计时器，
                     **不重置**状态
    exit()           场景出栈时被调用：释放资源
    update(inp)      每帧逻辑更新，inp 是 core.input.Input
    draw()           每帧绘制
"""

from __future__ import annotations


class Scene:
    """所有场景的基类。"""

    def __init__(self, game):
        self.game = game

    def enter(self, **kwargs) -> None:
        """场景进入（入栈 / replace 时调用）。"""

    def resume(self) -> None:
        """场景重新回到前台（被下层场景 pop 回来时调用）。"""

    def exit(self) -> None:
        """场景退出（出栈 / 被 replace 时调用）。"""

    def update(self, inp) -> None:
        """每帧更新。inp 为 core.input.Input 实例。"""

    def draw(self) -> None:
        """每帧绘制。"""
