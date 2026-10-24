"""战斗场景状态机测试（T3b）。

覆盖：

- INTRO -> COMMAND -> SKILL_SELECT -> COMMAND 的状态流转；
- 5.3 技能 MP 不足 -> 置灰且确认键无效；
- 4.1 伤害飘字：命中后出现圆圈数字，30 帧后消失；
- 5.4 我方倒下 -> 强制换人（不可取消）。
"""

from __future__ import annotations

import unittest

from src.model import Creature
from src.scenes.battle_scene import BattleScene
from src.ui.damage_number import LIFETIME
from tests import battle_helpers as bh
from tests import helpers

#: 独角兽 Lv5 的 SPD 是 13，比小火狮 Lv5 的 14 慢，
#: 所以用独角兽当对手时我方先手（5.2），测试更好断言。
FASTER_ENEMY = 5


class BattleStateMachineTest(unittest.TestCase):
    def setUp(self):
        helpers.ensure_init()
        self.game, self.scene, self.enemy = bh.make_battle(
            enemy_species=FASTER_ENEMY)

    def test_starts_in_intro(self):
        self.assertEqual(self.scene.state, BattleScene.INTRO)
        self.assertIn("出现了", self.scene.intro_text)

    def test_intro_confirm_goes_to_command(self):
        bh.press(self.game, "confirm")
        self.assertEqual(self.scene.state, BattleScene.COMMAND)

    def test_command_confirm_opens_skill_list(self):
        bh.press(self.game, "confirm")   # INTRO -> COMMAND
        bh.press(self.game, "confirm")   # 战斗 -> SKILL_SELECT
        self.assertEqual(self.scene.state, BattleScene.SKILL_SELECT)
        self.assertEqual(len(self.scene.skill_menu.items),
                         len(self.scene.active.skills))

    def test_skill_select_cancel_returns_to_command(self):
        bh.press(self.game, "confirm")
        bh.press(self.game, "confirm")
        self.assertEqual(self.scene.state, BattleScene.SKILL_SELECT)
        bh.press(self.game, "cancel")
        self.assertEqual(self.scene.state, BattleScene.COMMAND)

    def test_using_skill_runs_turn_and_comes_back_to_command(self):
        bh.press(self.game, "confirm")   # INTRO -> COMMAND
        bh.press(self.game, "confirm")   # -> SKILL_SELECT
        bh.press(self.game, "down")      # 第二个技能（撞击）
        bh.press(self.game, "confirm")   # 使用
        self.assertEqual(self.scene.state, BattleScene.MESSAGE)
        ok = bh.advance_until(
            self.game, lambda: self.scene.state == BattleScene.COMMAND)
        self.assertTrue(ok, "一回合之后没有回到五指令界面")

    def test_enemy_hp_drops_after_attack(self):
        hp_before = self.enemy.hp
        bh.press(self.game, "confirm")
        bh.press(self.game, "confirm")
        bh.press(self.game, "down")
        bh.press(self.game, "confirm")
        bh.advance_until(self.game,
                         lambda: self.scene.state == BattleScene.COMMAND)
        self.assertLess(self.enemy.hp, hp_before)


class CommandLayoutTest(unittest.TestCase):
    """13.2：五指令的坐标必须和文档一模一样。"""

    def setUp(self):
        helpers.ensure_init()
        self.game, self.scene, self.enemy = bh.make_battle()

    def test_command_positions(self):
        got = {it["id"]: (it["x"], it["y"]) for it in self.scene.command_menu.items}
        self.assertEqual(got, {
            "battle": (14, 156),
            "ball": (130, 156),
            "party": (14, 176),
            "item": (130, 176),
            "run": (14, 196),
        })

    def test_command_labels(self):
        labels = [it["label"] for it in self.scene.command_menu.items]
        self.assertEqual(labels, ["战斗", "精灵球", "精灵", "道具", "逃跑"])


