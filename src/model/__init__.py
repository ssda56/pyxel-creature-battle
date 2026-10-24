"""领域模型层（T3a）。

- :mod:`src.model.creature`：精灵个体（战斗单位）。
- :mod:`src.model.player`：玩家（队伍 / 仓库 / 背包 / 金币）。

**硬性约束**：本包内的模块一律**不 import pyxel 或任何 UI 模块**，
必须能脱离 Pyxel 直接 import 与单测。
"""

from src.model.creature import Creature
from src.model.player import Player

__all__ = ["Creature", "Player"]
