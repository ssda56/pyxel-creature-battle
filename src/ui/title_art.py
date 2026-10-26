"""标题画面封面美术（**纯绘制层**，T17 场景化封面）。

职责
----
把「深蓝底 + 三行字」的标题画面做成**一幅有景深的像素风景**，标题压在上面：

    天空渐变（实色带 + 拜耳抖动过渡）+ 星星 + 月牙
      -> 远山剪影（浅蓝，背光面压深，峰顶带雪）
        -> 近山剪影（蓝）
          -> 谷间薄雾（用天空的暖色抖动，把山脚化掉 —— 空气透视）
            -> 针叶林剪影（深绿，高矮不齐，右缘受晚霞照亮）
              -> 草地（林荫暗部 -> 明亮草地 -> 稀疏草丛 / 花 / 石头）
                -> 左右两只精灵（32x32 战斗图 + 脚下投影）夹住标题
                  -> 标题「精灵对战」（黄色 + 橙色立体底边 + 深紫描边，2 倍放大）
                    -> 菜单面板（深蓝板 + 浅灰描边 + 抖动羽化）

本模块**只负责静态美术**：整张封面在第一次需要时**烘焙成一张 240x216 的
整屏图**并缓存，之后每帧标题画面只需要一次 blt。菜单文字 / 光标 / 读档失败
提示随状态变化，由 src.scenes.title_scene 实时绘制。

三条让画面不"廉价"的关键做法
----------------------------
1. **空气透视**：越远的层越浅、越靠上；山脚用一层暖色薄雾化掉，
   而不是让山脊一条条硬切在地平线上。
2. **受光面与背光面**：山只给"朝光的那一侧"描亮，不给整条山脊描边 ——
   整条描边会让山看起来像画出来的帐篷。森林同理，只在树冠右侧撒亮色。
3. **分层抖动**：调色板只有 16 色，相邻两档如果整段做 50% 棋盘抖动，
   远看就是一整片噪点。所以每两档之间是「一段实色带 + 一段抖动过渡」，
   实色带负责干净，抖动段负责没有硬边。

确定性铁律
----------
**一切随机必须是确定性的**：所有"随机感"都来自 _hash01（坐标哈希，纯整数
运算）与固定表。不使用 random、不使用墙钟时间。同一份代码每次烘焙出来的图
**逐像素完全一致** —— 截图回归测试才能跑两次比哈希。

色彩铁律
--------
- **色 0 是 blt(colkey=0) 的透明键，绝不作为可见颜色**；
  整张背景图里**没有任何一个像素是色 0**（天空最暗处是色 1 深蓝）。
- 只使用 src.assets_gen.palette 的**语义常量**，不写裸色号。
"""

from __future__ import annotations

import pyxel

from src.assets_gen import palette, sprite_base
from src.assets_gen.sprites import creatures
from src.ui import dither, text

# ==================================================================== 画面几何
#: 画面尺寸（与 main.py / tests/helpers.py 锁定值一致）
SCREEN_W = 240
SCREEN_H = 216

#: 地平线（天空与草地的分界行）：地平线**这一行**已经是草地。
#:
#: 取 140 是为了给地面留 76px —— 地面太薄的话，精灵与菜单板会把草地
#: 完全吃掉，"前景"这一层就白画了。
HORIZON_Y = 140
#: 草地起始行（= 地平线，单独给个名字便于阅读）
GROUND_Y = HORIZON_Y

#: 标题中心 x 与顶部 y（标题 2 倍放大后是 104x28）
TITLE_CX = SCREEN_W // 2
TITLE_TOP = 10
#: 标题放大倍数（点阵字体整倍放大仍然锐利，不会糊）
TITLE_SCALE = 2

#: 菜单面板（深色板）的矩形：左闭右开
MENU_PANEL_X0 = 62
MENU_PANEL_Y0 = 163
MENU_PANEL_X1 = 178
MENU_PANEL_Y1 = 206

#: 菜单两项的基线。整块（光标 + 最长一项）在面板里**水平居中**：
#: 光标 89 -> 文字 103，「继续游戏」48px 宽 -> 右侧 151，
#: 于是 89~151 的中心正好是 120，左右留白各 29px。
CURSOR_X = 89
MENU_TEXT_X = 103
MENU_FIRST_Y = 172
MENU_STEP = 20


# ==================================================================== 坐标哈希
def _hash01(x: int, y: int, seed: int = 0) -> float:
    """把坐标映射到 [0, 1) 的确定性伪随机数（**纯整数运算**）。

    用途：草点、星点、山脊细节的"随机感"。
    同一个 (x, y, seed) 永远得到同一个值，所以画面可复现。
    """
    n = (int(x) * 374761393 + int(y) * 668265263 + int(seed) * 1274126177) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n = n ^ (n >> 16)
    return (n & 0xFFFFFF) / 16777216.0


