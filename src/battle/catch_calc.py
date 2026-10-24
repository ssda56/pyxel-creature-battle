"""捕捉概率（《数值设定.md》§8）。

    a = (1 - HP当前 / HP最大 × 0.7) × 球倍率 × 种族系数
    成功 = random.random() < a

- 球倍率：精灵球 = 1.0（本版本只有一种球）。
- 种族系数见 :mod:`src.data.species_data` 的 Species.catch_coef。

本模块**不 import 任何 UI / 引擎模块**。
"""

from __future__ import annotations

import random

#: 精灵球倍率（《数值设定.md》§8，本版本只有一种球）
BALL_MULTIPLIER: float = 1.0

#: HP 权重系数：血越少越好抓
HP_FACTOR: float = 0.7


def catch_chance(hp: int, hp_max: int, species_coef: float,
                 ball_mult: float = BALL_MULTIPLIER) -> float:
    """捕捉成功率。

    参数
    ----
    hp
        目标当前 HP。
    hp_max
        目标最大 HP。
    species_coef
        种族系数（见 :mod:`src.data.species_data`）。
    ball_mult
        球倍率，默认 :data:`BALL_MULTIPLIER` = 1.0。

    返回
    ----
    float
        0.0 ~ 1.0 之间的成功率（已夹取）。
    """
    if int(hp_max) <= 0:
        return 0.0
    ratio = int(hp) / int(hp_max)
    chance = (1.0 - ratio * HP_FACTOR) * float(ball_mult) * float(species_coef)
    return max(0.0, min(1.0, chance))


def try_catch(hp: int, hp_max: int, species_coef: float,
              ball_mult: float = BALL_MULTIPLIER,
              rng: random.Random | None = None) -> bool:
    """做一次捕捉判定。

    参数
    ----
    hp / hp_max / species_coef / ball_mult
        同 :func:`catch_chance`。
    rng
        随机源；为 None 时用模块级 :mod:`random`。

    返回
    ----
    bool
        True 表示捕捉成功。
    """
    chance = catch_chance(hp, hp_max, species_coef, ball_mult)
    roll = random.random() if rng is None else rng.random()
    return roll < chance
