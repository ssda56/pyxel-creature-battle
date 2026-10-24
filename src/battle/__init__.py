"""战斗数值层（T3a）。

本包只放**纯计算**的战斗规则，不含任何界面 / 场景代码：

- :mod:`src.battle.type_chart`：属性克制表（《数值设定.md》§2）。
- :mod:`src.battle.damage_calc`：伤害公式与治疗量（《数值设定.md》§4.1）。
- :mod:`src.battle.catch_calc`：捕捉概率（《数值设定.md》§8）。

**硬性约束**：本包内的模块一律**不 import pyxel 或任何 UI 模块**，
必须能脱离 Pyxel 直接 import 与单测。
"""
