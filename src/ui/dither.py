"""抖动（半色调）绘制工具 —— 战斗画面的立体感增强（**纯绘制层**）。

提供三样东西：

- :data:`BAYER_4X4`：4x4 拜耳矩阵（**固定表**）；
- :func:`bayer_threshold`：某个像素的抖动阈值；
- :func:`dither_ellipse`：密度向外衰减的抖动椭圆（脚下投影用）；
- :func:`shade_lower_right`：精灵图「右下侧暗化」（返回新图，**不改原图**）。

确定性铁律
----------
**一切随机必须是确定性的**：本模块的图案只由坐标决定，
**绝对不使用 `random` 或时间**。本仓库有 45 张截图作为视觉回归证据，
任何一处随机都会让每次跑测试都把仓库弄脏。

色彩铁律
--------
- **色 0 是 `pyxel.blt(colkey=0)` 的透明键，绝不作为可见颜色**；
- 只用 :mod:`src.assets_gen.palette` 里的**语义常量**，不写裸色号。
"""

from __future__ import annotations

import pyxel

from src.assets_gen import palette

# ==================================================================== 拜耳矩阵
#: 4x4 拜耳矩阵（有序抖动），值域 0~15，越小越容易被"选中"。
#: **固定表**：同一坐标永远得到同一个值 -> 画面可复现。
BAYER_4X4: tuple[tuple[int, ...], ...] = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)

#: 拜耳矩阵的边长
BAYER_SIZE = 4


def bayer_threshold(x: int, y: int) -> float:
    """像素 `(x, y)` 的抖动阈值，范围 0~1（越小越容易落色）。"""
    return BAYER_4X4[int(y) % BAYER_SIZE][int(x) % BAYER_SIZE] / 16.0


# ==================================================================== 脚下投影
def dither_ellipse(cx: float, cy: float, rx: float, ry: float,
                   color: int, intensity: float = 1.0) -> None:
    """画一个**抖动**的椭圆（密度从中心向外线性衰减到 0）。

    参数
    ----
    cx, cy
        椭圆中心（屏幕绝对坐标）。
    rx, ry
        半径（像素）。
    color
        落色（:mod:`src.assets_gen.palette` 的语义常量）。
    intensity
        整体浓度 0~1。0 = 完全不画。

    为什么要"密度衰减"
    ------------------
    实心椭圆会像贴了块膏药；密度从中心向外化开之后，
    边缘是散开的颗粒，读起来才是"一团柔和的影子"。

    .. note::
       这个是**直接画**的版本，每帧调用会有几百次 Python -> C 调用。
       要每帧画就用 :func:bake_dither_ellipse 烘焙成小图再 blt。
    """
    if rx <= 0 or ry <= 0 or intensity <= 0:
        return
    cx = float(cx)
    cy = float(cy)
    rx = float(rx)
    ry = float(ry)
    x0 = int(cx - rx) - 1
    x1 = int(cx + rx) + 1
    y0 = int(cy - ry) - 1
    y1 = int(cy + ry) + 1
    col = int(color)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d > 1.0:
                continue
            # 中心 cover=1，边缘 cover=0
            cover = (1.0 - d ** 0.5) * float(intensity)
            if cover <= 0.0:
                continue
            if bayer_threshold(x, y) < cover:
                pyxel.pset(x, y, col)


