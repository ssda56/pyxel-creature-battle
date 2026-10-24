r"""精灵对战小游戏 —— 程序入口。

正常运行（开窗口，Esc 退出）：

    E:\小说2\精灵对战小游戏\.venv\Scripts\python.exe main.py

无窗口自检（不依赖显示器，用于 CI / 截图核对）：

    E:\小说2\精灵对战小游戏\.venv\Scripts\python.exe main.py --headless --frames 10 ^
        --shot docs/shots/batch1_title.png

输入诊断（排查"按键没反应"是环境问题还是代码问题）：

    E:\小说2\精灵对战小游戏\.venv\Scripts\python.exe main.py --debug-input

    开启后每帧打印一次按键状态变化，例如按 D 应看到：
        [input] frame=42 held=['right']
    若按了键却完全没有这行输出，说明 Pyxel 根本没收到键盘事件
    （窗口没拿到焦点 / 有旧窗口占着键盘），与游戏代码无关。

分辨率固定 240x216，帧率固定 30。
"""

from __future__ import annotations

import os
import sys

# 允许从任意目录用绝对路径启动
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyxel  # noqa: E402

from src.assets_gen import palette  # noqa: E402
from src.core import focus  # noqa: E402
from src.core.game import Game  # noqa: E402
from src.core.input import RealInput  # noqa: E402
from src.ui import text  # noqa: E402

#: 画面尺寸（锁定）
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 216
#: 帧率（锁定）
FPS = 30
#: 窗口标题
TITLE = "精灵对战"


def _parse_args(argv: list[str]) -> tuple[bool, int, str | None]:
    """解析命令行：--headless / --frames N / --shot PATH。"""
    headless = "--headless" in argv
    frames = 10
    shot = None
    if "--frames" in argv:
        frames = int(argv[argv.index("--frames") + 1])
    if "--shot" in argv:
        shot = argv[argv.index("--shot") + 1]
    return headless, frames, shot


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    headless, frames, shot = _parse_args(argv)

    # 0) 输入诊断开关（放在 init 之前无副作用，只是置一个类属性）
    if "--debug-input" in argv:
        RealInput.DEBUG = True
        print(
            "[main] 输入诊断已开启：按 W/A/S/D 或方向键时，"
            "应看到 [input] held=[...] 输出",
            flush=True,
        )

    # 1) 初始化 Pyxel（分辨率 / 帧率锁定）
    pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title=TITLE, fps=FPS, headless=headless)

    # 1.5) 把窗口抢到前台（否则 SDL 收不到键盘事件，表现为"人物不走"）
    if not headless:
        focus.grab_focus()

    # 2) 自定义 16 色调色板 + 字体 + 素材烘焙
    palette.apply()
    text.init_font()

    # 3) 建 Game
    game = Game()

    if headless:
        # 无窗口自检：手动跑若干帧（Pyxel 的 pyxel.quit() 会结束整个进程，
        # 所以这里不用 pyxel.run），然后可选截图
        for _ in range(frames):
            game.update()
            game.draw()
        if shot:
            folder = os.path.dirname(os.path.abspath(shot))
            if folder:
                os.makedirs(folder, exist_ok=True)
            pyxel.screenshot(shot, scale=2)
        print(
            f"[main] headless ok：{frames} 帧，{SCREEN_WIDTH}x{SCREEN_HEIGHT}@{FPS}fps"
            + (f"，截图 {shot}" if shot else ""),
            flush=True,
        )
        return

    # 4) 正常跑游戏
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
