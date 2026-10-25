"""野生精灵技能测试（§9.4 方案 B：野生精灵不该只带 Lv1 技能）。

背景
----
《02-新增10只精灵规划.md》§9.4 记录了一个长期存在的缺陷：

    field_scene 生成野生精灵时是 `Creature(species_id, level)`，没有传 `skills`；
    而 `Creature.__init__` 在 `skills is None` 时只取 `learnset.get(1)`。

结果是洞窟里 15 级的不死鸟只有「烈焰 / 再生」两招，拿不到 Lv8 的「涅槃之炎」；
所有 8 级以上的野生精灵都只有 Lv1 两招。

本文件验证修复后的行为：

- 野外 / 洞窟生成的野生精灵，按等级带上「到该等级为止累计学会的技能」；
- 精灵最多 4 个技能，且没有重复；
- 捕捉回来的精灵（进队伍后）技能不再丢失；
- 存档往返（save_version 仍为 1）后技能不变。
"""

from __future__ import annotations

import os
import random
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.data import map_data
from src.data.species_data import MAX_SKILLS, SPECIES, learnset_up_to
from src.model import Creature
from tests import helpers

#: 野外地图 ID
FIELD_MAP = 2

#: 洞窟地图 ID
CAVE_MAP = 3


def make_field(map_id: int = FIELD_MAP, seed=None, x=None, y=None):
    """建一个跑着 FieldScene 的 Game（可注入固定随机种子）。"""
    helpers.ensure_init()

    from src.core.game import Game
    from src.core.input import FakeInput
    from src.scenes.field_scene import FieldScene

    game = Game(input=FakeInput())
    if seed is not None:
        game.wild_rng = random.Random(seed)
    scene = FieldScene(game)
    kwargs = {"map_id": map_id}
    if x is not None:
        kwargs["x"] = x
    if y is not None:
        kwargs["y"] = y
    game.scenes.replace(scene, **kwargs)
    return game, scene


def run(game, frames: int = 1) -> None:
    """跑若干帧（先 update 再 draw，和真实游戏一致）。"""
    for _ in range(frames):
        game.update()
        game.draw()


def wanderers_of(scene) -> list[dict]:
    """当前地图存活的野生精灵列表。"""
    return scene.wanderers


class WildSkillTableTest(unittest.TestCase):
    """遇敌表里的每只精灵，按等级该带什么技能。"""

    def test_every_encounter_row_has_cumulative_skills(self):
        """两张遇敌表里的每个 (种族, 等级区间) 端点都按等级取技能。"""
        for map_id in (FIELD_MAP, CAVE_MAP):
            enc = map_data.encounters_of(map_id)
            self.assertIsNotNone(enc)
            for row in enc["table"]:
                sid = int(row["species_id"])
                for level in (int(row["level_min"]), int(row["level_max"])):
                    enemy = Creature(sid, level=level)
                    self.assertEqual(enemy.skills, learnset_up_to(sid, level))
                    self.assertLessEqual(len(enemy.skills), MAX_SKILLS)
                    self.assertEqual(len(enemy.skills), len(set(enemy.skills)),
                                     f"种族 {sid} Lv{level} 技能重复")

    def test_high_level_species_get_their_lv8_skill(self):
        """Lv8 以上的野生精灵会带 Lv8 招（原来只有 Lv1 两招）。"""
        # 不死鸟 Lv15：Lv1 两招 + Lv8 的涅槃之炎 = 3 招
        enemy = Creature(7, level=15)
        self.assertEqual(len(enemy.skills), 3)
        self.assertIn(6, enemy.skills)
        # Lv16 再加凤凰天翔 = 4 招（刚好装满）
        self.assertEqual(len(Creature(7, level=16).skills), 4)

    def test_low_level_species_unchanged(self):
        """Lv1..Lv7 的野生精灵仍然只有 Lv1 两招（不能变）。"""
        for sid in SPECIES:
            for level in range(1, 8):
                self.assertEqual(len(Creature(sid, level=level).skills), 2,
                                 f"种族 {sid} Lv{level} 不该有多余技能")


class FieldSceneWildSkillTest(unittest.TestCase):
    """野外状态里生成的精灵，按等级带技能。"""

    def test_spawned_wanderers_match_expected_skills(self):
        """洞窟里刷出的每只野生精灵，技能都等于 learnset_up_to(种族, 等级)。"""
        game, scene = make_field(map_id=CAVE_MAP, seed=41, x=4, y=22)
        run(game, 3)
        wanderers = wanderers_of(scene)
        self.assertTrue(wanderers, "洞窟应该刷出野生精灵")
        for w in wanderers:
            sid = int(w["species_id"])
            level = int(w["level"])
            self.assertEqual(Creature(sid, level=level).skills,
                             learnset_up_to(sid, level),
                             f"种族 {sid} Lv{level} 技能不对")

    def test_deep_phoenix_in_cave_knows_lv8_skill(self):
        """最深处的不死鸟（Lv15-18）带 Lv8 的涅槃之炎。"""
        game, scene = make_field(map_id=CAVE_MAP, seed=7, x=4, y=22)
        run(game, 3)
        phoenix = [w for w in wanderers_of(scene) if int(w["species_id"]) == 7]
        for w in phoenix:
            level = int(w["level"])
            self.assertGreaterEqual(level, 15)
            skills = Creature(7, level=level).skills
            self.assertIn(6, skills,
                          "洞窟的不死鸟应该会 Lv8 的涅槃之炎")
            self.assertEqual(len(skills), 3 if level < 16 else 4)


class CaughtCreatureTest(unittest.TestCase):
    """捕捉回来的精灵保留自己的技能。"""

    def test_caught_creature_keeps_its_skills(self):
        """野外生成的敌人被捕捉后，技能仍是按等级累积的那一套。"""
        for sid, level in ((7, 15), (7, 16), (6, 12), (18, 16)):
            caught = Creature(sid, level=level)
            data = caught.to_dict()
            back = Creature.from_dict(data)
            self.assertEqual(back.skills, learnset_up_to(sid, level))
            self.assertEqual(len(back.skills), len(set(back.skills)))


class SaveCompatibilityTest(unittest.TestCase):
    """存档兼容性：save_version 仍是 1，读档以存档里的 skills 为准。"""

    def test_save_version_is_still_one(self):
        from src.model import save_io
        self.assertEqual(save_io.SAVE_VERSION, 1)

    def test_old_save_with_lv1_only_skills_is_not_rewritten(self):
        """老存档（只有 Lv1 两招）读回来仍是两招，不被新逻辑覆盖。"""
        old = {"species_id": 7, "level": 15, "exp": 0, "hp": 60, "mp": 40,
               "skills": [4, 25], "atk_mod": 1.0, "nickname": ""}
        back = Creature.from_dict(old)
        self.assertEqual(back.skills, [4, 25])

    def test_new_save_round_trip_keeps_all_skills(self):
        """新存档（带 3 个技能的高等级精灵）往返后技能不变。"""
        c = Creature(7, level=15)
        self.assertEqual(len(c.skills), 3)
        data = c.to_dict()
        back = Creature.from_dict(data)
        self.assertEqual(back.skills, c.skills)
        self.assertEqual(back.to_dict(), data)


if __name__ == "__main__":
    unittest.main()
