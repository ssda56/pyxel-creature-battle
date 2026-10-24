"""输入抽象层。

游戏逻辑只认 7 个**动作**，不认具体物理按键：

    up / down / left / right / confirm / cancel / menu

- `RealInput`：读真实键盘（pyxel.btn / pyxel.btnp）。
- `FakeInput`：按脚本注入，测试用。

按键映射
--------
======== ========== ==========================================
动作     按键        说明
======== ========== ==========================================
up       W / ↑      两种都支持
down     S / ↓
left     A / ←
right    D / →
confirm  Z / K / Enter   （pyxel.KEY_RETURN 即回车）
cancel   X / J / Backspace
menu     C
======== ========== ==========================================

**Esc 不作为功能键**：Esc 是 Pyxel 默认退出键（quit_key 默认 KEY_ESCAPE），
本项目保持默认，用户按 Esc 直接退出游戏。
"""

from __future__ import annotations

import pyxel

#: 全部动作名，顺序固定
ACTIONS: tuple[str, ...] = ("up", "down", "left", "right", "confirm", "cancel", "menu")

#: 动作 -> 物理按键码
KEY_MAP: dict[str, tuple[int, ...]] = {
    "up": (pyxel.KEY_UP, pyxel.KEY_W),
    "down": (pyxel.KEY_DOWN, pyxel.KEY_S),
    "left": (pyxel.KEY_LEFT, pyxel.KEY_A),
    "right": (pyxel.KEY_RIGHT, pyxel.KEY_D),
    "confirm": (pyxel.KEY_Z, pyxel.KEY_K, pyxel.KEY_RETURN),
    "cancel": (pyxel.KEY_X, pyxel.KEY_J, pyxel.KEY_BACKSPACE),
    "menu": (pyxel.KEY_C,),
}


def keys_of(action: str) -> tuple[int, ...]:
    """返回动作对应的按键码；未知动作抛 KeyError。"""
    try:
        return KEY_MAP[action]
    except KeyError:
        raise KeyError(f"未知动作 {action!r}，可用动作：{ACTIONS}") from None


class Input:
    """输入接口基类。

    约定：`update()` 每帧调用一次，**在场景 update 之后**，
    作用是把内部状态推进到"下一帧"。真实输入没有帧状态，所以基类是空操作。
    """

    def update(self) -> None:
        """推进一帧（基类空操作）。"""

    def held(self, action: str) -> bool:
        """动作是否**持续按住**（本帧及之前一直按下）。"""
        raise NotImplementedError

    def pressed(self, action: str) -> bool:
        """动作是否**本帧刚按下**（边沿，松开后再按才算）。"""
        raise NotImplementedError

    @staticmethod
    def is_action(action: str) -> bool:
        """动作名是否合法。"""
        return action in ACTIONS


class RealInput(Input):
    """真实键盘输入。

    `RealInput.DEBUG = True`（或 `main.py --debug-input`）时，每帧把「按住的
    动作集合」与上一帧比较，发生变化就打印一行。用来区分「按键根本没被 Pyxel
    收到（窗口没焦点 / 环境问题）」与「收到了但游戏逻辑没响应（代码问题）」。
    """

    #: 打开后每帧打印按键状态变化（诊断用）
    #: 临时默认开启，用于排查"地图上不能移动"；定位完成后改回 False。
    DEBUG = True

    def __init__(self) -> None:
        self._dbg_last: frozenset[str] = frozenset()
        #: 启动至今累计收到过多少次「新按下」的动作（松手后不会清零）
        self.seen_count: int = 0
        #: 最近一次收到的动作名
        self.last_action: str = ""
        #: 最近一次收到动作时的 pyxel 帧号
        self.last_frame: int = -1

    def update(self) -> None:
        current = frozenset(a for a in ACTIONS if self.held(a))
        fresh = current - self._dbg_last
        if fresh:
            self.seen_count += len(fresh)
            self.last_action = sorted(fresh)[-1]
            self.last_frame = pyxel.frame_count
        if RealInput.DEBUG and current != self._dbg_last:
            print(f"[input] frame={pyxel.frame_count} held={sorted(current)}")
        self._dbg_last = current

    def held(self, action: str) -> bool:
        return any(pyxel.btn(k) for k in keys_of(action))

    def pressed(self, action: str) -> bool:
        return any(pyxel.btnp(k) for k in keys_of(action))


