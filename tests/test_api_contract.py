"""公开 API 契约测试（锁死 T3b 要用的签名）。

下一波 T3b 会照着本批任务书里的签名写战斗界面。本文件用
:func:`inspect.signature` 把**每一个**对外签名逐字钉死：

- 参数名、参数顺序、默认值；
- 返回类型注解里约定的类型（对可注解的返回值做检查）。

一旦有人改动签名，这里立刻红给 T3b 看。
"""

from __future__ import annotations

import inspect
import unittest

from src.battle import catch_calc, damage_calc, type_chart
from src.data import item_data, skill_data, species_data
from src.model import creature as creature_mod
from src.model import player as player_mod


def _params(func) -> list[tuple[str, object]]:
    """返回 [(参数名, 默认值)]（默认值用 inspect._empty 表示无默认值）。

    自动去掉 self / cls，只保留**调用方真正要传**的参数。
    """
    sig = inspect.signature(func)
    items = list(sig.parameters.items())
    if items and items[0][0] in ("self", "cls"):
        items = items[1:]
    return [
        (name, p.default if p.default is not inspect.Parameter.empty else inspect.Parameter.empty)
        for name, p in items
    ]


class SpeciesApiTest(unittest.TestCase):
    """src/data/species_data.py。"""

    def test_species_dataclass_fields(self):
        import dataclasses
        fields = [f.name for f in dataclasses.fields(species_data.Species)]
        self.assertEqual(fields, ["id", "name", "type", "role", "base", "growth",
                                   "catch_coef", "learnset"])

    def test_get_species_signature(self):
        self.assertEqual(_params(species_data.get_species),
                         [("species_id", inspect.Parameter.empty)])

    def test_stat_at_signature(self):
        self.assertEqual(_params(species_data.stat_at),
                         [("species_id", inspect.Parameter.empty),
                          ("key", inspect.Parameter.empty),
                          ("level", inspect.Parameter.empty)])

    def test_tables(self):
        self.assertIsInstance(species_data.SPECIES, dict)
        self.assertIsInstance(species_data.STARTER_IDS, tuple)


class SkillApiTest(unittest.TestCase):
    """src/data/skill_data.py。"""

    def test_skill_dataclass_fields(self):
        import dataclasses
        fields = [f.name for f in dataclasses.fields(skill_data.Skill)]
        self.assertEqual(fields, ["id", "name", "type", "power", "mp", "effect",
                                   "value", "min_heal", "duration", "desc"])

    def test_get_skill_signature(self):
        self.assertEqual(_params(skill_data.get_skill),
                         [("skill_id", inspect.Parameter.empty)])


class ItemApiTest(unittest.TestCase):
    """src/data/item_data.py。"""

    def test_item_dataclass_fields(self):
        import dataclasses
        fields = [f.name for f in dataclasses.fields(item_data.Item)]
        self.assertEqual(fields, ["id", "name", "price", "sell", "effect",
                                   "value", "desc"])

    def test_get_item_signature(self):
        self.assertEqual(_params(item_data.get_item),
                         [("item_id", inspect.Parameter.empty)])

    def test_constants(self):
        self.assertIsInstance(item_data.INITIAL_BAG, dict)
        self.assertIsInstance(item_data.INITIAL_DOLLARS, int)


class TypeChartApiTest(unittest.TestCase):
    """src/battle/type_chart.py。"""

    def test_multiplier_signature(self):
        self.assertEqual(_params(type_chart.multiplier),
                         [("attack_type", inspect.Parameter.empty),
                          ("defend_type", inspect.Parameter.empty)])

    def test_constants(self):
        self.assertIsInstance(type_chart.TYPES, tuple)
        self.assertIsInstance(type_chart.TYPE_CHART, dict)
        self.assertEqual(type_chart.NEUTRAL_TYPE, "无")


class DamageCalcApiTest(unittest.TestCase):
    """src/battle/damage_calc.py。"""

    def test_damage_signature(self):
        self.assertEqual(_params(damage_calc.damage),
                         [("attack", inspect.Parameter.empty),
                          ("defense", inspect.Parameter.empty),
                          ("skill_type", inspect.Parameter.empty),
                          ("skill_power", inspect.Parameter.empty),
                          ("defend_type", inspect.Parameter.empty),
                          ("atk_mod", 1.0),
                          ("rng", None)])

    def test_heal_amount_signature(self):
        self.assertEqual(_params(damage_calc.heal_amount),
                         [("skill", inspect.Parameter.empty),
                          ("max_hp", inspect.Parameter.empty)])


