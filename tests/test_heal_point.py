"""治疗点测试（批 3 / T6）。

覆盖：

1. 面对护士读完对话 -> 播放治疗演出；
2. 演出期间玩家不能移动（状态位挡住输入）；
3. 演出结束（≤ 80 帧）后全队 HP / MP 全满、没有倒下的精灵、金币不变；
4. 治疗**免费**：背包一个道具都不消耗。
"""

from __future__ import annotations

import unittest

from src.core.input import FakeInput
from src.model.creature import Creature
from src.model.player import Player
from src.scenes.field_scene import HEAL_FRAMES
from tests import field_helpers

#: 护士（精灵中心）在新手村的位置
NURSE = (10, 8)
#: 玩家站在护士正下方、面向她时的位置
NURSE_FRONT = (10, 9)


def tap(game, action: str) -> None:
    """注入**一次**按键（只跑一帧，按键按下后立刻松开）。"""
    game.input = FakeInput(script=[{action: 1}])
    game.update()


def idle(game, frames: int = 1) -> None:
    """跑若干帧（不按任何键）。"""
    game.input = FakeInput(script=[])
    for _ in range(frames):
        game.update()


def make_game():
    """建一个跑在护士面前、队伍带伤的游戏。"""
    game, scene = field_helpers.make_field(
        map_id=1, x=NURSE_FRONT[0], y=NURSE_FRONT[1], facing="up")
    player = Player.new_game(1)
    # 第 1 只：倒下（HP = 0）
    first = player.party[0]
    first.hp = 0
    first.mp = 0
    # 第 2 只：残血
    second = Creature(2, level=6, hp=3, mp=1)
    player.party.append(second)
    game.player = player
    return game, scene


def start_heal(game, scene) -> None:
    """读完护士的对话，触发治疗演出。"""
    tap(game, "confirm")       # 打开对话
    assert scene.dialogue is not None
    tap(game, "confirm")       # 翻页
    tap(game, "confirm")       # 读完 -> 触发治疗演出
    assert scene.heal_timer > 0, "读完对话后应该开始治疗演出"


class HealPointTest(unittest.TestCase):
    """治疗点。"""

    def test_heal_restores_whole_party(self):
        """残血 + 倒下 -> 治疗 -> 全队 HP / MP 全满、无倒下、金币不变。"""
        game, scene = make_game()
        player = game.player
        dollars_before = player.dollars
        self.assertTrue(player.party[0].fainted, "第 1 只应该是倒下的状态")

        start_heal(game, scene)

        # 演出期间玩家不能移动
        for _ in range(20):
            tap(game, "down")
            self.assertEqual((scene.gx, scene.gy), NURSE_FRONT)
            self.assertFalse(scene.moving)

        # 跑完演出（≤ 80 帧）
        frames = 20
        while scene.heal_timer > 0 and frames < 80:
            idle(game, 1)
            frames += 1
        self.assertLessEqual(frames, 80)
        self.assertEqual(scene.heal_timer, 0)
        self.assertGreaterEqual(HEAL_FRAMES, 40)
        self.assertLessEqual(HEAL_FRAMES, 60)

        # 演出结束后弹出结果对话
        self.assertIsNotNone(scene.dialogue)
        self.assertIn("恢复", scene.dialogue["lines"][0])

        for creature in player.party:
            self.assertEqual(creature.hp, creature.hp_max)
            self.assertEqual(creature.mp, creature.mp_max)
            self.assertFalse(creature.fainted)

        self.assertEqual(player.dollars, dollars_before)

        # 确认键关闭结果对话
        tap(game, "confirm")
        self.assertIsNone(scene.dialogue)
        # 关闭结果对话**不会**又触发一次治疗（否则会变成死循环）
        self.assertEqual(scene.heal_timer, 0)
        idle(game, 5)
        self.assertEqual(scene.heal_timer, 0)
        self.assertIsNone(scene.dialogue)

    def test_heal_does_not_consume_items(self):
        """治疗免费：背包一个道具都不消耗。"""
        game, scene = make_game()
        player = game.player
        player.bag = {1: 5, 2: 2, 4: 1}
        bag_before = dict(player.bag)

        start_heal(game, scene)
        while scene.heal_timer > 0:
            idle(game, 1)

        self.assertEqual(player.bag, bag_before)
        self.assertEqual(player.item_count(1), 5)
        self.assertEqual(player.item_count(2), 2)
        self.assertEqual(player.item_count(4), 1)

    def test_player_cannot_move_during_performance(self):
        """演出期间按住方向键也不动（状态位挡住输入）。"""
        game, scene = make_game()
        start_heal(game, scene)
        self.assertTrue(scene.busy)

        for _ in range(25):
            tap(game, "down")
        self.assertEqual((scene.gx, scene.gy), NURSE_FRONT)
        self.assertTrue(scene.heal_timer > 0)

    def test_heal_keeps_map_state(self):
        """治疗不影响野外状态（地图 1 没有野生精灵，但状态表仍然在）。"""
        game, scene = make_game()
        wild_map_state = scene.wild_state      # 本图的状态（懒创建）
        wild_states = game.wild_state          # game 上的总表
        start_heal(game, scene)
        while scene.heal_timer > 0:
            idle(game, 1)
        self.assertIs(scene.wild_state, wild_map_state)
        self.assertIs(game.wild_state, wild_states)
        self.assertEqual(len(wild_map_state["wanderers"]), 0)
        self.assertEqual((scene.gx, scene.gy), NURSE_FRONT)

    def test_heal_is_free(self):
        """治疗免费：金币一点没变。"""
        game, scene = make_game()
        player = game.player
        player.dollars = 123
        start_heal(game, scene)
        while scene.heal_timer > 0:
            idle(game, 1)
        self.assertEqual(player.dollars, 123)

    def test_heal_without_player_does_not_crash(self):
        """还没开局（player is None）时交互也不崩。"""
        game, scene = field_helpers.make_field(
            map_id=1, x=NURSE_FRONT[0], y=NURSE_FRONT[1], facing="up")
        game.player = None
        tap(game, "confirm")
        tap(game, "confirm")
        tap(game, "confirm")
        self.assertGreater(scene.heal_timer, 0)
        while scene.heal_timer > 0:
            idle(game, 1)
        self.assertIsNotNone(scene.dialogue)


if __name__ == "__main__":
    unittest.main()