class _Segment:
    """脚本中的一段：一组 (动作, 持续帧数)。"""

    __slots__ = ("items", "duration")

    def __init__(self, items: list[tuple[str, int]]):
        self.items = items
        self.duration = max((f for _, f in items), default=1)


class FakeInput(Input):
    """脚本化的假输入（测试用）。

    脚本格式
    --------
    `script` 是一个**段列表**，每段是一个 dict：

        {动作: 持续帧数}

    例如 `FakeInput(script=[{"confirm": 3}])` 表示：
    从第 0 帧起，`confirm` 连续按住 3 帧（第 0、1、2 帧 held 为 True，
    只有第 0 帧 pressed 为 True）。

    - 段与段之间**不重叠**：上一段结束即进入下一段，没写到的动作自动松开。
    - 脚本用完后，之后所有帧都不按任何键（`loop=True` 则从第一段重新循环）。
    - 字典里的每个动作可以有各自的帧数，例如 `{"confirm": 3, "up": 1}`。

    另外提供 `queue()` 动态追加段、`step()` 手动推进一帧。
    """

    def __init__(self, script=None, loop: bool = False):
        self._segments: list[_Segment] = []
        self._loop = bool(loop)
        self._frame = 0
        self._prev: frozenset[str] = frozenset()
        self._cur: frozenset[str] = frozenset()
        if script:
            for seg in script:
                self.queue(seg)
        self._cur = self._state_at(0)

    # ------------------------------------------------------------ 脚本构造
    def queue(self, actions, frames: int = 1) -> "FakeInput":
        """追加一段脚本，返回自身以便链式调用。

        `actions` 可以是：
          * dict `{动作: 帧数}`——每个动作各自的持续帧数；
          * str  单个动作；
          * 可迭代对象——多个动作，此时都用 `frames` 帧。
        """
        if isinstance(actions, dict):
            items = [(a, max(1, int(f))) for a, f in actions.items()]
        elif isinstance(actions, str):
            items = [(actions, max(1, int(frames)))]
        else:
            items = [(a, max(1, int(frames))) for a in actions]
        self._segments.append(_Segment(items))
        return self

    #: queue 的语义化别名
    press = queue

    # ------------------------------------------------------------ 帧推进
    def update(self) -> None:
        """推进到下一帧。"""
        self._prev = self._cur
        self._frame += 1
        self._cur = self._state_at(self._frame)

    #: 手动推进一帧的别名
    step = update

    # ------------------------------------------------------------ 查询
    def held(self, action: str) -> bool:
        return action in self._cur

    def pressed(self, action: str) -> bool:
        return action in self._cur and action not in self._prev

    # ------------------------------------------------------------ 调试信息
    @property
    def frame(self) -> int:
        """当前帧号（从 0 开始）。"""
        return self._frame

    @property
    def current(self) -> frozenset[str]:
        """当前帧按住的动作集合。"""
        return self._cur

    @property
    def previous(self) -> frozenset[str]:
        """上一帧按住的动作集合。"""
        return self._prev

    def _state_at(self, frame: int) -> frozenset[str]:
        """计算第 frame 帧按住的动作集合。"""
        if not self._segments:
            return frozenset()
        total = sum(s.duration for s in self._segments)
        if total <= 0:
            return frozenset()
        if self._loop:
            frame %= total
        acc = 0
        for seg in self._segments:
            if frame < acc + seg.duration:
                local = frame - acc
                return frozenset(a for a, f in seg.items if local < f)
            acc += seg.duration
        return frozenset()
