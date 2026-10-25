"""战斗演出效果测试（六项视觉演出）。

核心断言：**演出只影响「绘制」，绝不影响「状态机」和「输入判定」**。
所以第 1 条测试专门盯住"入场动画还在播的时候，状态机已经往下走了"。

六项演出
--------
1. ① 入场动画（滑入）
2. ② 受击反馈（闪烁 + 抖动 + 后移）
3. ③ 血条缓动（两段式下降）
4. ④ 屏幕震动（克制命中）
5. ⑤ 命中粒子
6. ⑥ 伤害数字描边
"""

from __future__ import annotations

import unittest

import pyxel

from src.assets_gen import palette
from src.battle.type_chart import multiplier
from src.data import skill_data as sk
from src.scenes import battle_scene
from src.scenes.battle_scene import BattleScene
from src.ui.damage_number import (
    CIRCLE_RADIUS,
    OUTLINE_COLOR,
    OUTLINE_WIDTH,
    DamageNumber,
)
from src.ui.widgets import HpBarAnimator
from tests import battle_helpers as bh
from tests import helpers

#: 敌方默认种族 3 = 兔小子（草属性）
GRASS_ENEMY = 3
#: 招式 3 = 火花（火属性）-> 打草是 2 倍克制
FIRE_SKILL = 3
#: 招式 1 = 撞击（无属性）-> 永远 1 倍
NEUTRAL_SKILL = 1


def _idle(scene, frames: int = 1) -> None:
    """让场景空跑若干帧（不按任何键）。"""
    inp = helpers.fake_input()
    for _ in range(frames):
        scene.update(inp)


def _platform_min_x(sprite_box: tuple[int, int]) -> int:
    """敌方站台深绿椭圆的最左像素 x。

    只扫天上那一块（避开地平线和地面），并跳过精灵所在的 32x32 框，
    这样精灵图里万一有同色像素也不会干扰结果。
    """
    sx, sy = sprite_box
    xs = []
    for x in range(100, 220):
        for y in range(20, 70):
            if sx <= x < sx + 32 and sy <= y < sy + 32:
                continue
            if pyxel.pget(x, y) == palette.DARK_GREEN:
                xs.append(x)
    return min(xs)


