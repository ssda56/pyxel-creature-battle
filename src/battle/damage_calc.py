"""伤害公式与治疗量（《数值设定.md》§4.1 / §4.2）。

落地公式
--------
    攻击力_有效 = int(ATK × atk_mod)            # atk_mod 默认 1.0，被吼叫后 0.75
    基础       = max(0, 攻击力_有效 - 防御力 / 2)
    系数       = 技能威力 / 50.0
    克制       = TYPE_CHART[技能属性][防御方属性]   # "无" 属性恒 1.0
    浮动       = random.uniform(0.90, 1.10)
    伤害       = max(1, int(基础 × 系数 × 克制 × 浮动))

- **不做同属性加成（STAB）**，保持简单。
- 威力 0 的技能（治疗 / 减益）不走此公式，直接返回 0。
- 伤害永不出现 0 或负数。

可调点 O-1（《数值设定.md》§12）
------------------------------
:data:`FIXED_DAMAGE` 默认 0（关闭）。改成 2 即可压缩"抵抗命中"的回合数
（Lv5 抵抗命中从 10 下降到约 6 下）。

本模块**不 import 任何 UI / 引擎模块**。
"""

from __future__ import annotations

import math
import random

from src.battle.type_chart import multiplier

#: 固定伤害项（《数值设定.md》§12 O-1），默认 0 = 关闭
FIXED_DAMAGE: int = 0

#: 伤害浮动区间（《数值设定.md》§4.1）
DAMAGE_VARIANCE: tuple[float, float] = (0.90, 1.10)


def base_damage(attack: int, defense: int, atk_mod: float = 1.0) -> float:
    """基础伤害（未乘技能系数 / 克制 / 浮动）。

    计算式：`max(0, int(攻击 × atk_mod) - 防御 / 2)`。
    """
    effective = int(int(attack) * float(atk_mod))
    return max(0.0, effective - int(defense) / 2)


def damage(attack: int, defense: int, skill_type: str, skill_power: int,
           defend_type: str, atk_mod: float = 1.0,
           rng: random.Random | None = None) -> int:
    """计算一次攻击造成的伤害（《数值设定.md》§4.1）。

    参数
    ----
    attack
        攻击方 ATK。
    defense
        防御方 DEF。
    skill_type
        技能属性（"火"…/"雷"/"无"）。
    skill_power
        技能威力；<= 0 表示治疗 / 减益招式，直接返回 0。
    defend_type
        防御方属性。
    atk_mod
        攻击倍率（默认 1.0，被"吼叫"后 0.75）。
    rng
        随机源；为 None 时用模块级 :mod:`random`。传入
        :class:`random.Random` 可做确定性测试。

    返回
    ----
    int
        伤害值，最小 1。
    """
    if int(skill_power) <= 0:
        return 0
    base = base_damage(int(attack), int(defense), float(atk_mod))
    coef = int(skill_power) / 50.0
    mult = multiplier(skill_type, defend_type)
    lo, hi = DAMAGE_VARIANCE
    roll = random.uniform(lo, hi) if rng is None else rng.uniform(lo, hi)
    return max(1, int(base * coef * mult * roll) + FIXED_DAMAGE)


def expected_damage(attack: int, defense: int, skill_type: str, skill_power: int,
                    defend_type: str, atk_mod: float = 1.0) -> float:
    """**不计浮动**的期望伤害（《数值设定.md》§4.2 节奏表用的就是这个值）。"""
    if int(skill_power) <= 0:
        return 0.0
    base = base_damage(int(attack), int(defense), float(atk_mod))
    return base * (int(skill_power) / 50.0) * multiplier(skill_type, defend_type)


def heal_amount(skill, max_hp: int) -> int:
    """治疗技能的回复量（《数值设定.md》§3 中三个治疗技能）。

    计算式：`max(技能最小回复量, ceil(最大 HP × 回复比例))`。

    参数
    ----
    skill
        :class:`src.data.skill_data.Skill` 实例（需带 min_heal / value）。
    max_hp
        使用者的最大 HP。
    """
    return max(int(skill.min_heal), int(math.ceil(int(max_hp) * float(skill.value))))