def bake_dither_ellipse(layers) -> pyxel.Image:
    """把若干层「抖动椭圆」烘焙成一张小图（背景透明 = 色 0）。

    参数
    ----
    layers
        形如 [(rx, ry, color, intensity), ...]，几层**共用同一个圆心**，
        后面的层盖在前面层上（所以内层核心会盖掉外层的颜色，
        只在核心自己的抖动画洞里露出外层 —— 这就是两个色阶的过渡）。

    为什么要烘焙
    ------------
    椭圆是逐像素 pset 画的：一个 30x12 的椭圆要 360 次 Python -> C 调用，
    **每帧**都画就是每帧 ~0.3ms（是整个战斗画面绘制耗时的十倍）。
    烘焙成小图之后每帧只要一次 blt，快一个数量级 —— 图案本身完全一样。

    确定性
    ------
    图案用**小图自己的局部坐标**算拜耳阈值，所以影子在入场动画里
    平移时，颗粒纹理跟着影子一起走（不会在地面上"游泳"），
    而且同一只精灵每次烘焙出来的图**完全一样**。
    """
    layers = list(layers or [])
    if not layers:
        return pyxel.Image(1, 1)
    max_rx = max(int(layer[0]) for layer in layers)
    max_ry = max(int(layer[1]) for layer in layers)
    width = max_rx * 2 + 1
    height = max_ry * 2 + 1
    img = pyxel.Image(width, height)
    cx = float(max_rx)
    cy = float(max_ry)
    for layer in layers:
        rx = float(layer[0])
        ry = float(layer[1])
        color = int(layer[2])
        intensity = float(layer[3])
        if rx <= 0 or ry <= 0 or intensity <= 0:
            continue
        for y in range(height):
            for x in range(width):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d > 1.0:
                    continue
                cover = (1.0 - d ** 0.5) * intensity
                if cover <= 0.0:
                    continue
                if bayer_threshold(x, y) < cover:
                    img.pset(x, y, color)
    return img


# ==================================================================== 精灵暗化
#: 颜色 -> 同色系更暗一档（暗化时替换用）。
#:
#: 没有出现在这张表里的颜色（描边深紫 5、深蓝 1、深绿 3、灰 6、棕 13）
#: 本来就已经很暗，**保持原样** —— 免得把描边换成另一种黑，
#: 反而看不出体积感。
DARKEN_MAP: dict[int, int] = {
    palette.ORANGE: palette.BROWN,
    palette.RED: palette.BROWN,
    palette.YELLOW: palette.ORANGE,
    palette.LIGHT_GREEN: palette.GREEN,
    palette.LIGHT_BLUE: palette.BLUE,
    palette.WHITE: palette.LIGHT_GRAY,
    palette.BLUE: palette.DEEP_BLUE,
    palette.GREEN: palette.DARK_GREEN,
    palette.PINK: palette.RED,
    palette.LIGHT_GRAY: palette.GRAY,
}

#: 最外圈（run == 1）是精灵自带的色 5 描边，**跳过**：压暗它也看不出来。
_FIRST_INNER_RUN = 2

#: 暗化最多往里吃几圈（run <= 该值）
#:
#: 取 4 = 往里吃 3 圈（描边那圈不算）。再深就会糊住 32x32 的细节了。
SHADE_DEPTH = 4

#: 每一圈的压暗浓度（run -> 浓度），越往里越淡
SHADE_DENSITY: dict[int, float] = {2: 0.90, 3: 0.55, 4: 0.25}


