"""把游戏窗口提到前台并抢到键盘焦点（仅 Windows）。

为什么需要
----------
从 PyCharm / 命令行启动后，窗口有时不会成为**前台窗口**，此时 SDL 收不到
键盘事件：画面照常刷新，但所有按键都没反应（表现为「游戏打开了但人物不走」）。
用户手动点一下窗口就好了，但那不该由用户来做。

本模块在 `pyxel.init()` 之后调用一次，按窗口标题找到自己的窗口，
恢复并置于前台。找不到就静默跳过，绝不影响游戏启动。
"""

from __future__ import annotations

import os
import sys

#: 游戏窗口标题（与 main.py 的 TITLE 一致）
WINDOW_TITLE = "精灵对战"

#: SW_RESTORE，把最小化/未激活的窗口恢复
_SW_RESTORE = 9


_hwnd_cache: int = 0


def window_handle(title: str = WINDOW_TITLE) -> int:
    """返回本进程的窗口句柄（找不到返回 0），结果缓存。"""
    global _hwnd_cache
    if _hwnd_cache:
        return _hwnd_cache
    if sys.platform != "win32":
        return 0
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, title)
        if not hwnd:
            return 0
        owner = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value != os.getpid():
            return 0
        _hwnd_cache = int(hwnd)
        return _hwnd_cache
    except Exception:
        return 0


def is_focused(title: str = WINDOW_TITLE) -> bool:
    """游戏窗口当前是否是**前台窗口**（即键盘事件会送到游戏）。

    非 Windows 或找不到窗口时一律返回 True，避免误报。
    """
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        hwnd = window_handle(title)
        if not hwnd:
            return True
        return int(ctypes.windll.user32.GetForegroundWindow()) == hwnd
    except Exception:
        return True


def grab_focus(title: str = WINDOW_TITLE) -> bool:
    """尝试把标题为 title 的窗口置于前台。

    返回是否成功（非 Windows 平台或失败都返回 False，不抛异常）。
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, title)
        if not hwnd:
            return False
        # 必须是**我们自己进程**的窗口：同名窗口（例如另一个残留的游戏实例）
        # 不能抢，否则会把焦点给到错误的窗口。
        owner_pid = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
        if owner_pid.value != os.getpid():
            return False
        user32.ShowWindow(hwnd, _SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False
