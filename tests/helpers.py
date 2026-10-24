"""测试辅助工具（标准库 unittest，不依赖 pytest / Pillow / numpy）。"""

from __future__ import annotations

import os
import struct
import sys

import pyxel

#: 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

#: 与游戏一致的画面尺寸 / 帧率
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 216
FPS = 60

_initialized = False


def ensure_init() -> None:
    """进程内只初始化一次 Pyxel。

    Pyxel 不允许重复 `init()`，而 unittest 一个进程会跑多个测试模块，
    所以这里用模块级开关保证只初始化一次。
    """
    global _initialized
    if _initialized:
        return
    # quit_key=pyxel.KEY_NONE：关掉 Pyxel 自带的「Esc 立刻退出」，
    # 免得无窗口测试里一个 Esc 把整个测试进程干掉（退出走 Game 的确认弹窗）。
    pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="unittest", fps=FPS,
               headless=True, quit_key=pyxel.KEY_NONE)
    from src.assets_gen import palette

    palette.apply()
    _initialized = True


def run_frames(update, draw, frames: int = 1, shot_path: str | None = None,
               scale: int = 2) -> int:
    """无窗口跑指定帧数，可选截图，返回实际跑的帧数。

    **为什么不用 `pyxel.run()` + `pyxel.quit()`**：
    实测 Pyxel 2.9.9 在 headless 模式下调用 `pyxel.quit()` 会**直接结束整个
    Python 进程**（quit() 之后的代码不再执行），那样 unittest 的后续用例
    根本跑不到，报告也会被截断。所以这里改成手动帧循环 +
    `pyxel.screenshot()`：画面缓冲（`pyxel.screen`）在 draw 之后就是
    最后一帧的内容，截图结果与真实游戏一致。
    """
    ensure_init()
    for _ in range(frames):
        update()
        draw()
    if shot_path:
        folder = os.path.dirname(os.path.abspath(shot_path))
        if folder:
            os.makedirs(folder, exist_ok=True)
        pyxel.screenshot(shot_path, scale=scale)
    return frames


def fake_input(script=None, **kwargs):
    """构造假输入（core.input.FakeInput）。"""
    from src.core.input import FakeInput

    return FakeInput(script=script, **kwargs)


def png_size(path: str) -> tuple[int, int]:
    """读 PNG 文件头的宽高（不依赖 Pillow）。"""
    with open(path, "rb") as fh:
        header = fh.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} 不是合法的 PNG 文件")
    return struct.unpack(">II", header[16:24])