def shade_lower_right(img: pyxel.Image,
                      darken_map: dict[int, int] | None = None,
                      depth: int = SHADE_DEPTH,
                      intensity: float = 1.0) -> pyxel.Image:
    """给精灵图做「右下侧暗化」，返回一张**新图**（原图一个像素都不动）。

    光源假设在**左上**，所以轮廓的**右下侧**背光、压暗。

    做法
    ----
    1. 读出像素，算出每个不透明像素在四个方向上的**连续不透明长度**
       （`run_left` / `run_right` / `run_up` / `run_down`）：
       某一行里从左数第几个 = run_left，从右数第几个 = run_right。
    2. 只处理"朝右下"的像素：**右边或下边很快就是透明**
       （`run_right < run_left` / `run_down < run_up`），
       也就是轮廓朝右下方向比朝左上方向更陡的地方。
       左右对称的圆润身体中间部分两个长度相等，自然不会被选中。
    3. 跳过最外圈（精灵自带的描边），只处理内侧 1~2 圈。
    4. 用拜耳抖动决定哪些像素真的被压暗 —— 免得糊成一条硬边，
       也免得把 32x32 的小精灵糊成一团。

    参数
    ----
    img
        原图（不会被修改）。
    darken_map
        颜色 -> 暗色 的映射；给 None 用 :data:`DARKEN_MAP`。
    depth
        最多往里吃几圈。
    intensity
        整体浓度 0~1。

    返回
    ----
    pyxel.Image
        暗化后的新图（同尺寸）。
    """
    w = int(img.width)
    h = int(img.height)
    table = DARKEN_MAP if darken_map is None else darken_map
    px = [[img.pget(x, y) for x in range(w)] for y in range(h)]

    # ---- 四个方向的连续不透明长度
    run_left = [[0] * w for _ in range(h)]
    run_right = [[0] * w for _ in range(h)]
    run_up = [[0] * w for _ in range(h)]
    run_down = [[0] * w for _ in range(h)]
    for y in range(h):
        run = 0
        for x in range(w):
            run = run + 1 if px[y][x] != 0 else 0
            run_left[y][x] = run
        run = 0
        for x in range(w - 1, -1, -1):
            run = run + 1 if px[y][x] != 0 else 0
            run_right[y][x] = run
    for x in range(w):
        run = 0
        for y in range(h):
            run = run + 1 if px[y][x] != 0 else 0
            run_up[y][x] = run
        run = 0
        for y in range(h - 1, -1, -1):
            run = run + 1 if px[y][x] != 0 else 0
            run_down[y][x] = run

    # ---- 生成暗化后的新图
    out = pyxel.Image(w, h)
    for y in range(h):
        for x in range(w):
            color = px[y][x]
            if color == 0:
                continue          # 透明：保持透明（色 0 绝不当可见色）
            out.pset(x, y, color)

            # 找出"朝右下"的那一圈（取更靠外的一圈）
            ring = None
            rr = run_right[y][x]
            if (_FIRST_INNER_RUN <= rr <= depth and rr < run_left[y][x]):
                ring = rr
            rd = run_down[y][x]
            if (_FIRST_INNER_RUN <= rd <= depth and rd < run_up[y][x]):
                ring = rd if ring is None else min(ring, rd)
            if ring is None:
                continue

            density = SHADE_DENSITY.get(ring, 0.3) * float(intensity)
            if bayer_threshold(x, y) >= density:
                continue
            darker = table.get(color)
            if darker is not None and int(darker) != int(color):
                out.pset(x, y, int(darker))
    return out


def footprint(img: pyxel.Image, min_width: int = 6) -> tuple[int, int, int] | None:
    """算出精灵图的「落脚点」：返回 `(中心 x, 地面行 y, 脚宽)`。

    做法：找**最下面一行横向宽度 >= `min_width` 的不透明像素**。

    为什么要加"宽度"门槛
    --------------------
    好几只精灵的**最底一行只是尾巴尖 / 闪电尖**（9 雾尾狐整行只有 1 个像素、
    11 灯火鳅 3 个、18 雷云团 1 个）。直接用"最后一行有像素的地方"会把
    影子放到尾巴尖上，歪掉。取"最后一行足够宽"的位置才是真正的脚。

    返回 None 表示整张图都是透明的。
    """
    w = int(img.width)
    h = int(img.height)
    for y in range(h - 1, -1, -1):
        xs = [x for x in range(w) if img.pget(x, y) != 0]
        if len(xs) >= int(min_width):
            return (int((min(xs) + max(xs)) // 2), int(y), int(len(xs)))
    # 没有一行够宽：退化成"最后一个有像素的行"
    for y in range(h - 1, -1, -1):
        xs = [x for x in range(w) if img.pget(x, y) != 0]
        if xs:
            return (int((min(xs) + max(xs)) // 2), int(y), int(len(xs)))
    return None