def _value_noise(x: int, period: int, seed: int) -> float:
    """一维平滑值噪声：在 period 像素一个的格点上取哈希值，中间平滑插值。"""
    i = int(x) // period
    f = (int(x) % period) / float(period)
    a = _hash01(i, 0, seed)
    b = _hash01(i + 1, 0, seed)
    f = f * f * (3.0 - 2.0 * f)          # smoothstep：接缝处不出现折角
    return a + (b - a) * f


# ==================================================================== 天空
#: 天空渐变的色标：(位置 0~1, 调色板索引)，从上到下。
#:
#: 深蓝（夜）-> 蓝 -> 粉（晚霞）-> 橙 -> 黄（地平线的余晖）。
SKY_STOPS: tuple[tuple[float, int], ...] = (
    (0.00, palette.DEEP_BLUE),
    (0.30, palette.BLUE),
    (0.58, palette.PINK),
    (0.80, palette.ORANGE),
    (1.00, palette.YELLOW),
)

#: 两档之间**前面这么多比例是纯色带**，剩下的才做抖动过渡。
BAND_SOLID = 0.42

#: 星星只画在天空上半部分（下面的晚霞太亮，画星星很假）
STAR_BAND = 0.36

#: 8x8 拜耳矩阵：(值*64)，0~63。
#:
#: 天空渐变用它而不是 dither.BAYER_4X4：4x4 只有 16 级，
#: 跨十几行的渐变会退化成一排排可见的棋盘格点阵；
#: 8x8 有 64 级，同样的跨度下颗粒细一倍，远看是连续渐变。
#: （其余地方仍然统一用 dither 模块的 4x4 —— 那是项目既有风格。）
BAYER_8X8: tuple[tuple[int, ...], ...] = (
    (0, 32, 8, 40, 2, 34, 10, 42),
    (48, 16, 56, 24, 50, 18, 58, 26),
    (12, 44, 4, 36, 14, 46, 6, 38),
    (60, 28, 52, 20, 62, 30, 54, 22),
    (3, 35, 11, 43, 1, 33, 9, 41),
    (51, 19, 59, 27, 49, 17, 57, 25),
    (15, 47, 7, 39, 13, 45, 5, 37),
    (63, 31, 55, 23, 61, 29, 53, 21),
)


def bayer8(x: int, y: int) -> float:
    """8x8 有序抖动阈值，范围 [0, 1)。"""
    return BAYER_8X8[int(y) & 7][int(x) & 7] / 64.0


def sky_segment(t: float) -> tuple[int, int, float]:
    """天空位置 t（0=天顶，1=地平线）落在哪两档之间。

    返回 (暗色, 亮色, 亮色占比)：像素按拜耳阈值决定用哪一色，
    占比 0 是全暗色（纯色带）、占比 1 是全亮色。
    """
    t = 0.0 if t <= 0.0 else (1.0 if t >= 1.0 else float(t))
    for i in range(len(SKY_STOPS) - 1):
        p0, c0 = SKY_STOPS[i]
        p1, c1 = SKY_STOPS[i + 1]
        if t <= p1 or i == len(SKY_STOPS) - 2:
            span = p1 - p0
            frac = 0.0 if span <= 0.0 else (t - p0) / span
            frac = max(0.0, min(1.0, frac))
            if frac <= BAND_SOLID:
                return c0, c0, 0.0
            blend = (frac - BAND_SOLID) / (1.0 - BAND_SOLID)
            return c0, c1, blend
    last = SKY_STOPS[-1][1]
    return last, last, 0.0


def _paint_sky(img: pyxel.Image) -> None:
    """天空：逐行算色标，逐像素用 8x8 拜耳抖动过渡。"""
    last = float(HORIZON_Y - 1)
    for y in range(HORIZON_Y):
        lo, hi, frac = sky_segment(y / last)
        if frac <= 0.0:
            for x in range(SCREEN_W):
                img.pset(x, y, lo)
            continue
        for x in range(SCREEN_W):
            img.pset(x, y, hi if bayer8(x, y) < frac else lo)


