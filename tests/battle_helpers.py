"""战斗场景测试辅助（tests/test_battle_*.py 共用）。

提供：

- :func:`make_battle`：建一个跑着 BattleScene 的 Game（可注入固定随机种子）；
- :func:`press` / :func:`idle`：手动帧（注入一次按键 / 空跑一帧）；
- :func:`advance_until`：连按确认键直到条件成立。
"""

from __future__ import annotations

import os
import random
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests import helpers  # noqa: E402

#: 精灵球道具 ID（《数值设定.md》§7.1）
BALL_ID = 1


def make_battle(enemy_species: int = 3, enemy_level: int = 5, seed=None,
                on_end=None, party=None, player=None):
    """建一个跑着 BattleScene 的 Game。

    返回 (game, scene, enemy)。

    - `seed`：给场景注入 `random.Random(seed)`，整场战斗可复现；
    - `party`：替换 `game.player.party`（用于构造特定等级 / 队伍）；
    - `on_end`：战斗结束的回调（T4 要用的钩子）。
    """
    helpers.ensure_init()

    from src.core.game import Game
    from src.core.input import FakeInput
    from src.data import species_data as sd
    from src.model import Creature, Player
    from src.scenes.battle_scene import BattleScene

    game = Game(input=FakeInput())
    if game.player is None:
        # T5 起 Game.player 初值是 None（还没开局）。战斗场景自己也会兜底建一个，
        # 这里先装上，行为与 T5 之前完全一致。
        game.player = Player.new_game(sd.STARTER_IDS[0])
    if player is not None:
        game.player = player
    if party is not None:
        game.player.party = list(party)
    enemy = Creature(enemy_species, level=enemy_level)
    scene = BattleScene(
        game, enemy, on_end=on_end,
        rng=random.Random(seed) if seed is not None else None,
    )
    game.scenes.replace(scene)
    return game, scene, enemy


def press(game, action: str, frames: int = 1) -> None:
    """注入一次按键并跑对应帧数。"""
    from src.core.input import FakeInput

    game.input = FakeInput(script=[{action: frames}])
    for _ in range(frames):
        game.update()
        game.draw()


def idle(game, frames: int = 1) -> None:
    """不按任何键跑若干帧。"""
    from src.core.input import FakeInput

    game.input = FakeInput()
    for _ in range(frames):
        game.update()
        game.draw()


def advance_until(game, predicate, limit: int = 400) -> bool:
    """连按确认键直到 predicate() 成立。

    注意：只在「等待输入」的状态下才按确认键；
    五指令 / 技能列表这类状态会先空跑一帧，避免误触发指令。
    """
    from src.scenes.battle_scene import BattleScene

    scene = game.scenes.current
    for _ in range(limit):
        if predicate():
            return True
        if isinstance(scene, BattleScene):
            if scene.state in (BattleScene.MESSAGE, BattleScene.INTRO,
                               BattleScene.CATCH, BattleScene.RESULT):
                press(game, "confirm")
                continue
            idle(game, 1)
            continue
        press(game, "confirm")
    return predicate()