class MpGreyOutTest(unittest.TestCase):
    """5.3：MP 不足的技能置灰，光标能移过去但确认键无效。"""

    def setUp(self):
        helpers.ensure_init()
        self.game, self.scene, self.enemy = bh.make_battle()
        self.scene.active.mp = 0
        bh.press(self.game, "confirm")   # INTRO -> COMMAND
        bh.press(self.game, "confirm")   # -> SKILL_SELECT

    def _by_name(self):
        out = {}
        for item in self.scene.skill_menu.items:
            out[item["label"].split()[0]] = item
        return out

    def test_skill_with_cost_is_disabled(self):
        items = self._by_name()
        self.assertFalse(items["火花"]["enabled"], "MP 为 0 时火花不该可选")

    def test_zero_cost_skill_stays_enabled(self):
        items = self._by_name()
        self.assertTrue(items["撞击"]["enabled"], "撞击 MP 为 0，必须永远可选")

    def test_cursor_can_move_onto_disabled_skill(self):
        # 光标初始就停在置灰的「火花」上
        self.assertFalse(self.scene.skill_menu.is_enabled())
        self.assertFalse(self.scene.skill_menu.confirm())
        # 可以移到「撞击」（MP 0，永远可选）
        self.scene.skill_menu.move(1)
        self.assertTrue(self.scene.skill_menu.is_enabled())
        self.assertTrue(self.scene.skill_menu.confirm())

    def test_confirm_on_disabled_skill_does_nothing(self):
        hp_before = self.enemy.hp
        mp_before = self.scene.active.mp
        self.scene.skill_menu.index = 0        # 火花（MP 不足）
        bh.press(self.game, "confirm")
        self.assertEqual(self.scene.state, BattleScene.SKILL_SELECT)
        self.assertIsNone(self.scene.message)
        self.assertEqual(self.enemy.hp, hp_before)
        self.assertEqual(self.scene.active.mp, mp_before)


class DamageNumberTest(unittest.TestCase):
    """13.3：命中后出现圆圈数字，30 帧后消失。"""

    def setUp(self):
        helpers.ensure_init()
        self.game, self.scene, self.enemy = bh.make_battle(
            enemy_species=FASTER_ENEMY)

    def _attack(self):
        """走完一次玩家攻击（我方先手）。"""
        bh.press(self.game, "confirm")   # INTRO -> COMMAND
        bh.press(self.game, "confirm")   # -> SKILL_SELECT
        bh.press(self.game, "down")      # 撞击
        bh.press(self.game, "confirm")   # 使用
        bh.press(self.game, "confirm")   # 伤害结算（飘字出现）

    def test_damage_number_appears(self):
        self._attack()
        self.assertLess(self.enemy.hp, self.enemy.hp_max)
        self.assertEqual(self.scene.numbers.count, 1)
        number = self.scene.numbers.numbers[0]
        self.assertEqual(number.value, self.enemy.hp_max - self.enemy.hp)
        self.assertEqual(number.kind, "enemy")

    def test_damage_number_disappears_after_30_frames(self):
        self._attack()
        self.assertEqual(self.scene.numbers.count, 1)
        bh.idle(self.game, LIFETIME - 1)
        self.assertEqual(self.scene.numbers.count, 1, "未到 30 帧不该消失")
        bh.idle(self.game, 1)
        self.assertEqual(self.scene.numbers.count, 0, "30 帧后飘字应该消失")


class ForcedSwitchTest(unittest.TestCase):
    """5.4：我方出战精灵倒下 -> 强制换人（不可取消）。"""

    def setUp(self):
        helpers.ensure_init()
        party = [Creature(1, level=5), Creature(2, level=5)]
        self.game, self.scene, self.enemy = bh.make_battle(
            enemy_species=FASTER_ENEMY, party=party)
        self.party = self.game.player.party
        self.party[0].hp = 1
        # 先出一招，让敌方打回来把我方打倒
        bh.press(self.game, "confirm")   # INTRO -> COMMAND
        bh.press(self.game, "confirm")   # -> SKILL_SELECT
        bh.press(self.game, "down")      # 撞击
        bh.press(self.game, "confirm")   # 使用

    def test_faint_triggers_forced_switch(self):
        ok = bh.advance_until(
            self.game, lambda: self.scene.state == BattleScene.FORCED_SWITCH)
        self.assertTrue(ok, "倒下后应该进入强制换人")

    def test_forced_switch_cannot_be_cancelled(self):
        bh.advance_until(
            self.game, lambda: self.scene.state == BattleScene.FORCED_SWITCH)
        bh.press(self.game, "cancel")
        self.assertEqual(self.scene.state, BattleScene.FORCED_SWITCH)
        bh.press(self.game, "cancel")
        self.assertEqual(self.scene.state, BattleScene.FORCED_SWITCH)

    def test_fainted_creature_cannot_be_selected(self):
        bh.advance_until(
            self.game, lambda: self.scene.state == BattleScene.FORCED_SWITCH)
        names = [it["creature"] for it in self.scene.party_menu.items]
        self.assertNotIn(self.party[0], names, "倒下的精灵不能被选中")
        self.assertIn(self.party[1], names)

    def test_switching_marks_old_creature_fainted(self):
        bh.advance_until(
            self.game, lambda: self.scene.state == BattleScene.FORCED_SWITCH)
        bh.press(self.game, "confirm")
        self.assertTrue(self.party[0].fainted)
        self.assertIs(self.scene.active, self.party[1])


if __name__ == "__main__":
    unittest.main()