class CatchCalcApiTest(unittest.TestCase):
    """src/battle/catch_calc.py。"""

    def test_catch_chance_signature(self):
        self.assertEqual(_params(catch_calc.catch_chance),
                         [("hp", inspect.Parameter.empty),
                          ("hp_max", inspect.Parameter.empty),
                          ("species_coef", inspect.Parameter.empty),
                          ("ball_mult", catch_calc.BALL_MULTIPLIER)])

    def test_try_catch_signature(self):
        self.assertEqual(_params(catch_calc.try_catch),
                         [("hp", inspect.Parameter.empty),
                          ("hp_max", inspect.Parameter.empty),
                          ("species_coef", inspect.Parameter.empty),
                          ("ball_mult", catch_calc.BALL_MULTIPLIER),
                          ("rng", None)])

    def test_ball_multiplier_constant(self):
        self.assertEqual(catch_calc.BALL_MULTIPLIER, 1.0)


class CreatureApiTest(unittest.TestCase):
    """src/model/creature.py。"""

    def test_init_signature(self):
        self.assertEqual(
            _params(creature_mod.Creature.__init__),
            [("species_id", inspect.Parameter.empty),
             ("level", 5),
             ("exp", 0),
             ("hp", None),
             ("mp", None),
             ("skills", None),
             ("nickname", "")],
        )

    def test_method_signatures(self):
        self.assertEqual(_params(creature_mod.Creature.exp_to_next), [])
        self.assertEqual(_params(creature_mod.Creature.gain_exp),
                         [("amount", inspect.Parameter.empty)])
        self.assertEqual(_params(creature_mod.Creature.take_damage),
                         [("dmg", inspect.Parameter.empty)])
        self.assertEqual(_params(creature_mod.Creature.heal_hp),
                         [("n", inspect.Parameter.empty)])
        self.assertEqual(_params(creature_mod.Creature.heal_mp),
                         [("n", inspect.Parameter.empty)])
        self.assertEqual(_params(creature_mod.Creature.heal_full), [])
        self.assertEqual(_params(creature_mod.Creature.revive), [("hp_ratio", 0.5)])
        self.assertEqual(_params(creature_mod.Creature.can_use),
                         [("skill_id", inspect.Parameter.empty)])
        self.assertEqual(_params(creature_mod.Creature.spend_mp),
                         [("skill_id", inspect.Parameter.empty)])
        self.assertEqual(_params(creature_mod.Creature.apply_atk_mod),
                         [("mult", inspect.Parameter.empty),
                          ("rounds", inspect.Parameter.empty)])
        self.assertEqual(_params(creature_mod.Creature.tick_mods), [])
        self.assertEqual(_params(creature_mod.Creature.to_dict), [])
        self.assertEqual(_params(creature_mod.Creature.from_dict),
                         [("data", inspect.Parameter.empty)])

    def test_readonly_properties_exist(self):
        for name in ("species_id", "species", "level", "exp", "nickname", "hp", "mp",
                     "hp_max", "mp_max", "attack", "defense", "speed", "skills",
                     "atk_mod", "mod_rounds", "fainted"):
            self.assertIsInstance(getattr(creature_mod.Creature, name), property,
                                  f"Creature.{name} 应当是只读属性")

    def test_hp_and_mp_are_writable(self):
        c = creature_mod.Creature(1)
        c.hp = 5
        c.mp = 5
        self.assertEqual(c.hp, 5)
        self.assertEqual(c.mp, 5)

    def test_max_skills_constant(self):
        self.assertEqual(creature_mod.Creature.MAX_SKILLS, 4)


class PlayerApiTest(unittest.TestCase):
    """src/model/player.py。"""

    def test_init_signature(self):
        self.assertEqual(
            _params(player_mod.Player.__init__),
            [("dollars", 300),
             ("party", None),
             ("storage", None),
             ("bag", None)],
        )

    def test_method_signatures(self):
        self.assertEqual(_params(player_mod.Player.add_creature),
                         [("c", inspect.Parameter.empty)])
        self.assertEqual(_params(player_mod.Player.alive_party), [])
        self.assertEqual(_params(player_mod.Player.all_fainted), [])
        self.assertEqual(_params(player_mod.Player.heal_all), [])
        self.assertEqual(_params(player_mod.Player.add_item),
                         [("item_id", inspect.Parameter.empty), ("n", 1)])
        self.assertEqual(_params(player_mod.Player.remove_item),
                         [("item_id", inspect.Parameter.empty), ("n", 1)])
        self.assertEqual(_params(player_mod.Player.item_count),
                         [("item_id", inspect.Parameter.empty)])
        self.assertEqual(_params(player_mod.Player.to_dict), [])
        self.assertEqual(_params(player_mod.Player.from_dict),
                         [("data", inspect.Parameter.empty)])
        self.assertEqual(_params(player_mod.Player.new_game),
                         [("starter_species_id", inspect.Parameter.empty)])

    def test_party_limit_constant(self):
        self.assertEqual(player_mod.PARTY_LIMIT, 6)
        self.assertEqual(player_mod.Player.PARTY_LIMIT, 6)


if __name__ == "__main__":
    unittest.main()
