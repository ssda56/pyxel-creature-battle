"""批 1（地图探索）测试辅助。

给 tests/test_field_*.py 共用：建一个 FieldScene + 假输入，手动跑帧。
"""

from __future__ import annotations

import os
import random
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests import helpers  # noqa: E402


def make_field(map_id: int = 1, script=None, x=None, y=None, facing=None,
               seed=None):
    """建一个跑在 FieldScene 上的 Game。

    返回 (game, scene)：
    - game.input 是 FakeInput，可以继续 queue() 追加脚本；
    - scene 是当前场景（FieldScene）。

    `seed` 给定时把 `game.wild_rng` 换成 `random.Random(seed)`，刷怪与游走
    因此完全可复现。**截图测试必须传 seed**，否则同一个用例两次跑出来的图不同，
    提交进仓库的截图会一直产生无意义 diff。
    """
    helpers.ensure_init()

    from src.core.game import Game
    from src.core.input import FakeInput
    from src.scenes.field_scene import FieldScene

    game = Game(input=FakeInput(script=script))
    if seed is not None:
        game.wild_rng = random.Random(seed)
    scene = FieldScene(game)
    kwargs = {"map_id": map_id}
    if x is not None:
        kwargs["x"] = x
    if y is not None:
        kwargs["y"] = y
    if facing is not None:
        kwargs["facing"] = facing
    game.scenes.replace(scene, **kwargs)
    return game, scene


def run(game, frames: int = 1) -> None:
    """跑若干帧（先 update 再 draw，和真实游戏一致）。"""
    for _ in range(frames):
        game.update()
        game.draw()


def shot_path(name: str) -> str:
    """docs/shots 下的截图路径。"""
    return os.path.join(helpers.PROJECT_ROOT, "docs", "shots", name)