class IntroEffectTest(unittest.TestCase):
    """① 入场动画。"""

    def setUp(self):
        helpers.ensure_init()

    def test_intro_animation_does_not_block_state_machine(self):
        """入场动画在播的时候，状态机已经进到下一状态了（演出不阻塞逻辑）。"""
        game, scene, enemy = bh.make_battle()
        self.assertEqual(scene.state, BattleScene.INTRO)
        self.assertLess(scene.intro_frame, battle_scene.INTRO_FRAMES)

        bh.press(game, "confirm")           # INTRO -> COMMAND

        self.assertEqual(scene.state, BattleScene.COMMAND)
        # 动画**还在播**：说明状态机没有等动画播完
        self.assertLess(scene.intro_frame, battle_scene.INTRO_FRAMES)
        self.assertNotEqual(scene.intro_offset("enemy"), (0, 0))

    def test_intro_offset_is_zero_after_intro_frames(self):
        """入场动画帧数走完后，绘制偏移归零。"""
        game, scene, enemy = bh.make_battle()
        self.assertNotEqual(scene.intro_offset("enemy"), (0, 0))
        self.assertNotEqual(scene.intro_offset("player"), (0, 0))

        _idle(scene, battle_scene.INTRO_FRAMES)

        self.assertEqual(scene.intro_offset("enemy"), (0, 0))
        self.assertEqual(scene.intro_offset("player"), (0, 0))
        self.assertEqual(scene.creature_offset("enemy"), (0, 0))
        self.assertEqual(scene.creature_offset("player"), (0, 0))

    def test_intro_slides_in_from_opposite_corners(self):
        """敌方从右上滑入，我方从左下滑入。"""
        game, scene, enemy = bh.make_battle()
        ex, ey = scene.intro_offset("enemy")
        px, py = scene.intro_offset("player")
        self.assertGreater(ex, 0)
        self.assertLess(ey, 0)
        self.assertLess(px, 0)
        self.assertGreater(py, 0)

    def test_intro_offset_shrinks_monotonically(self):
        """缓出：越接近终点，剩余偏移越小。"""
        game, scene, enemy = bh.make_battle()
        first = abs(scene.intro_offset("enemy")[0])
        _idle(scene, battle_scene.INTRO_FRAMES // 2)
        middle = abs(scene.intro_offset("enemy")[0])
        self.assertLess(middle, first)
        self.assertGreaterEqual(middle, 0)


class PlatformFollowTest(unittest.TestCase):
    """站台（精灵脚下的椭圆影子）必须跟着精灵一起滑入。

    回归测试：之前站台只吃 `shake_offset()`、精灵吃 `creature_offset()`，
    入场那 16 帧里精灵在滑、影子钉在原地 —— 精灵看起来悬在影子上面。
    """

    def setUp(self):
        helpers.ensure_init()

    def test_platform_offset_matches_creature_intro_offset(self):
        """入场中间帧：某一侧的站台偏移 == 该侧精灵的入场偏移。"""
        game, scene, enemy = bh.make_battle()
        _idle(scene, 5)
        for side in ("enemy", "player"):
            self.assertEqual(scene.platform_offset(side),
                             scene.intro_offset(side))
            self.assertNotEqual(scene.intro_offset(side), (0, 0))

    def test_platform_offset_adds_shake_without_double_counting(self):
        """震屏时站台 = 入场偏移 + 震屏偏移（偏移没有叠加两次）。"""
        game, scene, enemy = bh.make_battle()
        _idle(scene, 5)
        scene.trigger_shake()
        sx, sy = scene.shake_offset()
        for side in ("enemy", "player"):
            ix, iy = scene.intro_offset(side)
            self.assertEqual(scene.platform_offset(side), (ix + sx, iy + sy))

    def test_platform_offset_is_zero_after_intro(self):
        """入场结束后：精灵和站台的偏移都为 0。"""
        game, scene, enemy = bh.make_battle()
        _idle(scene, battle_scene.INTRO_FRAMES)
        self.assertEqual(scene.platform_offset("enemy"), (0, 0))
        self.assertEqual(scene.platform_offset("player"), (0, 0))
        self.assertEqual(scene.intro_offset("enemy"), (0, 0))
        self.assertEqual(scene.creature_offset("enemy"), (0, 0))

    def test_platform_pixels_move_with_the_creature(self):
        """像素级：站台真的跟着精灵挪走了（深绿椭圆的最左像素平移同样的量）。"""
        game, scene, enemy = bh.make_battle()
        _idle(scene, 5)
        ox, oy = scene.intro_offset("enemy")
        self.assertNotEqual((ox, oy), (0, 0))
        game.draw()
        intro_min = _platform_min_x((150 + ox, 20 + oy))
        _idle(scene, battle_scene.INTRO_FRAMES)
        game.draw()
        settled_min = _platform_min_x((150, 20))
        self.assertEqual(intro_min, settled_min + ox)


class HitEffectTest(unittest.TestCase):
    """② 受击反馈。"""

    def setUp(self):
        helpers.ensure_init()

    def test_hit_offset_returns_to_zero_after_hit_frames(self):
        """受击抖动在 N 帧后自动归零，不会永久偏移。"""
        game, scene, enemy = bh.make_battle()
        # 先把入场动画跑完，免得它的偏移混进断言里
        _idle(scene, battle_scene.INTRO_FRAMES)
        scene.trigger_hit_effect(enemy, sk.get_skill(NEUTRAL_SKILL))
        self.assertNotEqual(scene.hit_offset("enemy"), (0, 0))

        _idle(scene, battle_scene.HIT_FRAMES)

        self.assertEqual(scene.hit_offset("enemy"), (0, 0))
        self.assertEqual(scene.hit_offset("player"), (0, 0))
        self.assertEqual(scene.creature_offset("enemy"), (0, 0))

    def test_hit_effect_is_bounded(self):
        """位移幅度有上限（240x216 下不能糊住画面）。"""
        game, scene, enemy = bh.make_battle()
        scene.trigger_hit_effect(enemy, sk.get_skill(NEUTRAL_SKILL))
        peak = 0
        for _ in range(battle_scene.HIT_FRAMES):
            _idle(scene, 1)
            peak = max(peak, abs(scene.hit_offset("enemy")[0]))
        self.assertGreater(peak, 0)
        self.assertLessEqual(peak, 4)

    def test_hit_effect_does_not_touch_hp(self):
        """受击演出不碰真实 HP（数值结算在别处）。"""
        game, scene, enemy = bh.make_battle()
        hp = enemy.hp
        scene.trigger_hit_effect(enemy, sk.get_skill(NEUTRAL_SKILL))
        _idle(scene, 30)
        self.assertEqual(enemy.hp, hp)

    def test_player_and_enemy_shake_in_opposite_directions(self):
        """我方向左退、敌方向右退。"""
        game, scene, enemy = bh.make_battle()
        scene.trigger_hit_effect(enemy, sk.get_skill(NEUTRAL_SKILL))
        scene.trigger_hit_effect(scene.active, sk.get_skill(NEUTRAL_SKILL))
        self.assertGreater(scene.hit_offset("enemy")[0], 0)
        self.assertLess(scene.hit_offset("player")[0], 0)


class HpBarEaseTest(unittest.TestCase):
    """③ 血条缓动。"""

    def setUp(self):
        helpers.ensure_init()

    def test_display_hp_converges_to_real_hp(self):
        """display_hp 从旧值收敛到新值，收敛后 == creature.hp。"""
        game, scene, enemy = bh.make_battle()
        _idle(scene, 1)
        start = scene.hp_display("enemy")
        real = enemy.hp
        self.assertEqual(start, real)

        enemy.hp = real - 10
        _idle(scene, 1)

        # 缓动刚开始：显示值还是旧值，真实 HP 已经是新值
        self.assertEqual(scene.hp_display("enemy"), start)
        self.assertEqual(enemy.hp, real - 10)

        _idle(scene, 200)

        # 收敛：显示值 == 真实 HP
        self.assertEqual(scene.hp_display("enemy"), enemy.hp)

    def test_real_hp_is_not_modified_while_easing(self):
        """缓动期间真实 HP 不会被改。"""
        game, scene, enemy = bh.make_battle()
        _idle(scene, 1)
        real = enemy.hp
        enemy.hp = real - 12
        for _ in range(60):
            _idle(scene, 1)
            self.assertEqual(enemy.hp, real - 12)   # 真实值一动不动
            self.assertLessEqual(scene.hp_display("enemy"), real)

    def test_animator_never_writes_back_to_real_value(self):
        """HpBarAnimator 自身也只读真实值。"""
        anim = HpBarAnimator()
        anim.sync("a", 30)
        anim.sync("a", 20)
        for _ in range(200):
            anim.sync("a", 20)
        self.assertEqual(anim.display("a", 20), 20)
        self.assertEqual(anim.phase("a"), "idle")

    def test_two_stage_easing_pauses_in_the_middle(self):
        """两段式：先掉到差值的 30%，停顿一下，再掉到真实值。"""
        anim = HpBarAnimator()
        anim.sync("a", 30)
        anim.sync("a", 20)              # 侦测到变化
        for _ in range(10):
            anim.sync("a", 20)
            if anim.phase("a") == "hold":
                break
        self.assertEqual(anim.phase("a"), "hold")
        self.assertEqual(anim.display("a", 20), 27)   # 30 - 10 * 0.3
        before = anim.display("a", 20)
        anim.sync("a", 20)
        self.assertEqual(anim.display("a", 20), before)   # 停顿中，值不变

    def test_switching_creature_resets_display(self):
        """换人时显示值直接跳到新精灵的真实 HP（不做缓动）。"""
        from src.model import Creature

        party = [Creature(1, level=5), Creature(2, level=5)]
        game, scene, enemy = bh.make_battle(party=party)
        _idle(scene, 1)
        other = party[1]
        scene.active = other
        _idle(scene, 1)
        self.assertEqual(scene.hp_display("player"), other.hp)


class ScreenShakeTest(unittest.TestCase):
    """④ 屏幕震动。"""

    def setUp(self):
        helpers.ensure_init()

    def test_shake_offset_returns_to_zero_after_shake_frames(self):
        """震屏偏移在 N 帧后归零。"""
        game, scene, enemy = bh.make_battle()
        scene.trigger_shake()
        self.assertNotEqual(scene.shake_offset(), (0, 0))

        _idle(scene, battle_scene.SHAKE_FRAMES)

        self.assertEqual(scene.shake_offset(), (0, 0))

    def test_super_effective_hit_triggers_shake(self):
        """克制（2 倍）命中 -> 震屏。"""
        game, scene, enemy = bh.make_battle(enemy_species=GRASS_ENEMY)
        fire = sk.get_skill(FIRE_SKILL)
        self.assertEqual(multiplier(fire.type, enemy.species.type), 2.0)
        scene.trigger_hit_effect(enemy, fire)
        self.assertNotEqual(scene.shake_offset(), (0, 0))

    def test_normal_hit_does_not_shake(self):
        """普通命中不震屏。"""
        game, scene, enemy = bh.make_battle(enemy_species=GRASS_ENEMY)
        scene.trigger_hit_effect(enemy, sk.get_skill(NEUTRAL_SKILL))
        self.assertEqual(scene.shake_offset(), (0, 0))

    def test_shake_amplitude_is_small(self):
        """震屏幅度 <= 2px（240x216 下不能晃瞎眼）。"""
        game, scene, enemy = bh.make_battle()
        scene.trigger_shake()
        peak = 0
        for _ in range(battle_scene.SHAKE_FRAMES):
            _idle(scene, 1)
            sx, sy = scene.shake_offset()
            peak = max(peak, abs(sx), abs(sy))
        self.assertGreater(peak, 0)
        self.assertLessEqual(peak, battle_scene.SHAKE_MAX)


class ParticleTest(unittest.TestCase):
    """⑤ 命中粒子。"""

    def setUp(self):
        helpers.ensure_init()

    def test_particles_are_spawned_on_hit(self):
        game, scene, enemy = bh.make_battle()
        scene.trigger_hit_effect(enemy, sk.get_skill(FIRE_SKILL))
        self.assertEqual(len(scene.particles), battle_scene.PARTICLE_COUNT)

    def test_particles_are_cleared_after_animation(self):
        """粒子列表在动画结束后被清空（不会无限累积）。"""
        game, scene, enemy = bh.make_battle()
        scene.trigger_hit_effect(enemy, sk.get_skill(FIRE_SKILL))
        self.assertGreater(len(scene.particles), 0)

        _idle(scene, battle_scene.PARTICLE_FRAMES + 2)

        self.assertEqual(len(scene.particles), 0)

    def test_particles_do_not_accumulate_over_a_long_battle(self):
        """长时间战斗里粒子数量不会越堆越多。"""
        game, scene, enemy = bh.make_battle()
        peak = 0
        for i in range(400):
            if i % 15 == 0:
                scene.trigger_hit_effect(enemy, sk.get_skill(FIRE_SKILL))
            _idle(scene, 1)
            peak = max(peak, len(scene.particles))
        self.assertLessEqual(peak, battle_scene.PARTICLE_COUNT * 2)
        # 最后一批粒子放完 -> 列表清空
        _idle(scene, battle_scene.PARTICLE_FRAMES + 2)
        self.assertEqual(len(scene.particles), 0)

    def test_entering_battle_clears_particles(self):
        """重新进战斗时粒子被清空。"""
        game, scene, enemy = bh.make_battle()
        scene.trigger_hit_effect(enemy, sk.get_skill(FIRE_SKILL))
        scene.enter()
        self.assertEqual(len(scene.particles), 0)


class DamageNumberOutlineTest(unittest.TestCase):
    """⑥ 伤害数字描边。"""

    def setUp(self):
        helpers.ensure_init()
        pyxel.cls(0)

    def test_outline_color_is_dark_purple(self):
        """描边用色 5（深紫）—— 调色板里就是「描边专用色」。"""
        self.assertEqual(OUTLINE_COLOR, palette.DARK_PURPLE)
        self.assertEqual(OUTLINE_COLOR, 5)
        self.assertEqual(OUTLINE_WIDTH, 1)

    def test_badge_has_one_pixel_dark_outline(self):
        """圆圈数字外面套一圈 1px 深色描边。"""
        number = DamageNumber(100, 100, 8, "enemy")
        number.draw()
        # 外框：半径 +1 那一圈是描边色
        self.assertEqual(pyxel.pget(100 + CIRCLE_RADIUS + 1, 100), OUTLINE_COLOR)
        self.assertEqual(pyxel.pget(100 - CIRCLE_RADIUS - 1, 100), OUTLINE_COLOR)
        self.assertEqual(pyxel.pget(100, 100 + CIRCLE_RADIUS + 1), OUTLINE_COLOR)
        # 里面还是原来的圆圈（边色 7 白 / 底色 15 浅灰）
        self.assertEqual(pyxel.pget(100 + CIRCLE_RADIUS, 100), palette.WHITE)
        self.assertEqual(pyxel.pget(100 + CIRCLE_RADIUS - 1, 100),
                         palette.LIGHT_GRAY)

    def test_outline_does_not_smear_the_digit(self):
        """描边没有盖到数字本身（字还是黑的，洞还在）。"""
        number = DamageNumber(100, 100, 8, "enemy")
        number.draw()
        colors = set()
        for dx in range(-6, 7):
            for dy in range(-6, 7):
                colors.add(pyxel.pget(100 + dx, 100 + dy))
        self.assertIn(palette.BLACK, colors)        # 数字本体（敌方字色 0）
        self.assertNotIn(OUTLINE_COLOR, colors)     # 描边只在圆圈外面那圈

    def test_outline_is_visible_for_player_numbers_too(self):
        """我方飘字（白字红底）同样有描边。"""
        number = DamageNumber(100, 100, 12, "player")
        number.draw()
        self.assertEqual(pyxel.pget(100 + CIRCLE_RADIUS + 1, 100), OUTLINE_COLOR)
        colors = set()
        for dx in range(-6, 7):
            for dy in range(-6, 7):
                colors.add(pyxel.pget(100 + dx, 100 + dy))
        self.assertIn(palette.WHITE, colors)        # 数字本体（我方字色 7）


class DrawSafetyTest(unittest.TestCase):
    """演出全开时也不能把画面画崩。"""

    def setUp(self):
        helpers.ensure_init()

    def test_draw_with_all_effects_active(self):
        game, scene, enemy = bh.make_battle()
        scene.trigger_hit_effect(enemy, sk.get_skill(FIRE_SKILL))
        scene.trigger_hit_effect(scene.active, sk.get_skill(FIRE_SKILL))
        scene.trigger_shake()
        for _ in range(10):
            game.update()
            game.draw()

    def test_intro_frames_draw_without_crash(self):
        game, scene, enemy = bh.make_battle()
        for _ in range(battle_scene.INTRO_FRAMES + 2):
            game.update()
            game.draw()


if __name__ == "__main__":
    unittest.main()
