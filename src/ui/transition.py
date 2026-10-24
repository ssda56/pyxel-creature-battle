"""画面淡入淡出（转场）。

用途
----
地图切换、T3 战斗转场都复用本模块。淡出 -> 换场景 -> 淡入。

用法
----
    fade = Fade()

    # 渐黑，结束时执行 on_done
    fade.start_out(15, on_done=lambda: switch_scene())

    # 每帧
    fade.update()      # 推进一帧，结束时触发 on_done
    fade.draw()        # 画在画面最上层

实现
----
Pyxel 2.9.9 没有 alpha 混合，pyxel.dither 的签名也不可用，所以这里用
**4x4 有序抖动（Bayer）矩阵**逐像素描黑：

- 黑度分 16 档（0 = 全亮，16 = 全黑），每帧黑度按 1/16 递增/递减，
  **肉眼能看到连续渐变**（不是一步黑到底）；
- 每一档要描黑的像素位置都预先算好（_BLACK_X），绘制时只对黑像素
  调用 pyxel.pset，帧开销足够小（30fps 下 < 20ms）。
"""

from __future__ import annotations

import pyxel

#: 画面宽度（与 main.py 锁定值一致）
SCREEN_W = 240
#: 画面高度（与 main.py 锁定值一致）
SCREEN_H = 216

#: 黑度档数上限（0 = 全亮，16 = 全黑）
MAX_STEPS = 16

#: 4x4 有序抖动矩阵（Bayer matrix），值 0~15，越小越先变黑
_BAYER4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def _build_black_table() -> tuple[tuple[tuple[int, ...], ...], ...]:
    """预计算每一档黑度、每一行类别下需要描黑的 x 坐标。

    返回 table[level][row_class] = 该行要涂黑的 x 坐标元组。
    """
    table: list[tuple[tuple[int, ...], ...]] = []
    for level in range(MAX_STEPS + 1):
        rows: list[tuple[int, ...]] = []
        for row in _BAYER4:
            xs = tuple(x for x in range(SCREEN_W) if row[x & 3] < level)
            rows.append(xs)
        table.append(tuple(rows))
    return tuple(table)


#: 预计算的描黑像素表
_BLACK_X = _build_black_table()


class Fade:
    """可复用的淡入淡出。

    状态
    ----
    - level：当前黑度 0~16（0 全亮，16 全黑）
    - is_active：是否正在播放
    - is_black：是否已经完全变黑

    回调
    ----
    start_out / start_in 的 on_done 在**最后一帧 update() 时**调用一次
    （调用后自动清空，不会重复触发）。
    """

    def __init__(self) -> None:
        self.active = False
        #: "out" 渐黑 / "in" 渐亮 / "none" 未播放
        self.mode = "none"
        self.total = 0
        self.frames_left = 0
        self.level = 0
        self.on_done = None

    # ------------------------------------------------------------ 控制
    def start_out(self, frames: int = 15, on_done=None) -> None:
        """开始渐黑（画面变暗）。on_done 在变全黑时调用。"""
        self.active = True
        self.mode = "out"
        self.total = max(1, int(frames))
        self.frames_left = self.total
        self.level = 0
        self.on_done = on_done

    def start_in(self, frames: int = 15, on_done=None) -> None:
        """开始渐亮（从全黑恢复）。on_done 在完全亮起时调用。"""
        self.active = True
        self.mode = "in"
        self.total = max(1, int(frames))
        self.frames_left = self.total
        self.level = MAX_STEPS
        self.on_done = on_done

    def stop(self) -> None:
        """立刻结束淡入淡出（清零黑度，不触发回调）。"""
        self.active = False
        self.mode = "none"
        self.frames_left = 0
        self.level = 0
        self.on_done = None

    # ------------------------------------------------------------ 每帧
    def update(self) -> None:
        """推进一帧；播放结束时调用 on_done 一次。"""
        if not self.active:
            return
        self.frames_left -= 1
        if self.mode == "out":
            # 黑度递增：第 1 帧就有一点点黑，最后一帧全黑
            self.level = MAX_STEPS - (MAX_STEPS * self.frames_left) // self.total
        else:
            # 黑度递减：最后一帧全亮
            self.level = (MAX_STEPS * self.frames_left) // self.total
        if self.frames_left <= 0:
            was_in = self.mode == "in"
            self.active = False
            self.mode = "none"
            if was_in:
                self.level = 0
            callback = self.on_done
            self.on_done = None
            if callback is not None:
                callback()

    def draw(self) -> None:
        """把当前黑度画在画面最上层（叠在所有内容之上）。"""
        level = self.level
        if level <= 0:
            return
        if level > MAX_STEPS:
            level = MAX_STEPS
        table = _BLACK_X[level]
        for y in range(SCREEN_H):
            xs = table[y & 3]
            if not xs:
                continue
            for x in xs:
                pyxel.pset(x, y, 0)

    # ------------------------------------------------------------ 查询
    @property
    def is_active(self) -> bool:
        """是否正在播放淡入淡出。"""
        return self.active

    @property
    def is_black(self) -> bool:
        """画面是否已完全变黑。"""
        return self.level >= MAX_STEPS
