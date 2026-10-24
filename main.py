r"""精灵对战小游戏 —— 程序入口。

正常运行（开窗口，按 Esc 弹退出确认，可存档后退出）：

    E:\小说2\精灵对战小游戏\.venv\Scripts\python.exe main.py

无窗口自检（不依赖显示器，用于 CI / 截图核对）：

    E:\小说2\精灵对战小游戏\.venv\Scripts\python.exe main.py --headless --frames 10 ^
        --shot docs/shots/batch1_title.png

**注意**：中文输入法（IME）开启时会吞掉键盘事件——画面正常刷新但人物
不走。游玩前请切到英文输入法（Shift 或 Win+Space）。详见 README「已知限制」。

分辨率固定 240x216，帧率固定 60。
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
from src.ui import sound, text  # noqa: E402

#: 画面尺寸（锁定）
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 216
#: 帧率（锁定）
FPS = 60
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

    # 1) 初始化 Pyxel（分辨率 / 帧率锁定）
    # quit_key=pyxel.KEY_NONE：**关掉 Pyxel 自带的「Esc 立刻退出」**，
    # 改由 src/core/game.py 接管 Esc -> 弹出退出确认弹窗
    # （存档并退出 / 直接退出 / 取消），玩家按 Esc 不会立刻消失。
    pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title=TITLE, fps=FPS,
               headless=headless, quit_key=pyxel.KEY_NONE)

    # 1.5) 把窗口抢到前台（否则 SDL 收不到键盘事件，表现为"人物不走"）
    if not headless:
        focus.grab_focus()

    # 2) 自定义 16 色调色板 + 字体 + 素材烘焙
    palette.apply()
    text.init_font()

    # 2.5) 音频（T8b）：定义音效 + 载入 BGM + 设置通道音量。
    #      无声 / 无头环境下 init() 只会把音频标记成「不可用」，
    #      游戏照常跑（详见 src/ui/sound.py）。
    sound.init()

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
