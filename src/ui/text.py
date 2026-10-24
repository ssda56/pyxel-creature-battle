"""中文文本渲染封装。

**本文件是全项目唯一允许出现字体路径的地方**（验收标准 7）。
**所有中文必须经由本模块渲染**，禁止在别处直接调用 `pyxel.text` 画中文。

字体为什么不用素材目录里的 BDF / TTF
------------------------------------
《pyxel官方示例训练素材》examples/assets 里的 `umplus_j12r.bdf` /
`PixelMplus12-Regular.ttf` 是**日文字体，缺简体字形**，"精灵对战" 会渲染成
"精?小游"（已实测）。因此本项目只认 Windows 系统字体，按下列顺序回退：

1. 项目根 `assets/fonts/simhei.ttf`（可随项目分发自己的字体）
2. `C:\\Windows\\Fonts\\simhei.ttf`   ← 实测 12px 最清晰
3. `C:\\Windows\\Fonts\\msyh.ttc`
4. `C:\\Windows\\Fonts\\Deng.ttf`
5. `C:\\Windows\\Fonts\\simsun.ttc`

全部找不到时抛 RuntimeError，并提示手动放置字体。

字号固定 12（与《数值设定.md》§13 一致：全角 12px / 半角 6px / 行高 14px）。
"""

from __future__ import annotations

import os

import pyxel

#: 字号固定 12
FONT_SIZE = 12
#: 行高 14（《数值设定.md》§13）
LINE_HEIGHT = 14

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: 字体候选路径（按优先级）。**只有本模块能引用这些路径。**
FONT_CANDIDATES: tuple[str, ...] = (
    os.path.join(_PROJECT_ROOT, "assets", "fonts", "simhei.ttf"),
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\Deng.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
)

_FONT: pyxel.Font | None = None
_FONT_PATH: str | None = None


def font_path() -> str:
    """返回第一个可用的字体路径；都不可用时抛 RuntimeError。"""
    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            return path
    raise RuntimeError(
        "找不到可用的中文字体。请手动放置 simhei.ttf 到以下任一位置后重试：\n"
        + "\n".join(f"  - {p}" for p in FONT_CANDIDATES)
        + "\n（项目自带的 umplus_j12r.bdf / PixelMplus12-Regular.ttf 是日文字体，"
        "缺简体字形，不可用）"
    )


def init_font() -> pyxel.Font:
    """初始化并返回全局字体对象（幂等）。"""
    global _FONT, _FONT_PATH
    if _FONT is None:
        path = font_path()
        _FONT = pyxel.Font(path, FONT_SIZE)
        _FONT_PATH = path
    return _FONT


def current_font_path() -> str | None:
    """返回当前实际使用的字体路径（未初始化时返回 None）。"""
    return _FONT_PATH


def width(s: str) -> int:
    """测量字符串像素宽度。全角 12px、半角 6px。"""
    return init_font().text_width(s)


def draw(x: int, y: int, s: str, col: int) -> None:
    """在 (x, y) 处用颜色 col 绘制字符串（**中文必须走这里**）。"""
    pyxel.text(x, y, s, col, init_font())


def draw_center(cx: int, y: int, s: str, col: int) -> None:
    """以 cx 为中心水平居中绘制字符串。"""
    draw(int(cx - width(s) // 2), y, s, col)


def wrap(s: str, max_px: int) -> list[str]:
    """按像素宽度折行（支持中英混排，\n 强制换行）。

    - 单行宽度都不会超过 max_px；
    - 某个字符本身比 max_px 还宽时，它独占一行；
    - 保留原文中的空行。
    """
    if max_px <= 0:
        raise ValueError(f"max_px 必须为正整数，收到 {max_px}")

    lines: list[str] = []
    for paragraph in s.split("\n"):
        if paragraph == "":
            lines.append("")
            continue
        current = ""
        for ch in paragraph:
            if current and width(current + ch) > max_px:
                lines.append(current)
                current = ch
            else:
                current += ch
        lines.append(current)
    return lines


def draw_wrapped(x: int, y: int, s: str, max_px: int, col: int,
                 line_height: int = LINE_HEIGHT) -> int:
    """折行绘制文本，返回绘制后的下一行 y 坐标。"""
    for i, line in enumerate(wrap(s, max_px)):
        draw(x, y + i * line_height, line, col)
    return y + len(wrap(s, max_px)) * line_height