def _paint_stars(img: pyxel.Image) -> None:
    """星星：按 12x8 的格子布点，格子内位置与亮度都由坐标哈希决定。

    画两种：单点（暗星，浅灰）与十字（亮星，白 + 一圈浅灰拖尾）。
    """
    limit = int(HORIZON_Y * STAR_BAND)
    cell_w, cell_h = 12, 8
    for gy in range(0, limit, cell_h):
        for gx in range(0, SCREEN_W, cell_w):
            r = _hash01(gx // cell_w, gy // cell_h, 11)
            if r > 0.46:
                continue
            x = gx + int(_hash01(gx, gy, 12) * cell_w)
            y = gy + int(_hash01(gx, gy, 13) * cell_h)
            if not (0 <= x < SCREEN_W and 0 <= y < limit):
                continue
            if r < 0.09:
                # 亮星：十字
                img.pset(x, y, palette.WHITE)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if 0 <= x + dx < SCREEN_W and 0 <= y + dy < limit:
                        img.pset(x + dx, y + dy, palette.LIGHT_GRAY)
            else:
                img.pset(x, y, palette.LIGHT_GRAY)


#: 月牙圆心与半径
MOON_CX, MOON_CY, MOON_R = 200, 27, 11


def _paint_moon(img: pyxel.Image) -> None:
    """右上角一弯月牙：大圆减去一个右上方偏移的小圆（几何相减，边界是干净的弧）。

    第一版用"抖动啃掉一块"做缺口，结果右下角留了个生硬的直角缺块；
    月牙的边界必须是清晰的圆弧，所以改成两个圆的差集。
    """
    cx, cy, r = MOON_CX, MOON_CY, MOON_R
    ix, iy, ir = cx + 5, cy - 4, r - 1
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if not (0 <= x < SCREEN_W and 0 <= y < HORIZON_Y):
                continue
            if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                continue
            if (x - ix) ** 2 + (y - iy) ** 2 <= ir * ir:
                continue
            d = ((x - cx) ** 2 + (y - cy) ** 2) / float(r * r)
            img.pset(x, y, palette.WHITE if d > 0.62 else palette.LIGHT_GRAY)


# ==================================================================== 山脉
#: 远山（浅色，被晚霞照亮）：(峰心 x, 峰高, 半宽)
FAR_PEAKS: tuple[tuple[int, int, int], ...] = (
    (-10, 52, 50),
    (54, 38, 44),
    (112, 60, 56),
    (172, 34, 40),
    (230, 50, 52),
)

#: 近山（介于远山与树林之间）：(峰心 x, 峰高, 半宽)
NEAR_PEAKS: tuple[tuple[int, int, int], ...] = (
    (14, 30, 46),
    (84, 22, 36),
    (152, 34, 50),
    (228, 26, 42),
)

#: 山脚所在的 y（远山更高、近山更低，让两层都有"脚"可藏）
FAR_RIDGE_BASE = HORIZON_Y - 14
NEAR_RIDGE_BASE = HORIZON_Y - 4


def ridge_top(x: int, peaks, base_y: int, seed: int, rugged: float = 1.0) -> int:
    """山脊在列 x 处的顶行 y（越小越高）。

    = 大尺度山峰包络（固定表，负责构图）+ 三层值噪声（负责岩石的崎岖）。
    只有包络的话山脊是一条条直线，远看像一排帐篷。
    """
    top = base_y
    for cx, h, hw in peaks:
        d = abs(int(x) - cx) / float(hw)
        if d >= 1.0:
            continue
        top = min(top, base_y - int(h * (1.0 - d) ** 1.5))
    rough = (
        (_value_noise(x, 29, seed) - 0.5) * 5.0
        + (_value_noise(x, 13, seed + 1) - 0.5) * 2.6
        + (_value_noise(x, 5, seed + 2) - 0.5) * 1.2
    ) * rugged
    return int(round(base_y - (base_y - top) + rough)) if top == base_y else int(round(top + rough))


def _ridge_body(img: pyxel.Image, peaks, base_y: int, seed: int,
                light: int, shade: int, rim: int,
                snow_line: float | None = None,
                snow_min_height: int = 0) -> None:
    """画一条山的剪影，并做「朝光面 / 背光面」分色。

    受光方式是**上亮下暗**：山脊线附近接天光（light），越往下越暗
    （shade）。第一版按"左坡亮、右坡暗"分色，结果每座山中间都有一条
    斜生生的分界线，看着像折纸 —— 现在改用纵向渐变，柔和得多。

    脊线本身**只给迎光的坡**打一像素亮色（rim），不给整条脊线描边：
    整条描边会让山变成"画出来的帐篷轮廓"。
    snow_line 给定时，够高的峰顶按比例撒雪。
    """
    tops = [ridge_top(x, peaks, base_y, seed) for x in range(SCREEN_W)]
    fade = 14.0
    for x in range(SCREEN_W):
        top = tops[x]
        if top >= base_y:
            continue
        for y in range(max(0, top), base_y):
            k = (y - top) / fade             # 0 = 脊线附近，1 = 十几像素以下
            col = light if dither.bayer_threshold(x, y) >= min(0.95, k) else shade
            if snow_line is not None:
                span = base_y - top
                # 只有够高的峰才积雪；雪线附近就已经稀疏了，不糊成白帽子
                if span > snow_min_height and span > 0:
                    k = (y - top) / float(span)
                    if k < snow_line:
                        dens = 0.7 * (1.0 - k / snow_line) ** 1.5
                        if bayer8(x, y) < dens:
                            col = palette.WHITE if k < snow_line * 0.45 else palette.LIGHT_BLUE
            img.pset(x, y, col)
        # 迎光坡的脊线亮一像素
        prev = tops[x - 1] if x > 0 else top
        if prev >= top:
            img.pset(x, top, rim)


def _paint_ridges(img: pyxel.Image) -> None:
    """远山（浅蓝 + 雪）与近山（蓝），远浅近深。"""
    # 远山：蓝（比天空的粉/橙暗，才像逆光剪影）
    _ridge_body(img, FAR_PEAKS, FAR_RIDGE_BASE, 31,
                light=palette.BLUE, shade=palette.DEEP_BLUE,
                rim=palette.LIGHT_BLUE, snow_line=0.16, snow_min_height=24)
    # 近山：整片深蓝（**平涂**）。
    #
    # 这里不能用"黑色"做暗面：色 0 是 blt 的透明键，画成黑色会在贴图上
    # 开一片窟窿，露出上一帧的残留；而深蓝已经是调色板里除黑之外最暗的色，
    # 再往下没有色可以用了，所以近山就做成一整块深蓝剪影，
    # 靠山脊上那条粉色暖光与远山分开。
    _ridge_body(img, NEAR_PEAKS, NEAR_RIDGE_BASE, 47,
                light=palette.DEEP_BLUE, shade=palette.DEEP_BLUE,
                rim=palette.PINK, snow_line=None)


def _paint_haze(img: pyxel.Image) -> None:
    """谷间薄雾：在山脚叠一层"天空的暖色"，让山脚化进地平线（空气透视）。

    没有这层雾，远山会像贴纸一样硬切在地平线上。
    """
    y0 = HORIZON_Y - 16
    for y in range(y0, HORIZON_Y):
        t = (y - y0) / float(HORIZON_Y - y0)
        dens = 0.10 + 0.72 * (t ** 1.6)
        for x in range(SCREEN_W):
            if bayer8(x, y) < dens:
                img.pset(x, y, palette.ORANGE if t < 0.55 else palette.YELLOW)


# ==================================================================== 针叶林
#: 针叶林固定表：(中心 x, 高度, 半宽)。
#:
#: 树与树的间距**小于**树宽，所以它们连成一片林，而不是一根根立着的棍子
#: （第一版就是间距太大、树干露在外面，像插了一排杆子）。
CONIFERS: tuple[tuple[int, int, int], ...] = (
    (-2, 30, 11), (10, 22, 9), (21, 34, 12), (33, 19, 8), (42, 27, 10),
    (54, 16, 7), (63, 31, 11), (75, 21, 9), (86, 14, 6), (95, 26, 10),
    (107, 18, 8), (117, 33, 12), (129, 22, 9), (140, 15, 6), (149, 28, 10),
    (160, 19, 8), (171, 32, 11), (183, 20, 9), (193, 13, 6), (202, 27, 10),
    (214, 17, 8), (224, 30, 11), (236, 21, 9), (245, 26, 10),
)

#: 针叶林的底色：深绿（比草地暗、比近山亮，夹在中间形成第三层深度）
FOREST_BODY = palette.DARK_GREEN
#: 被晚霞照亮的一侧
FOREST_RIM = palette.GREEN
#: 树脚所在的 y（压进草地两个像素，不留缝）
FOREST_BASE = HORIZON_Y + 2


def _paint_forest(img: pyxel.Image) -> None:
    """针叶林剪影：一站到底的深绿林带 + 每棵树描一圈受光边。

    树与树之间高度差很大、左右略有倾斜，所以轮廓是高低起伏的树冠线；
    每棵树**左缘一像素亮绿**把剪影彼此分开，否则整片林子会糊成一堵墙
    （第二版就是这样：一片绿色锯齿墙）。
    """
    for i, (cx, h, hw) in enumerate(CONIFERS):
        apex = FOREST_BASE - h
        skew = (_hash01(i, 0, 91) - 0.5) * 2.0
        prev_half = -1
        for step in range(h):
            y = apex + step
            if not (0 <= y < SCREEN_H):
                continue
            t = step / float(h)
            # 侧边微凹（1.12 次方），比直线更像树冠
            half = int(round(hw * (t ** 1.12)))
            # 枝杈缺口：每 4 行往里收一格，做出针叶层的锯齿
            if step % 4 == 3:
                half = max(0, half - 1)
            mid = cx + skew * t
            left = int(round(mid - half))
            right = int(round(mid + half))
            for x in range(left, right + 1):
                if not (0 <= x < SCREEN_W):
                    continue
                img.pset(x, y, FOREST_BODY)
            # 左缘受光边（光从左上来）：只描刚刚变宽的那一侧，不做成实线
            if 0 <= left < SCREEN_W and (prev_half < 0 or half >= prev_half):
                img.pset(left, y, FOREST_RIM)
            prev_half = half


# ==================================================================== 草地
#: 精灵脚踩的地面行
CREATURE_FEET_Y = 182
#: 精灵图的显示 x（32x32）
CREATURE_LEFT_X = 18
CREATURE_RIGHT_X = 190
#: 精灵图顶行
CREATURE_TOP = CREATURE_FEET_Y - 32

#: 草地明暗的两个来源（**只用行号决定，行内均匀抖动**，绝不撒随机点）
#:
#: 林荫：地平线往下多少行之内有树林投下的影子，以及影子最浓处的浓度
GROUND_SHADOW_ROWS = 10
GROUND_SHADOW_MAX = 0.95
#: 前景：画面最下方多少行开始做透视压暗，以及最底部的浓度
GROUND_NEAR_ROWS = 14
GROUND_NEAR_MAX = 0.62
#: **压暗密度下限**：低于这个密度的行，一个深绿像素都不画。
#:
#: 这一条是"草地发脏"的真正解药。有序抖动在**低密度**区间落下来的是
#: 孤立单像素，按 8x8 拜耳矩阵排成一张稀疏的规则点阵 —— 放大 6 倍看得
#: 清清楚楚，就是一地小黑点，而不是"阴影"。
#: 把 0.22 以下的密度直接归零之后，明暗只剩两段：干净的纯中绿，
#: 以及足够密、读起来是"暗带"的抖动区，中间不会再出现游离的脏点。
GROUND_DARK_FLOOR = 0.22

#: 装饰花的固定位置：(x, y, 花瓣色) —— 花芯固定黄色
FLOWERS: tuple[tuple[int, int, int], ...] = (
    (9, 197, palette.RED),
    (29, 211, palette.WHITE),
    (47, 193, palette.YELLOW),
    (55, 172, palette.RED),
    (183, 179, palette.WHITE),
    (197, 210, palette.RED),
    (219, 195, palette.YELLOW),
    (232, 169, palette.WHITE),
    (109, 210, palette.RED),
    (127, 209, palette.WHITE),
)

#: 石头：(中心 x, 中心 y, 半径)
ROCKS: tuple[tuple[int, int, int], ...] = (
    (36, 189, 5),
    (205, 198, 4),
    (5, 165, 3),
)

#: 精灵脚下投影的椭圆层（烘焙成小图，再 blt）
SHADOW_LAYERS: tuple[tuple[int, int, int, float], ...] = (
    (16, 6, palette.DARK_GREEN, 1.0),
    (11, 4, palette.DEEP_BLUE, 0.85),
    (6, 3, palette.DEEP_BLUE, 1.0),
)


def _blocked(x: int, y: int, pad: int = 4) -> bool:
    """这个像素是否落在"不许撒草"的保留区（菜单板 / 精灵脚下）。"""
    if (MENU_PANEL_X0 - pad <= x < MENU_PANEL_X1 + pad
            and MENU_PANEL_Y0 - pad <= y <= MENU_PANEL_Y1):
        return True
    for sx in (CREATURE_LEFT_X, CREATURE_RIGHT_X):
        if (sx - pad <= x < sx + 32 + pad
                and CREATURE_TOP - pad <= y <= CREATURE_FEET_Y + 3):
            return True
    return False


def _ground_dark_density(y: int) -> float:
    """草地在第 y 行要压暗多少（0 = 纯中绿，1 = 全深绿）。

    只有两处该暗，而且是**连续渐变**，不是散点：

    1. **林荫**：树林在地平线以下投下一道影子，越往下越淡，到
       GROUND_SHADOW_ROWS 行为止；
    2. **前景**：画面最下方离眼睛最近，按透视压暗一档，越靠下越暗。

    两处取 **max** 而不是相加 —— 相加会把两道暗部重叠的区域压成一片死黑，
    那正是"草地发脏"的根源。
    """
    # 林荫：顶部最浓，单调减到 0
    shadow = 0.0
    if y < GROUND_Y + GROUND_SHADOW_ROWS:
        t = (y - GROUND_Y) / float(GROUND_SHADOW_ROWS)
        shadow = GROUND_SHADOW_MAX * (1.0 - t) ** 1.2
    # 前景：底部最浓，向上单调减到 0
    near = 0.0
    top = SCREEN_H - GROUND_NEAR_ROWS
    if y >= top:
        t = (y - top) / float(GROUND_NEAR_ROWS)
        near = GROUND_NEAR_MAX * t ** 1.1
    dens = max(shadow, near)
    # 低密度一律归零：宁可少一段过渡，也不要一地游离的深色单像素
    return dens if dens >= GROUND_DARK_FLOOR else 0.0


def _paint_ground(img: pyxel.Image) -> None:
    """草地：一整块干净的中绿，只在两处做均匀的抖动明暗。

    设计要求是「退后看是一块干净的绿」，所以这里**刻意什么都不撒**：

    - 不再有随机深绿颗粒（上一版用 8x8 阈值 0.86 铺了 14% 的噪点，
      再叠 700 个散点，草地糊成泥地）；
    - 明暗**只由行号决定**，同一行内每个像素的压暗概率完全相同，
      所以过渡是均匀的抖动条纹，不会出现孤立的黑点；
    - 视线焦点交给有形状的东西：草丛、花、石头。

    调色板里除了 GREEN(4) 和 DARK_GREEN(3) 没有第三种草色，
    所以"中间调"没法用另一个色号来做 —— 只能靠抖动的密度来表达深浅。
    """
    for y in range(GROUND_Y, SCREEN_H):
        dens = _ground_dark_density(y)
        if dens <= 0.0:
            for x in range(SCREEN_W):
                img.pset(x, y, palette.GREEN)
            continue
        for x in range(SCREEN_W):
            img.pset(x, y,
                     palette.DARK_GREEN if bayer8(x, y) < dens else palette.GREEN)

    # 草丛：成簇的浅绿"V"形草，是草地上唯一的视觉焦点之一
    for gy in range(GROUND_Y + 14, SCREEN_H - 2, 12):
        for gx in range(0, SCREEN_W, 16):
            if _hash01(gx, gy, 51) > 0.68:
                continue
            bx = gx + int(_hash01(gx, gy, 52) * 14)
            by = gy + int(_hash01(gx, gy, 53) * 10)
            if not (GROUND_Y + 14 <= by < SCREEN_H - 2) or _blocked(bx, by):
                continue
            _paint_tuft(img, bx, by)

    _paint_rocks(img)
    _paint_flowers(img)


def _paint_tuft(img: pyxel.Image, bx: int, by: int) -> None:
    """一簇草：三根浅绿叶 + 底下一点深绿阴影。"""
    for dx, up in ((-2, 2), (0, 3), (2, 2)):
        x = bx + dx
        for k in range(up):
            y = by - k
            if 0 <= x < SCREEN_W and GROUND_Y <= y < SCREEN_H:
                img.pset(x, y, palette.LIGHT_GREEN)
    if 0 <= bx < SCREEN_W and GROUND_Y <= by + 1 < SCREEN_H:
        img.pset(bx, by + 1, palette.DARK_GREEN)


def _paint_rocks(img: pyxel.Image) -> None:
    """石头：灰色块面 + 左上浅灰高光 + 右下深蓝暗部。"""
    for cx, cy, r in ROCKS:
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if not (GROUND_Y <= y < SCREEN_H and 0 <= x < SCREEN_W):
                    continue
                d = ((x - cx) / r) ** 2 + ((y - cy) / (r * 0.72)) ** 2
                if d > 1.0:
                    continue
                col = palette.GRAY
                if (x - cx) + (y - cy) < -r * 0.45:
                    col = palette.LIGHT_GRAY
                elif (x - cx) + (y - cy) > r * 0.80:
                    col = palette.DEEP_BLUE
                img.pset(x, y, col)


def _paint_flowers(img: pyxel.Image) -> None:
    """花：十字花瓣 + 黄色花芯，下面两片浅绿叶。"""
    for cx, cy, petal in FLOWERS:
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            x, y = cx + dx, cy + dy
            if 0 <= x < SCREEN_W and GROUND_Y <= y < SCREEN_H:
                img.pset(x, y, petal)
        img.pset(cx, cy, palette.YELLOW)
        for dx, dy in ((-1, 1), (1, 2)):
            x, y = cx + dx, cy + dy
            if 0 <= x < SCREEN_W and GROUND_Y <= y < SCREEN_H:
                img.pset(x, y, palette.LIGHT_GREEN)


# ==================================================================== 精灵
#: 封面左右两只精灵（战斗图 id）：左火右水
CREATURE_LEFT = 1
CREATURE_RIGHT = 2


def _paint_creature(img: pyxel.Image, species_id: int, x: int) -> None:
    """把一只精灵连同影子画到背景图上。

    影子用 dither.footprint 找真正的落脚点 —— 好几只精灵最底一行
    只是尾巴尖，直接贴在图片底边会让影子飘在尾巴上。
    """
    src = sprite_base.bake(creatures.CREATURE_BATTLE[species_id])
    y = CREATURE_FEET_Y - src.height
    info = dither.footprint(src)
    foot_x = info[0] if info else src.width // 2
    foot_y = info[1] if info else src.height - 1
    shadow = dither.bake_dither_ellipse(SHADOW_LAYERS)
    img.blt(x + foot_x - shadow.width // 2, y + foot_y - shadow.height // 2,
            shadow, 0, 0, shadow.width, shadow.height, 0)
    img.blt(x, y, src, 0, 0, src.width, src.height, 0)


def _paint_creatures(img: pyxel.Image) -> None:
    _paint_creature(img, CREATURE_LEFT, CREATURE_LEFT_X)
    _paint_creature(img, CREATURE_RIGHT, CREATURE_RIGHT_X)


# ==================================================================== 标题
def render_title(s: str = "精灵对战", face: int = palette.YELLOW,
                 bevel: int = palette.ORANGE,
                 outline: int = palette.DARK_PURPLE,
                 scale: int = TITLE_SCALE) -> pyxel.Image:
    """把标题渲染成一张带描边 + 立体边的整倍放大图。

    做法
    ----
    1. 用 src.ui.text 的字体把字画进一张小图，拿到**字形遮罩**；
    2. 每个字形像素：正下方还是字形 -> 面色，正下方是空的 -> **底边**
       （这一圈换成暖色，字的下面像被火光照亮，不是死板的单色）；
    3. 在字形外面扩**一圈**描边（深紫），所以标题压在任何背景上都有边；
    4. 整倍放大（默认 2 倍）—— 点阵字体整倍放大仍然落在整像素上，不会糊。

    返回的小图背景是色 0，用 blt(..., colkey=0) 贴上画面。
    """
    font = text.init_font()
    w = font.text_width(s)
    h = text.FONT_SIZE

    mask = pyxel.Image(w, h)
    mask.cls(0)
    mask.text(0, 0, s, palette.WHITE, font)

    pad = 1
    bw, bh = w + pad * 2, h + pad * 2
    body = pyxel.Image(bw, bh)
    body.cls(0)
    for y in range(h):
        for x in range(w):
            if mask.pget(x, y) == 0:
                continue
            below = (y + 1 < h) and mask.pget(x, y + 1) != 0
            body.pset(x + pad, y + pad, face if below else bevel)

    # 描边：所有"空着但贴着字形"的像素
    out = pyxel.Image(bw, bh)
    out.cls(0)
    for y in range(bh):
        for x in range(bw):
            c = body.pget(x, y)
            if c != 0:
                out.pset(x, y, c)
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < bw and 0 <= ny < bh and body.pget(nx, ny) != 0:
                    out.pset(x, y, outline)
                    break

    if scale <= 1:
        return out
    big = pyxel.Image(bw * scale, bh * scale)
    big.cls(0)
    for y in range(bh):
        for x in range(bw):
            c = out.pget(x, y)
            if c == 0:
                continue
            for dy in range(scale):
                for dx in range(scale):
                    big.pset(x * scale + dx, y * scale + dy, c)
    return big


def _paint_title(img: pyxel.Image) -> None:
    """标题：居中压在天空上。"""
    title = render_title()
    x = TITLE_CX - title.width // 2
    img.blt(x, TITLE_TOP, title, 0, 0, title.width, title.height, 0)


# ==================================================================== 菜单面板
def _paint_menu_panel(img: pyxel.Image) -> None:
    """菜单面板：深蓝板 + 浅灰描边 + 外圈抖动羽化 + 板下一团软阴影。

    为什么要一条板：菜单直接压在草地上时，白字落在浅绿草叶上会读不清；
    压一条深色板之后对比度是稳定的，与背景画到哪一层无关。
    """
    x0, y0, x1, y1 = MENU_PANEL_X0, MENU_PANEL_Y0, MENU_PANEL_X1, MENU_PANEL_Y1

    # 板下的软阴影：先压暗一圈，板子才"坐"在草地上而不是浮着
    for y in range(y1 - 2, min(SCREEN_H, y1 + 6)):
        drop = 0.85 - (y - (y1 - 2)) * 0.16
        for x in range(x0 - 4, x1 + 4):
            if 0 <= x < SCREEN_W and drop > 0 and dither.bayer_threshold(x, y) < drop:
                img.pset(x, y, palette.DARK_GREEN)

    # 外圈羽化：越往外抖动得越稀，板子"化"进背景里
    for pad, dens in ((3, 0.22), (2, 0.45), (1, 0.80)):
        for y in range(y0 - pad, y1 + pad):
            for x in range(x0 - pad, x1 + pad):
                if not (0 <= x < SCREEN_W and 0 <= y < SCREEN_H):
                    continue
                inner = (x0 - pad + 1 <= x < x1 + pad - 1
                         and y0 - pad + 1 <= y < y1 + pad - 1)
                if inner:
                    continue
                if dither.bayer_threshold(x, y) < dens:
                    img.pset(x, y, palette.DEEP_BLUE)

    # 实心板：深蓝打底，顶部三行压成深紫，板子本身有层次。
    # （不能用色 0 黑：那是 blt 的透明键，会在板上开三个洞。）
    for y in range(y0, y1):
        edge = palette.DARK_PURPLE if y < y0 + 3 else palette.DEEP_BLUE
        for x in range(x0, x1):
            img.pset(x, y, edge)

    # 描边：浅灰外框；内侧再压一条深紫细线做层次
    for x in range(x0, x1):
        img.pset(x, y0, palette.LIGHT_GRAY)
        img.pset(x, y1 - 1, palette.LIGHT_GRAY)
    for y in range(y0, y1):
        img.pset(x0, y, palette.LIGHT_GRAY)
        img.pset(x1 - 1, y, palette.LIGHT_GRAY)
    for x in range(x0 + 2, x1 - 2):
        img.pset(x, y0 + 1, palette.DARK_PURPLE)


# ==================================================================== 烘焙 / 绘制
_CACHE: dict[str, pyxel.Image] = {}


def bake_background() -> pyxel.Image:
    """烘焙整张封面（含标题 / 精灵 / 菜单面板），**首次调用后缓存**。

    整张图一次性画好，title_scene 每帧只要一次 blt，
    所以每帧绘制耗时与场景复杂度无关。
    """
    cached = _CACHE.get("background")
    if cached is not None:
        return cached
    img = pyxel.Image(SCREEN_W, SCREEN_H)
    img.cls(palette.DEEP_BLUE)
    _paint_sky(img)
    _paint_stars(img)
    _paint_moon(img)
    _paint_ridges(img)
    _paint_haze(img)
    _paint_ground(img)
    _paint_forest(img)
    _paint_creatures(img)
    _paint_title(img)
    _paint_menu_panel(img)
    _CACHE["background"] = img
    return img


def draw_background() -> None:
    """把烘焙好的封面贴到屏幕上（每帧一次 blt）。"""
    img = bake_background()
    pyxel.blt(0, 0, img, 0, 0, SCREEN_W, SCREEN_H, 0)


def draw_hint(cy: int, s: str, color: int = palette.YELLOW) -> None:
    """读档失败提示：先垫一块深色小板，再画黄字（保证在任何背景上都读得清）。"""
    w = text.width(s)
    x0 = SCREEN_W // 2 - w // 2 - 5
    y0 = cy - 4
    for y in range(y0, y0 + 20):
        for x in range(x0, x0 + w + 10):
            if 0 <= x < SCREEN_W and 0 <= y < SCREEN_H:
                pyxel.pset(x, y, palette.DEEP_BLUE)
    for x in range(x0, x0 + w + 10):
        if 0 <= x < SCREEN_W:
            pyxel.pset(x, y0, palette.LIGHT_GRAY)
            pyxel.pset(x, y0 + 19, palette.LIGHT_GRAY)
    text.draw_center(SCREEN_W // 2, cy, s, color)


def draw_menu_item(x: int, y: int, s: str, selected: bool) -> None:
    """画一项菜单：选中黄字加光标三角，未选中白字。"""
    text.draw(x, y, s, palette.YELLOW if selected else palette.WHITE)
    if selected:
        pyxel.tri(
            CURSOR_X, y + 1,
            CURSOR_X, y + 11,
            CURSOR_X + 8, y + 6,
            palette.YELLOW,
        )
