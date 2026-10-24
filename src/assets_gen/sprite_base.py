"""字符画烘焙器（规划文档 §9.1 方案 D）。

数据流：字符画（list[str]） -> `SpriteMatrix.bake()` -> `pyxel.Image` -> 全局 REGISTRY
启动时 `bake_all()` 一次性烘焙全部素材，运行期只做 `pyxel.blt()`，零解析开销。

约定
----
- 字符 `'.'` 表示**透明**，烘焙时**跳过不写像素**（Image 初始值 0，
  配合 `pyxel.blt(..., colkey=0)` 即为透明）。
- 其他字符必须出现在该精灵的 palette 里，否则抛 KeyError。
- 精灵描边统一用**色 5（深紫）**：因为 `colkey=0` 会把色 0 变透明，
  黑色描边会整圈消失（已实测）。
- 每一行字符画长度必须一致，否则抛 `SpriteRowLengthError`（ValueError 子类），
  异常消息里带**精灵名 + 行号**。
"""

from __future__ import annotations

import pyxel


class SpriteRowLengthError(ValueError):
    """字符画各行长度不一致。"""


class SpriteMatrix:
    """一张字符画。

    :param name: 精灵名（REGISTRY 的键，必须全局唯一）
    :param rows: 字符画，每行一个字符串，长度必须一致
    :param palette: 字符 -> 调色板索引；`'.'` 约定为透明（None）
    """

    def __init__(self, name: str, rows: list[str], palette: dict[str, int]):
        self.name = name
        self.rows = [str(r) for r in rows]
        self.palette = dict(palette)

    # ------------------------------------------------------------ 尺寸
    @property
    def width(self) -> int:
        """字符画宽度（第一行的长度）。"""
        return len(self.rows[0]) if self.rows else 0

    @property
    def height(self) -> int:
        """字符画高度（行数）。"""
        return len(self.rows)

    # ------------------------------------------------------------ 校验
    def validate(self) -> None:
        """校验各行长度一致；不一致抛 SpriteRowLengthError。"""
        if not self.rows:
            raise SpriteRowLengthError(f"精灵 '{self.name}' 的字符画是空的")
        width = len(self.rows[0])
        for lineno, row in enumerate(self.rows, start=1):
            if len(row) != width:
                raise SpriteRowLengthError(
                    f"精灵 '{self.name}' 第 {lineno} 行长度 {len(row)} != 第 1 行长度 {width}"
                    f"（字符画每行长度必须一致）"
                )

    # ------------------------------------------------------------ 烘焙
    def bake(self) -> pyxel.Image:
        """把字符画烘焙成 pyxel.Image。行宽不一致时抛异常。"""
        self.validate()
        image = pyxel.Image(self.width, self.height)
        for y, row in enumerate(self.rows):
            for x, ch in enumerate(row):
                if ch == ".":
                    continue  # 透明：不写像素
                if ch not in self.palette:
                    raise KeyError(
                        f"精灵 '{self.name}' 第 {y + 1} 行第 {x + 1} 列的字符 {ch!r} 不在 palette 中"
                    )
                col = self.palette[ch]
                if col is None:
                    continue
                image.pset(x, y, col)
        return image

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<SpriteMatrix {self.name} {self.width}x{self.height}>"


#: 全局素材库：精灵名 -> 已烘焙的 pyxel.Image
REGISTRY: dict[str, pyxel.Image] = {}


def bake(sprite: SpriteMatrix) -> pyxel.Image:
    """烘焙精灵并放进 REGISTRY（**幂等**：同名素材不会重复烘焙）。"""
    if sprite.name in REGISTRY:
        return REGISTRY[sprite.name]
    image = sprite.bake()
    REGISTRY[sprite.name] = image
    return image


def get(name: str) -> pyxel.Image:
    """按名字取已烘焙的素材；未烘焙时抛 KeyError。"""
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"素材 '{name}' 尚未烘焙，请先调用 sprite_base.bake_all()"
        ) from None


def bake_all() -> None:
    """烘焙全部素材（启动时调用一次）。"""
    from src.assets_gen.sprites import ALL_SPRITES

    for sprite in ALL_SPRITES:
        bake(sprite)


# ==================================================================== 绘图辅助
class Canvas:
    """字符画辅助画布。

    供占位素材用几何图元拼装（椭圆 / 矩形 / 三角 / 直线），
    仍然产出标准的 `list[str]` 字符画，可以直接交给 `SpriteMatrix`。
    """

    def __init__(self, width: int, height: int, fill: str = "."):
        self.width = width
        self.height = height
        self.grid = [[fill] * width for _ in range(height)]

    # ------------------------------------------------------------ 图元
    def pixel(self, x: int, y: int, ch: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = ch

    def rect(self, x: int, y: int, w: int, h: int, ch: str) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.pixel(xx, yy, ch)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, ch: str) -> None:
        if rx <= 0 or ry <= 0:
            return
        for y in range(self.height):
            for x in range(self.width):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.pixel(x, y, ch)

    def triangle(self, p1, p2, p3, ch: str) -> None:
        (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3

        def cross(ax, ay, bx, by, cx, cy):
            return (ax - cx) * (by - cy) - (bx - cx) * (ay - cy)

        for y in range(self.height):
            for x in range(self.width):
                d1 = cross(x, y, x1, y1, x2, y2)
                d2 = cross(x, y, x2, y2, x3, y3)
                d3 = cross(x, y, x3, y3, x1, y1)
                has_neg = d1 < 0 or d2 < 0 or d3 < 0
                has_pos = d1 > 0 or d2 > 0 or d3 > 0
                if not (has_neg and has_pos):
                    self.pixel(x, y, ch)

    def line(self, x1: int, y1: int, x2: int, y2: int, ch: str) -> None:
        dx, dy = abs(x2 - x1), -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        while True:
            self.pixel(x1, y1, ch)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy

    # ------------------------------------------------------------ 描边
    def outline(self, ch: str = "K") -> None:
        """给所有非透明区域外面加一圈描边。"""
        targets = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if self.grid[y][x] != "."
        ]
        for x, y in targets:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if self.grid[ny][nx] == ".":
                        self.grid[ny][nx] = ch

    # ------------------------------------------------------------ 输出
    def rows(self) -> list[str]:
        return ["".join(row) for row in self.grid]
