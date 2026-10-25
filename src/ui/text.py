"""中文文本渲染封装。

**本文件是全项目唯一允许出现字体路径的地方**（验收标准 7）。
**所有中文必须经由本模块渲染**，禁止在别处直接调用 `pyxel.text` 画中文。

字体选择
--------
首选**随项目分发的点阵字体** Ark Pixel 12px（OFL 1.1，见同目录 OFL.txt）。
它是为 12px 手工点阵设计的中文像素字体，笔画落在整像素上，因此在
240x216 这个分辨率下比矢量黑体清晰得多——系统黑体在 12px 会把横竖笔画糊在一起
（实测同一段文字，simhei 的标题渲染出粘连和块状伪影）。

经实测，它的字宽与 simhei 在 12px 下**完全一致**（全角 12px / 半角 6px），
所以换字体不需要改任何布局常量。

回退顺序（前面的不可用才用后面的）：

1. `assets/fonts/ark-pixel-12px-monospaced-zh_hans.ttf`  ← 首选，随项目分发
2. `assets/fonts/simhei.ttf`                            ← 也可自行放一份
3. `C:\\Windows\\Fonts\\simhei.ttf`
4. `C:\\Windows\\Fonts\\msyh.ttc`
5. `C:\\Windows\\Fonts\\Deng.ttf`
6. `C:\\Windows\\Fonts\\simsun.ttc`

有了第 1 项之后，本项目**不再依赖 Windows 系统字体**，非 Windows 平台也能跑。
全部找不到时抛 RuntimeError，并提示手动放置字体。

（素材目录里的 `umplus_j12r.bdf` / `PixelMplus12-Regular.ttf` 仍然不可用：
它们是日文字体，缺简体字形，"精灵对战" 会渲染成 "精?小游"，已实测。）

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

#: 随项目分发的点阵字体文件名（OFL 1.1，可自由分发）
BUNDLED_FONT = "ark-pixel-12px-monospaced-zh_hans.ttf"

#: 字体候选路径（按优先级）。**只有本模块能引用这些路径。**
FONT_CANDIDATES: tuple[str, ...] = (
    os.path.join(_PROJECT_ROOT, "assets", "fonts", BUNDLED_FONT),
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

# ------------------------------------------------------------------ 字形覆盖回退
#
# 随项目分发的点阵字体**不一定覆盖游戏里用到的每一个汉字**（实测 Ark Pixel
# 简体版就缺 "药/然/即/既/热/毁/紧/缘" 等 31 个常用字，会渲染成空心方块）。
# 与其指望某一套字体全知全能，不如在这里做**逐字回退**：
#
#   主字体有这个字 -> 用主字体（锐利）
#   主字体没有     -> 用备用系统字体渲染这一个字（略糊，但至少不是方块）
#
# 之所以敢这么做，是因为两套字体在 12px 下的**字宽完全一致**
# （全角 12px / 半角 6px，已实测），所以中间换字体不会影响任何排版与折行。
# width() 因此完全不用改。

#: 主字体缺字时用来补的字体（按顺序找第一个可用的系统字体）
FALLBACK_CANDIDATES: tuple[str, ...] = (
    os.path.join(_PROJECT_ROOT, "assets", "fonts", "simhei.ttf"),
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\Deng.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
)

_FALLBACK_FONT: pyxel.Font | None = None
_FALLBACK_PATH: str | None = None
_COVERED: set[int] | None = None
_COVERAGE_RESOLVED = False


def read_cmap_codepoints(path: str) -> set[int]:
    """读取字体 cmap 表，返回它支持的码位集合。

    纯标准库（struct）实现，不依赖第三方库。只解析 format 4 与 format 12，
    这两种覆盖了中文点阵字体实际会用到的全部情况。解析失败返回空集，
    调用方会据此退化为"不做回退"，不会崩。
    """
    import struct

    try:
        with open(path, "rb") as f:
            data = f.read()
        if len(data) < 12:
            return set()
        (num_tables,) = struct.unpack(">H", data[4:6])
        cmap_off = None
        for i in range(num_tables):
            rec = 12 + i * 16
            if data[rec:rec + 4] == b"cmap":
                (cmap_off,) = struct.unpack(">I", data[rec + 8:rec + 12])
                break
        if cmap_off is None:
            return set()

        (n_sub,) = struct.unpack(">H", data[cmap_off + 2:cmap_off + 4])
        codes: set[int] = set()
        for i in range(n_sub):
            rec = cmap_off + 4 + i * 8
            (sub_off,) = struct.unpack(">I", data[rec + 4:rec + 8])
            so = cmap_off + sub_off
            (fmt,) = struct.unpack(">H", data[so:so + 2])
            if fmt == 4:
                (seg_x2,) = struct.unpack(">H", data[so + 6:so + 8])
                seg = seg_x2 // 2
                ends = [struct.unpack(">H", data[so + 14 + 2 * j:so + 16 + 2 * j])[0]
                        for j in range(seg)]
                starts_base = so + 16 + seg_x2
                starts = [struct.unpack(">H", data[starts_base + 2 * j:starts_base + 2 * j + 2])[0]
                          for j in range(seg)]
                for s, e in zip(starts, ends):
                    if s != 0xFFFF:
                        codes.update(range(s, e + 1))
            elif fmt == 12:
                (n_groups,) = struct.unpack(">I", data[so + 12:so + 16])
                for j in range(n_groups):
                    g = so + 16 + j * 12
                    s, e = struct.unpack(">II", data[g:g + 8])
                    if e - s <= 0xFFFF:
                        codes.update(range(s, e + 1))
        return codes
    except Exception:
        return set()


def covered_codepoints() -> set[int] | None:
    """主字体支持的码位集合；无法判定时返回 None（表示不做回退）。"""
    global _COVERED, _COVERAGE_RESOLVED
    if _COVERAGE_RESOLVED:
        return _COVERED
    _COVERAGE_RESOLVED = True
    path = font_path()
    # 只有主字体是随项目分发的点阵字体时才需要回退：
    # 系统字体（simhei 等）本身就覆盖这些字，没必要再套一层。
    if os.path.basename(path) != BUNDLED_FONT:
        return None
    codes = read_cmap_codepoints(path)
    _COVERED = codes or None
    return _COVERED


def fallback_font() -> pyxel.Font | None:
    """备用字体；没有可用回退时返回 None。"""
    global _FALLBACK_FONT, _FALLBACK_PATH
    if _FALLBACK_PATH is not None:
        return _FALLBACK_FONT
    main = os.path.abspath(font_path())
    for cand in FALLBACK_CANDIDATES:
        if os.path.isfile(cand) and os.path.abspath(cand) != main:
            _FALLBACK_PATH = cand
            _FALLBACK_FONT = pyxel.Font(cand, FONT_SIZE)
            return _FALLBACK_FONT
    _FALLBACK_PATH = ""          # 标记"已查找过，没有可用回退"
    return None



def warm_up() -> None:
    """预先付清字体相关的懒初始化开销。

    为什么需要：`pyxel.Font()` 的构造很贵——内置点阵字体约 60ms，系统黑体
    200~400ms（实测）。缺字回退用的是系统字体，如果不预热，这笔开销会落在
    **第一帧真正画中文的那一刻**，玩家看到的就是「窗口出现了，画面卡住半秒」。

    这里在进入主循环前把主字体、cmap 表、回退字体全部构造好，并把两套字体
    各光栅化一次。之后每帧的文字绘制只剩查表。
    """
    init_font()
    covered_codepoints()
    fallback = fallback_font()
    probe = "精灵对战伤药然"        # 含缺字，确保回退字体也被光栅化
    pyxel.cls(0)
    pyxel.text(0, 0, probe, 0, init_font())   # 色 0 = 黑，画完立刻清屏，肉眼不可见
    if fallback is not None:
        pyxel.text(0, 0, probe, 0, fallback)
    pyxel.cls(0)


def width(s: str) -> int:
    """测量字符串像素宽度。全角 12px、半角 6px。"""
    return init_font().text_width(s)


def draw(x: int, y: int, s: str, col: int) -> None:
    """在 (x, y) 处用颜色 col 绘制字符串（**中文必须走这里**）。

    主字体缺字时自动切换到备用字体渲染该字，避免出现空心方块。
    两套字体 12px 下字宽一致，所以分段绘制不会改变排版。
    """
    main = init_font()
    covered = covered_codepoints()
    if covered is None:
        pyxel.text(x, y, s, col, main)
        return

    fallback = fallback_font()
    if fallback is None:
        pyxel.text(x, y, s, col, main)
        return

    cx = x
    run = ""
    run_covered = None
    for ch in s:
        ok = ord(ch) in covered or ch == "\n"
        if run_covered is None or ok == run_covered:
            run += ch
            run_covered = ok
        else:
            pyxel.text(cx, y, run, col, main if run_covered else fallback)
            cx += (main if run_covered else fallback).text_width(run)
            run = ch
            run_covered = ok
    if run:
        pyxel.text(cx, y, run, col, main if run_covered else fallback)


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
