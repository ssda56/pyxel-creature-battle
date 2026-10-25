"""回合制战斗场景（《数值设定.md》§5 战斗流程 / §13.1 画面布局 / §13.2 五指令 / §13.3 飘字）。

状态机
--------
::

    INTRO ──确认──> COMMAND ──┬─「战斗」──> SKILL_SELECT ──确认──> 结算演出
                              ├─「精灵」──> PARTY_SELECT
                              ├─「精灵球」> CATCH
                              ├─「道具」──> ITEM_SELECT
                              └─「逃跑」──> 逃跑判定

    任意时刻的演出文字走 MESSAGE；我方倒下且队伍仍有存活 -> FORCED_SWITCH；
    战斗结束 -> RESULT（调用 on_end 后弹出场景）。

所有数值都来自《数值设定.md》：

- §4.1 伤害：**只**调用 :func:`src.battle.damage_calc.damage`（本文件不另写公式）；
- §5.3 技能 MP 不足 -> 置灰（色 5）不可选；
- §5.4 我方倒下 -> 强制换人（不可取消）；
- §5.5 逃跑 `p = clamp(0.55 + (我方SPD - 敌方SPD) * 0.02, 0.20, 0.95)`；
- §5.6 战败 -> 淡出 -> 全队回复 -> 回新手村出生点，**不扣金币**；
- §5.7 胜利：经验 `20 + 15 × 敌方等级`、金币 `6 + 4 × 敌方等级`、MP 回复 10%（向上取整）；
- §8 捕捉成功：不给金币，战精灵得 `3 × 敌方等级` 经验。
"""

from __future__ import annotations

import math
import random

import pyxel

from src.assets_gen import palette, sprite_base
from src.battle import catch_calc, damage_calc
from src.battle.type_chart import multiplier
from src.data import item_data as it
from src.data import map_data
from src.data import skill_data as sk
from src.data import species_data as sd
from src.model import Creature, Player
from src.scenes.field_scene import FieldScene
from src.scenes.scene_base import Scene
from src.ui import sound, text
from src.ui.damage_number import DamageNumberGroup
from src.ui.transition import Fade
from src.ui.widgets import HpBarAnimator, MenuList, draw_status_box

# ==================================================================== 数值
#: §5.7 胜利经验 = WIN_EXP_BASE + WIN_EXP_PER_LEVEL × 敌方等级
WIN_EXP_BASE = 20
WIN_EXP_PER_LEVEL = 15

#: §5.7 胜利金币 = WIN_DOLLAR_BASE + WIN_DOLLAR_PER_LEVEL × 敌方等级
WIN_DOLLAR_BASE = 6
WIN_DOLLAR_PER_LEVEL = 4

#: §5.7 胜利后出战精灵回复的最大 MP 比例（向上取整）
MP_RECOVER_RATIO = 0.10

#: §5.7 / §8 捕捉成功给战精灵的经验 = CATCH_EXP_PER_LEVEL × 敌方等级
CATCH_EXP_PER_LEVEL = 3

#: §5.5 逃跑成功率：clamp(RUN_BASE + 速度差 × RUN_SPD_COEF, RUN_MIN, RUN_MAX)
RUN_BASE = 0.55
RUN_SPD_COEF = 0.02
RUN_MIN = 0.20
RUN_MAX = 0.95

#: §5.6 战败淡出帧数（60 帧 @60fps = 1 秒，与 30 帧 @30fps 一致）
DEFEAT_FADE_FRAMES = 60

#: 精灵球道具 ID（§7.1）
BALL_ITEM_ID = 1

# ==================================================================== 布局
#: 画面尺寸
SCREEN_W = 240
SCREEN_H = 216

#: 底部面板（§13.1：(0, 150) 240×66）
PANEL_X, PANEL_Y, PANEL_W, PANEL_H = 0, 150, 240, 66

#: 敌方信息框 (4, 4)、我方信息框 (120, 108)（§13.1）
ENEMY_BOX_X, ENEMY_BOX_Y = 4, 4
PLAYER_BOX_X, PLAYER_BOX_Y = 120, 108

#: 敌方精灵 (150, 20)、我方精灵 (24, 86)，都是 32×32（§13.1）
ENEMY_SPRITE_X, ENEMY_SPRITE_Y = 150, 20
PLAYER_SPRITE_X, PLAYER_SPRITE_Y = 24, 86

#: §13.2 五指令坐标（绝对屏幕坐标）
COMMAND_POS: dict[str, tuple[int, int]] = {
    "battle": (14, 156),
    "ball": (130, 156),
    "party": (14, 176),
    "item": (130, 176),
    "run": (14, 196),
}

#: 精灵球数量提示的位置（不占用 §13.2 的指令坐标）
BALL_COUNT_X = 174

#: 技能列表
SKILL_X, SKILL_Y, SKILL_LINE_H = 14, 156, 14

#: 道具列表
ITEM_X, ITEM_Y, ITEM_LINE_H = 14, 156, 14

#: 队伍列表（最多 4 行 + 1 行提示）
PARTY_X, PARTY_Y, PARTY_LINE_H = 14, 152, 12
PARTY_ROWS = 4
PARTY_HINT_Y = 202

#: 地平线
HORIZON_Y = 88

# ==================================================================== 演出效果（纯绘制层）
#
# 铁律：**演出只影响「绘制」，绝不影响「状态机」和「输入判定」**。
#
# 做法：进入场景时记一个帧计数器，每帧 +1；draw() 里用计数器算绘制偏移 /
# 透明度 / 缩放。update() 里的状态流转逻辑**一行都没有改**，
# 所以 INTRO -> COMMAND -> SKILL_SELECT 的既有测试全部照旧通过，
# 玩家也不会因为等动画播完而觉得卡。

#: ① 入场动画总帧数（60fps，16 帧 ≈ 0.27 秒）
INTRO_FRAMES = 16
#: ① 入场起始偏移：敌方从右上滑入、我方从左下滑入
INTRO_FROM = {"enemy": (36, -26), "player": (-32, 26)}

#: ② 受击反馈的逐帧水平位移（像素；敌方被推向右，我方取反）
#: 0~2 帧 = 后移 2px 推出，3~7 帧 = 抖动回归，8 帧之后 = 完全归位
HIT_OFFSETS = (2, 3, 2, 1, -1, 2, -2, 1, 0, 0, 0, 0)
#: ② 受击反馈总帧数（= 位移表长度）
HIT_FRAMES = len(HIT_OFFSETS)
#: ② 受击闪烁：前几帧里隔帧不画精灵
HIT_FLASH_FRAMES = 4

#: ④ 震屏总帧数（60fps）
SHAKE_FRAMES = 8
#: ④ 震屏最大位移（像素）
SHAKE_MAX = 2
#: ④ 震屏逐帧位移（水平 / 垂直）
SHAKE_PATTERN_X = (2, -2, 1, -1, 1, -1, 0, 0)
SHAKE_PATTERN_Y = (0, 1, 0, -1, 0, 1, 0, -1)

#: ⑤ 命中粒子：个数 / 寿命（帧）/ 渐隐帧数
PARTICLE_COUNT = 5
PARTICLE_FRAMES = 12
PARTICLE_FADE = 4
#: ⑤ 粒子飞散方向（**固定表，不用随机数**）
#: 战斗的随机源是注入的 seeded RNG，粒子去抽它会改变伤害骰子的结果，
#: 所以这里用写死的方向表，保证战斗可复现。
#: 速度给得比"看着自然"稍快一点：飘字圆圈半径 9（加描边 10），
#: 粒子起步就在圆圈里，速度太慢前几帧会被圆圈挡住看不见。
PARTICLE_DIRS = ((-3, -1), (0, -3), (3, -1), (3, 2), (-3, 2))


# ==================================================================== 规则函数
def victory_exp(enemy_level: int) -> int:
    """胜利经验（《数值设定.md》§5.7）：`20 + 15 × 敌方等级`。"""
    return WIN_EXP_BASE + WIN_EXP_PER_LEVEL * int(enemy_level)


def victory_dollars(enemy_level: int) -> int:
    """胜利金币（《数值设定.md》§5.7）：`6 + 4 × 敌方等级`。"""
    return WIN_DOLLAR_BASE + WIN_DOLLAR_PER_LEVEL * int(enemy_level)


def mp_recover_amount(mp_max: int) -> int:
    """胜利后回复的 MP（《数值设定.md》§5.7）：最大 MP 的 10%（向上取整）。"""
    return int(math.ceil(int(mp_max) * MP_RECOVER_RATIO))


def catch_exp(enemy_level: int) -> int:
    """捕捉成功给战精灵的经验（《数值设定.md》§5.7）：`3 × 敌方等级`。"""
    return CATCH_EXP_PER_LEVEL * int(enemy_level)


def escape_chance(my_spd: int, enemy_spd: int) -> float:
    """逃跑成功率（《数值设定.md》§5.5）。

    `p = clamp(0.55 + (我方SPD - 敌方SPD) × 0.02, 0.20, 0.95)`
    """
    raw = RUN_BASE + (int(my_spd) - int(enemy_spd)) * RUN_SPD_COEF
    if raw < RUN_MIN:
        return RUN_MIN
    if raw > RUN_MAX:
        return RUN_MAX
    return raw


class HitParticle:
    """命中时飞散的小点（纯装饰，寿命结束即被回收）。

    参数
    ----
    x, y
        出生点（被击中的精灵身上）。
    vx, vy
        每帧位移。
    color
        粒子颜色（招式属性主色）。
    bg_color
        渐隐时混进去的背景色（精灵身后的底色）。
    """

    __slots__ = ("x", "y", "vx", "vy", "age", "color", "bg_color")

    def __init__(self, x: int, y: int, vx: int, vy: int,
                 color: int, bg_color: int):
        self.x = int(x)
        self.y = int(y)
        self.vx = int(vx)
        self.vy = int(vy)
        self.age = 0
        self.color = int(color)
        self.bg_color = int(bg_color)

    def update(self) -> bool:
        """推进一帧。

        返回
        ----
        bool
            True 表示还活着；False 表示寿命结束、该被回收了。
        """
        self.age += 1
        self.x += self.vx
        self.y += self.vy
        if self.age > PARTICLE_FRAMES // 2:
            self.vy += 1          # 后半程轻微下坠
        return self.age < PARTICLE_FRAMES

    def draw(self, offset: tuple[int, int] = (0, 0)) -> None:
        """画这个小点（最后几帧渐隐到背景色）。"""
        ox = int(offset[0]) if offset else 0
        oy = int(offset[1]) if offset else 0
        color = self.color
        if self.age >= PARTICLE_FRAMES - PARTICLE_FADE:
            color = self.bg_color
        pyxel.circ(self.x + ox, self.y + oy, 1, color)


class BattleScene(Scene):
    """回合制战斗场景。

    参数
    ----
    game
        :class:`src.core.game.Game` 实例（读 game.player 与 game.player_state）。
    enemy
        敌方精灵（:class:`src.model.Creature`）。
    on_end
        战斗结束、场景弹出**之前**调用一次：on_end(result)，
        result 取值 "win" / "lose" / "catch" / "run"。
    rng
        随机源（random.Random）；不给就用模块级 random。
        测试注入固定种子即可让整场战斗可复现。
    """

    # ---------------------------------------------------------- 状态枚举
    INTRO = "INTRO"
    COMMAND = "COMMAND"
    SKILL_SELECT = "SKILL_SELECT"
    PARTY_SELECT = "PARTY_SELECT"
    ITEM_SELECT = "ITEM_SELECT"
    CATCH = "CATCH"
    MESSAGE = "MESSAGE"
    RESULT = "RESULT"
    FORCED_SWITCH = "FORCED_SWITCH"

    # ---------------------------------------------------------- 战斗结果
    RESULT_WIN = "win"
    RESULT_LOSE = "lose"
    RESULT_CATCH = "catch"
    RESULT_RUN = "run"

    # ---------------------------------------------------------- 生命周期
    def __init__(self, game, enemy: Creature, on_end=None, rng=None):
        super().__init__(game)
        self.enemy: Creature = enemy
        self.on_end = on_end
        self.rng = rng
        self._rng = rng if rng is not None else random

        #: 玩家状态（队伍 / 金币 / 背包）
        player = getattr(game, "player", None)
        if player is None:
            player = Player.new_game(sd.STARTER_IDS[0])
            game.player = player
        self.player: Player = player

        #: 我方出战精灵
        self.active: Creature | None = (
            self.player.party[0] if self.player.party else None
        )

        #: 当前状态（见状态枚举）
        self.state: str = self.INTRO
        #: 当前演出文字（None 表示没有文字）
        self.message: str | None = None
        #: 文字确认后要执行的动作
        self._after = None
        #: 战斗结果（结束后写入）
        self.result: str | None = None
        #: 开场白（进入时写入）
        self.intro_text = ""
        #: 战败台词（战败淡出后写入）
        self._defeat_text = ""

        #: 伤害飘字
        self.numbers = DamageNumberGroup()
        #: 转场（战败淡出用）
        self.fade = Fade()

        # ---------------------------------------------------------- 演出效果
        #: ① 入场动画帧计数器（纯绘制层）
        self.intro_frame = 0
        #: ② 受击反馈帧计数（enemy / player）；-1 = 当前没有受击演出
        self._hit_age = {"enemy": -1, "player": -1}
        #: ④ 震屏帧计数；-1 = 当前不震
        self._shake_age = -1
        #: ⑤ 命中粒子（寿命结束会被回收，列表不会无限累积）
        self._particles: list[HitParticle] = []
        #: ③ 血条缓动（只维护显示值，**绝不写回** Creature.hp）
        self._hp_anim = HpBarAnimator()
        #: 血条缓动对应的「我方出战精灵」（换人时重置显示值）
        self._hp_owner = None

        #: 本回合双方是否已经行动过（决定行动顺序与回合结束）
        self._enemy_acted = False
        self._player_acted = False

        #: 队伍菜单的模式："switch" / "forced" / "revive"
        self._party_mode = "switch"

        #: 四个菜单
        self.command_menu = MenuList(0, 0, [])
        self.skill_menu = MenuList(0, 0, [])
        self.party_menu = MenuList(0, 0, [])
        self.item_menu = MenuList(0, 0, [])

    def enter(self, **kwargs) -> None:
        """进入战斗场景：重置状态并显示开场白。"""
        sprite_base.bake_all()
        self.numbers.clear()
        self.fade.stop()
        self.message = None
        self._after = None
        self.result = None
        self._enemy_acted = False
        self._player_acted = False
        self.state = self.INTRO
        self.intro_text = f"野生的{self.enemy.display_name}出现了！"
        self._build_command_menu()
        # 重置演出计时器（① 入场动画从头播）
        self._reset_effects()
        # 战斗 BGM（T8b）：顶掉地面的 field / cave 音乐
        sound.play_bgm("battle")

    def resume(self) -> None:
        """回到前台：战斗状态不变。"""

    def exit(self) -> None:
        """退出：不做额外处理（状态已经写回 player）。"""

    # ================================================================ 每帧
    def update(self, inp) -> None:
        """每帧逻辑更新。"""
        # 演出计时器先推进（**只影响绘制**，不参与状态流转与输入判定）
        self._update_effects()
        self.numbers.update()
        if self.fade.is_active:
            self.fade.update()

        # 有演出文字时：按确认键继续
        if self.message is not None:
            if inp.pressed("confirm"):
                self._dismiss_message()
            return

        state = self.state
        if state == self.INTRO:
            if inp.pressed("confirm"):
                self._start_command()
        elif state == self.COMMAND:
            self._update_command(inp)
        elif state == self.SKILL_SELECT:
            self._update_skill(inp)
        elif state == self.PARTY_SELECT:
            self._update_party(inp)
        elif state == self.FORCED_SWITCH:
            self._update_party(inp)
        elif state == self.ITEM_SELECT:
            self._update_item(inp)
        elif state == self.CATCH:
            if inp.pressed("confirm"):
                self._dismiss_message()

    def draw(self) -> None:
        """画整个战斗画面。"""
        self._draw_background()
        self._draw_creature(self.enemy, ENEMY_SPRITE_X, ENEMY_SPRITE_Y, "enemy")
        self._draw_creature(self.active, PLAYER_SPRITE_X, PLAYER_SPRITE_Y,
                            "player")
        self._draw_status_boxes()
        self._draw_panel()
        self._draw_particles()
        self.numbers.draw(self.shake_offset())
        self.fade.draw()
        self._draw_defeat_text()

    # ================================================================ 演出效果
    # 这一整节都只影响「绘制」：状态机（INTRO -> COMMAND -> ...）和
    # 输入判定一行都没动，演出只是叠在画面上的一层。

    def _reset_effects(self) -> None:
        """重置所有演出计时器（进战斗 / 重新进战斗时调用）。"""
        self.intro_frame = 0
        self._hit_age = {"enemy": -1, "player": -1}
        self._shake_age = -1
        self._particles = []
        self._hp_anim.reset()
        self._hp_owner = None

    def _update_effects(self) -> None:
        """推进所有演出计时器（纯绘制层，不影响状态机 / 输入判定）。"""
        # ① 入场动画
        if self.intro_frame < INTRO_FRAMES:
            self.intro_frame += 1
        # ② 受击反馈
        for side in ("enemy", "player"):
            age = self._hit_age.get(side, -1)
            if age >= 0:
                age += 1
                self._hit_age[side] = -1 if age >= HIT_FRAMES else age
        # ④ 震屏
        if self._shake_age >= 0:
            age = self._shake_age + 1
            self._shake_age = -1 if age >= SHAKE_FRAMES else age
        # ⑤ 粒子（寿命结束就回收，列表不会无限增长）
        if self._particles:
            alive: list[HitParticle] = []
            for particle in self._particles:
                if particle.update():
                    alive.append(particle)
            self._particles = alive
        # ③ 血条缓动（只读真实 HP）
        self._sync_hp_bars()

    def _sync_hp_bars(self) -> None:
        """把两侧真实 HP 喂给血条缓动器（**只读**，不写回 Creature.hp）。"""
        if self.active is not self._hp_owner:
            # 换人：显示值直接跳到新精灵的真实 HP，不做缓动
            self._hp_anim.reset("player")
            self._hp_owner = self.active
        self._hp_anim.sync("enemy", self.enemy.hp)
        if self.active is not None:
            self._hp_anim.sync("player", self.active.hp)

    # ------------------------------------------------------------ 查询
    def intro_offset(self, side: str) -> tuple[int, int]:
        """① 入场动画的绘制偏移（帧数走完后恒为 (0, 0)）。"""
        if self.intro_frame >= INTRO_FRAMES:
            return (0, 0)
        t = self.intro_frame / float(INTRO_FRAMES)
        ease = 1.0 - (1.0 - t) ** 2        # 缓出：先快后慢
        fx, fy = INTRO_FROM.get(side, (0, 0))
        return (int(round(fx * (1.0 - ease))), int(round(fy * (1.0 - ease))))

    def hit_offset(self, side: str) -> tuple[int, int]:
        """② 受击反馈的绘制偏移（结束后恒为 (0, 0)）。"""
        age = self._hit_age.get(side, -1)
        if age < 0 or age >= HIT_FRAMES:
            return (0, 0)
        value = HIT_OFFSETS[age]
        if side == "player":
            value = -value               # 我方被推向左
        return (value, 0)

    def creature_offset(self, side: str) -> tuple[int, int]:
        """一只精灵当前的绘制偏移（入场 + 受击）。"""
        ix, iy = self.intro_offset(side)
        hx, hy = self.hit_offset(side)
        return (ix + hx, iy + hy)

    def platform_offset(self, side: str) -> tuple[int, int]:
        """站台（精灵脚下的椭圆影子）的绘制偏移。

        站台跟着**该侧精灵的入场偏移**一起滑入：否则入场那 16 帧里
        精灵在滑、影子钉在原地，看起来像精灵悬在影子上面。
        震屏时站台跟着一起晃。

        注意：这里只叠加入场偏移，**不含受击位移** —— 受击时精灵单独
        后移弹回、影子留在原地，正是"被打得往后一顿"的观感。
        """
        ix, iy = self.intro_offset(side)
        sx, sy = self.shake_offset()
        return (ix + sx, iy + sy)

    def shake_offset(self) -> tuple[int, int]:
        """④ 震屏偏移（结束后恒为 (0, 0)）。"""
        age = self._shake_age
        if age < 0 or age >= SHAKE_FRAMES:
            return (0, 0)
        return (SHAKE_PATTERN_X[age % len(SHAKE_PATTERN_X)],
                SHAKE_PATTERN_Y[age % len(SHAKE_PATTERN_Y)])

    def hp_display(self, side: str) -> int:
        """③ 血条当前该画的 HP（缓动显示值；收敛后 == 真实 HP）。"""
        if side == "player":
            if self.active is None:
                return 0
            return self._hp_anim.display("player", self.active.hp)
        return self._hp_anim.display("enemy", self.enemy.hp)

    @property
    def particles(self) -> list[HitParticle]:
        """⑤ 当前还活着的命中粒子。"""
        return self._particles

    # ------------------------------------------------------------ 触发
    def trigger_hit_effect(self, defender, info) -> None:
        """②⑤ 受击演出：闪烁 + 抖动 + 后移 + 粒子（克制时额外震屏）。

        由 :meth:`_apply_attack` 调用；也可以单独调用（测试用）。
        """
        if defender is None:
            return
        side = "player" if defender is self.active else "enemy"
        self._hit_age[side] = 0
        base_x, base_y = ((PLAYER_SPRITE_X, PLAYER_SPRITE_Y)
                          if side == "player"
                          else (ENEMY_SPRITE_X, ENEMY_SPRITE_Y))
        dx, dy = self.creature_offset(side)
        color = self._hit_color(info)
        bg = palette.GREEN if side == "player" else palette.LIGHT_BLUE
        for i in range(PARTICLE_COUNT):
            vx, vy = PARTICLE_DIRS[i % len(PARTICLE_DIRS)]
            self._particles.append(
                HitParticle(base_x + 16 + dx, base_y + 16 + dy,
                            vx, vy, color, bg))
        # ④ 克制命中 -> 震屏
        if self._is_super_effective(info, defender):
            self.trigger_shake()

    def trigger_shake(self) -> None:
        """④ 震屏（克制命中时调用）。"""
        self._shake_age = 0

    @staticmethod
    def _is_super_effective(info, defender) -> bool:
        """这次命中是不是克制（系数 > 1）。"""
        try:
            return multiplier(info.type, defender.species.type) > 1.0
        except Exception:
            return False

    @staticmethod
    def _hit_color(info) -> int:
        """⑤ 粒子颜色：招式属性主色；「无」属性用黄色。"""
        type_name = str(getattr(info, "type", "") or "")
        color = palette.color_of(type_name)
        if color == palette.GRAY:
            color = palette.YELLOW
        return color

    # ================================================================ 演出文字
    def _say(self, msg: str, then=None, state: str | None = None) -> None:
        """显示一条演出文字；按确认键后执行 then（可再接下一条）。"""
        self.message = str(msg)
        self._after = then
        self.state = state if state is not None else self.MESSAGE

    def _say_series(self, msgs, then=None) -> None:
        """依次显示多条文字（每条都要按一次确认键）。"""

        def chain(i: int) -> None:
            if i >= len(msgs):
                if then is not None:
                    then()
                return
            self._say(msgs[i], then=lambda: chain(i + 1))

        chain(0)

    def _dismiss_message(self) -> None:
        """关掉当前文字，执行后续动作。"""
        after = self._after
        self.message = None
        self._after = None
        if after is not None:
            after()

    # ================================================================ 菜单
    def _build_command_menu(self) -> None:
        """建五指令菜单（坐标严格按 §13.2）。"""
        items = [
            {"id": "battle", "label": "战斗", "x": COMMAND_POS["battle"][0],
             "y": COMMAND_POS["battle"][1], "col": 0, "row": 0},
            {"id": "ball", "label": "精灵球", "x": COMMAND_POS["ball"][0],
             "y": COMMAND_POS["ball"][1], "col": 1, "row": 0},
            {"id": "party", "label": "精灵", "x": COMMAND_POS["party"][0],
             "y": COMMAND_POS["party"][1], "col": 0, "row": 1},
            {"id": "item", "label": "道具", "x": COMMAND_POS["item"][0],
             "y": COMMAND_POS["item"][1], "col": 1, "row": 1},
            {"id": "run", "label": "逃跑", "x": COMMAND_POS["run"][0],
             "y": COMMAND_POS["run"][1], "col": 0, "row": 2},
        ]
        self.command_menu = MenuList(0, 0, items, line_h=20, cols=2)
        self.command_menu.index = 0

    def _build_skill_menu(self) -> None:
        """建技能列表；MP 不足的招置灰（§5.3）。"""
        items: list[dict] = []
        for sid in self.active.skills:
            info = sk.get_skill(sid)
            enabled = self.active.can_use(sid)
            label = f"{info.name}  威力{info.power}  MP{info.mp}"
            if not enabled:
                label += "  MP不足"
            items.append({"skill_id": sid, "label": label, "enabled": enabled,
                          "col": 0, "row": len(items)})
        self.skill_menu = MenuList(SKILL_X, SKILL_Y, items,
                                   line_h=SKILL_LINE_H, cols=1)
        self.skill_menu.index = 0

    def _build_party_menu(self, mode: str) -> None:
        """建队伍列表。

        mode：

        - "switch"：主动换人（不能选已倒下的，也不能选当前出战）；
        - "forced"：强制换人（只能选活着的）；
        - "revive"：复活草的目标（只能选倒下的）。
        """
        if mode == "revive":
            members = [c for c in self.player.party if c.fainted]
        elif mode == "forced":
            members = [c for c in self.player.party if not c.fainted]
        else:
            members = [c for c in self.player.party
                       if not c.fainted and c is not self.active]
        items: list[dict] = []
        for creature in members:
            label = (f"{creature.display_name} Lv{creature.level}  "
                     f"{creature.hp}/{creature.hp_max}  "
                     f"{creature.mp}/{creature.mp_max}")
            items.append({"creature": creature, "label": label,
                          "enabled": True, "col": 0, "row": len(items)})
        self.party_menu = MenuList(PARTY_X, PARTY_Y, items,
                                   line_h=PARTY_LINE_H, cols=1)
        self._party_mode = mode
        self._layout_party()

    def _layout_party(self) -> None:
        """按光标位置滚动队伍列表（最多显示 PARTY_ROWS 行）。"""
        menu = self.party_menu
        total = len(menu.items)
        start = 0
        if total > PARTY_ROWS:
            start = min(max(0, menu.index - PARTY_ROWS + 1), total - PARTY_ROWS)
        for k, item in enumerate(menu.items):
            item["x"] = PARTY_X
            if start <= k < start + PARTY_ROWS:
                item["y"] = PARTY_Y + (k - start) * PARTY_LINE_H
            else:
                item["y"] = -100

    def _battle_items(self) -> list[dict]:
        """背包里能在战斗中使用的道具（精灵球不算，它有独立指令）。"""
        items: list[dict] = []
        for item_id in sorted(self.player.bag):
            info = it.get_item(item_id)
            if info.effect not in ("heal_hp", "heal_mp", "revive"):
                continue
            count = self.player.item_count(item_id)
            if info.effect == "heal_hp":
                desc = f"  回复 {info.value} HP"
            elif info.effect == "heal_mp":
                desc = f"  回复 {info.value} MP"
            else:
                desc = "  复活一只精灵"
            items.append({"item_id": item_id,
                          "label": f"{info.name} x{count}{desc}",
                          "enabled": True, "col": 0, "row": len(items)})
        return items

    def _build_item_menu(self, items: list[dict]) -> None:
        """建道具列表。"""
        self.item_menu = MenuList(ITEM_X, ITEM_Y, items,
                                   line_h=ITEM_LINE_H, cols=1)
        self.item_menu.index = 0

    # ================================================================ 输入
    def _update_command(self, inp) -> None:
        """五指令界面（§13.2）。"""
        menu = self.command_menu
        if inp.pressed("up"):
            menu.move(-1)
        elif inp.pressed("down"):
            menu.move(1)
        elif inp.pressed("left"):
            menu.move_h(-1)
        elif inp.pressed("right"):
            menu.move_h(1)
        elif inp.pressed("confirm"):
            self._confirm_command(menu.selected.get("id"))

    def _update_skill(self, inp) -> None:
        """技能列表：MP 不足的招置灰，确认键无效（§5.3）。"""
        menu = self.skill_menu
        if inp.pressed("up"):
            menu.move(-1)
        elif inp.pressed("down"):
            menu.move(1)
        elif inp.pressed("cancel"):
            self._start_command()
        elif inp.pressed("confirm"):
            if not menu.confirm():
                return
            self._player_attack(menu.selected.get("skill_id"))

    def _update_party(self, inp) -> None:
        """队伍列表（主动 / 强制换人、复活草目标）。"""
        menu = self.party_menu
        if inp.pressed("up"):
            menu.move(-1)
        elif inp.pressed("down"):
            menu.move(1)
        elif inp.pressed("confirm"):
            if not menu.confirm():
                return
            self._confirm_party(menu.selected.get("creature"))
        # 强制换人不可取消：cancel 键在这里什么都不做
        self._layout_party()

    def _update_item(self, inp) -> None:
        """道具列表。"""
        menu = self.item_menu
        if inp.pressed("up"):
            menu.move(-1)
        elif inp.pressed("down"):
            menu.move(1)
        elif inp.pressed("cancel"):
            self._start_command()
        elif inp.pressed("confirm"):
            if not menu.confirm():
                return
            self._use_item(menu.selected.get("item_id"))

    # ================================================================ 指令
    def _confirm_command(self, command) -> None:
        """执行五指令之一（§5.1）。"""
        if command == "battle":
            self._build_skill_menu()
            self.state = self.SKILL_SELECT
        elif command == "party":
            if not self._switch_candidates():
                self._say("没有可以换的精灵！", then=self._start_command)
                return
            self._build_party_menu("switch")
            self.state = self.PARTY_SELECT
        elif command == "ball":
            self._try_catch()
        elif command == "item":
            items = self._battle_items()
            if not items:
                self._say("没有可用道具！", then=self._start_command)
                return
            self._build_item_menu(items)
            self.state = self.ITEM_SELECT
        elif command == "run":
            self._try_run()

    def _switch_candidates(self) -> list[Creature]:
        """可以换上来的精灵（存活且不是当前出战）。"""
        return [c for c in self.player.party
                if not c.fainted and c is not self.active]

    # ================================================================ 行动
    def _player_attack(self, skill_id: int) -> None:
        """我方用技能攻击（§5.2：按 SPD 决定先后）。"""
        info = sk.get_skill(skill_id)
        self.active.spend_mp(info.id)
        self._player_acted = True
        if self._player_first():
            self._player_attack_steps(info)
        else:
            # 敌方先手：先让敌方行动，结束后再轮到玩家
            self._enemy_action(then=lambda: self._player_attack_steps(info))

    def _player_attack_steps(self, info) -> None:
        """我方攻击的演出。"""
        self._say(f"{self.active.display_name} 使用了 {info.name}！",
                  then=lambda: self._apply_attack(self.active, self.enemy, info))

    def _apply_attack(self, attacker: Creature, defender: Creature, info,
                      then=None) -> None:
        """结算一次招式（伤害一律走 damage_calc.damage）。"""
        if info.effect == "damage":
            dmg = damage_calc.damage(
                attacker.attack, defender.defense, info.type, info.power,
                defender.species.type, atk_mod=attacker.atk_mod, rng=self._rng,
            )
            actual = defender.take_damage(dmg)
            self._spawn_damage(defender, actual, defender is self.active)
            # ②⑤ 受击演出（纯绘制层）；克制命中时额外 ④ 震屏
            self.trigger_hit_effect(defender, info)
            # 命中音效（T8b）：我方受击 -> hurt，打中敌人按克制系数选 hit / hit_super
            self._play_hit_sound(defender, info)
            self._say(f"{defender.display_name} 受到了 {actual} 点伤害！",
                      then=lambda: self._after_attack(attacker, defender, then))
        elif info.effect == "heal":
            amount = damage_calc.heal_amount(info, attacker.hp_max)
            actual = attacker.heal_hp(amount)
            attacker.clear_mods()
            self._say(f"{attacker.display_name} 恢复了 {actual} 点体力！",
                      then=lambda: self._after_attack(attacker, defender, then))
        else:
            # debuff_atk：敌方 ATK × value，持续 duration 回合
            defender.apply_atk_mod(info.value, info.duration)
            self._say(f"{defender.display_name} 的攻击下降了！",
                      then=lambda: self._after_attack(attacker, defender, then))

    def _play_hit_sound(self, defender: Creature, info) -> None:
        """命中音效（T8b）。

        - 被打的是**我方**出战精灵 -> 受击音（hurt）；
        - 打到敌人 -> 按克制系数选普通命中（hit）或克制命中（hit_super）。
        """
        if defender is self.active:
            sound.play_sfx("hurt")
            return
        try:
            mult = multiplier(info.type, defender.species.type)
        except Exception:
            mult = 1.0
        sound.play_sfx("hit_super" if mult > 1.0 else "hit")

    def _play_level_up(self, events) -> None:
        """经验事件里出现升级就播升级音（T8b）。"""
        for event in events or []:
            if str(event).startswith("升到"):
                sound.play_sfx("level_up")
                return

    def _after_attack(self, attacker: Creature, defender: Creature,
                       then=None) -> None:
        """一次招式之后的处理：胜负 / 倒下 / 轮到谁。"""
        if self.enemy.fainted:
            self._start_victory()
            return
        if self.active is not None and self.active.fainted:
            self._start_faint()
            return
        if then is not None:
            then()
            return
        if attacker is self.active:
            if not self._enemy_acted:
                self._enemy_action()
                return
            self._end_turn()
            return
        # 敌方刚行动完
        self._end_turn()

    def _enemy_action(self, then=None) -> None:
        """敌方行动。"""
        info = self._enemy_choose_skill()
        self.enemy.spend_mp(info.id)
        self._enemy_acted = True
        self._say(f"{self.enemy.display_name} 使用了 {info.name}！",
                  then=lambda: self._apply_attack(self.enemy, self.active, info,
                                                  then))

    def _enemy_turn(self) -> None:
        """玩家已行动（非攻击指令）-> 敌方行动（§5.2）。"""
        self._enemy_action()

    def _enemy_choose_skill(self):
        """敌方选招：优先期望伤害最高的可用攻击招。"""
        usable = []
        for sid in self.enemy.skills:
            info = sk.get_skill(sid)
            if not self.enemy.can_use(sid):
                continue
            if info.effect == "heal" and self.enemy.hp >= self.enemy.hp_max:
                continue
            usable.append(info)
        damaging = [i for i in usable if i.effect == "damage"]
        if damaging:
            def score(info):
                return damage_calc.expected_damage(
                    self.enemy.attack, self.active.defense, info.type,
                    info.power, self.active.species.type,
                    atk_mod=self.enemy.atk_mod,
                )
            return max(damaging, key=lambda i: (score(i), i.power))
        if usable:
            return usable[0]
        return sk.get_skill(1)

    def _player_first(self) -> bool:
        """我方是否先手（§5.2）：SPD 大者先手，相等 50% 随机。"""
        mine = self.active.speed
        theirs = self.enemy.speed
        if mine > theirs:
            return True
        if mine < theirs:
            return False
        return self._rng.random() < 0.5

    def _end_turn(self) -> None:
        """回合结束：双方能力下降计时 -1，然后回到五指令。"""
        if self.active is not None:
            self.active.tick_mods()
        self.enemy.tick_mods()
        self._start_command()

    def _start_command(self) -> None:
        """回到五指令界面。"""
        self.state = self.COMMAND
        self._enemy_acted = False
        self._player_acted = False
        self.command_menu.index = 0

    # ================================================================ 捕捉
    def _try_catch(self) -> None:
        """使用精灵球（§5.1 / §8）。"""
        if self.player.item_count(BALL_ITEM_ID) <= 0:
            self._say("没有精灵球了！", then=self._start_command)
            return
        self.player.remove_item(BALL_ITEM_ID, 1)
        self._player_acted = True
        self._say("抛出精灵球……", then=self._resolve_catch, state=self.CATCH)

    def _resolve_catch(self) -> None:
        """捕捉判定。"""
        ok = catch_calc.try_catch(
            self.enemy.hp, self.enemy.hp_max, self.enemy.species.catch_coef,
            catch_calc.BALL_MULTIPLIER, self._rng,
        )
        if not ok:
            sound.play_sfx("catch_fail")
            self._say("……没能捕捉到！", then=self._enemy_turn)
            return

        where = self.player.add_creature(self.enemy)
        place = "队伍" if where == "party" else "仓库"
        msgs = [f"捕捉成功！{self.enemy.display_name} 加入了{place}！"]
        exp = catch_exp(self.enemy.level)
        events = self.active.gain_exp(exp)
        for event in events:
            msgs.append(f"{self.active.display_name} {event}")
        sound.play_sfx("catch_ok")
        self._play_level_up(events)
        self._say_series(msgs, then=lambda: self._finish_battle(self.RESULT_CATCH))

    # ================================================================ 逃跑
    def _try_run(self) -> None:
        """逃跑判定（§5.5）。"""
        self._player_acted = True
        chance = escape_chance(self.active.speed, self.enemy.speed)
        if self._rng.random() < chance:
            sound.play_sfx("escape")
            self._say("成功逃走了！",
                      then=lambda: self._finish_battle(self.RESULT_RUN))
        else:
            self._say("没能逃走！", then=self._enemy_turn)

    # ================================================================ 道具
    def _use_item(self, item_id: int) -> None:
        """使用道具（§5.1）。"""
        info = it.get_item(item_id)
        if info.effect == "revive":
            if not [c for c in self.player.party if c.fainted]:
                self._say("没有可以复活的精灵！", then=self._start_command)
                return
        if not self.player.remove_item(item_id, 1):
            self._say("道具不够用了！", then=self._start_command)
            return
        self._player_acted = True
        if info.effect == "heal_hp":
            actual = self.active.heal_hp(info.value)
            self._say(f"{self.active.display_name} 恢复了 {actual} 点体力！",
                      then=self._enemy_turn)
        elif info.effect == "heal_mp":
            actual = self.active.heal_mp(info.value)
            self._say(f"{self.active.display_name} 恢复了 {actual} 点 MP！",
                      then=self._enemy_turn)
        else:
            # 复活草：选一只倒下的精灵
            self._build_party_menu("revive")
            self.state = self.PARTY_SELECT

    # ================================================================ 换人
    def _confirm_party(self, creature: Creature) -> None:
        """确认换人 / 复活。"""
        if creature is None:
            self._start_command()
            return
        mode = self._party_mode
        if mode == "revive":
            creature.revive(0.5)
            self._say(f"{creature.display_name} 复活了！", then=self._enemy_turn)
            return

        old = self.active
        self.active = creature
        self._player_acted = True
        msgs = []
        if old is not None and old is not creature:
            msgs.append(f"回来吧，{old.display_name}！")
        msgs.append(f"去吧，{creature.display_name}！")
        then = self._end_turn if mode == "forced" else self._enemy_turn
        self._say_series(msgs, then=then)

    # ================================================================ 倒下
    def _start_faint(self) -> None:
        """我方出战精灵倒下（§5.4）：强制换人 / 战败。"""
        if not self.player.alive_party():
            self._start_defeat()
            return
        self._build_party_menu("forced")
        self.state = self.FORCED_SWITCH

    # ================================================================ 胜利
    def _start_victory(self) -> None:
        """战斗胜利结算（§5.7）。"""
        sound.play_sfx("victory")
        msgs = [f"{self.enemy.display_name} 被打倒了！"]
        msgs.extend(self._grant_victory_rewards())
        self._say_series(msgs, then=lambda: self._finish_battle(self.RESULT_WIN))

    def _grant_victory_rewards(self) -> list[str]:
        """发放胜利奖励（§5.7），返回要显示的文字。"""
        msgs: list[str] = []
        mp_gain = mp_recover_amount(self.active.mp_max)
        exp = victory_exp(self.enemy.level)
        events = self.active.gain_exp(exp)
        for event in events:
            msgs.append(f"{self.active.display_name} {event}")
        self._play_level_up(events)
        money = victory_dollars(self.enemy.level)
        self.player.dollars += money
        msgs.append(f"获得 {money} 金币！")
        sound.play_sfx("coin")
        self.active.heal_mp(mp_gain)
        msgs.append(f"{self.active.display_name} 恢复了 {mp_gain} 点 MP！")
        return msgs

    # ================================================================ 战败
    def _start_defeat(self) -> None:
        """战败流程（§5.6）：淡出 -> 台词 -> 全队回复 -> 回新手村。"""
        sound.play_sfx("defeat")
        self.state = self.RESULT
        self.fade.start_out(DEFEAT_FADE_FRAMES, on_done=self._defeat_fade_done)

    def _defeat_fade_done(self) -> None:
        """淡出结束：全队回复 + 台词。"""
        self.player.heal_all()
        spawn = map_data.get_map(map_data.START_MAP_ID)["spawn"]
        state = getattr(self.game, "player_state", None)
        if state is not None:
            state["map_id"] = map_data.START_MAP_ID
            state["x"] = spawn[0]
            state["y"] = spawn[1]
            state["dollars"] = self.player.dollars
        self._defeat_text = "你眼前一黑……醒来时已经躺在了村子的精灵中心。"
        self._say(self._defeat_text, then=self._finish_defeat, state=self.RESULT)

    def _finish_defeat(self) -> None:
        """战败收尾：回新手村出生点，不扣金币。"""
        self.result = self.RESULT_LOSE
        self.state = self.RESULT
        if self.on_end is not None:
            self.on_end(self.RESULT_LOSE)
        spawn = map_data.get_map(map_data.START_MAP_ID)["spawn"]
        self.game.player_state["dollars"] = self.player.dollars
        self.game.scenes.replace(FieldScene(self.game),
                                 map_id=map_data.START_MAP_ID,
                                 x=spawn[0], y=spawn[1])

    # ================================================================ 结束
    def _finish_battle(self, result: str) -> None:
        """战斗结束：写回金币 -> 调用 on_end -> 回到地图（保持原位置）。"""
        self.result = result
        self.state = self.RESULT
        if self.on_end is not None:
            self.on_end(result)
        state = getattr(self.game, "player_state", None) or {}
        map_id = state.get("map_id", map_data.START_MAP_ID)
        x = state.get("x")
        y = state.get("y")
        self.game.player_state["dollars"] = self.player.dollars
        self.game.scenes.replace(FieldScene(self.game), map_id=map_id,
                                 x=x, y=y)

    # ================================================================ 飘字
    def _spawn_damage(self, creature: Creature, value: int,
                       player_side: bool) -> None:
        """在受击的精灵身上冒一个圆圈数字（§13.3）。"""
        if player_side:
            x = PLAYER_SPRITE_X + 16
            y = PLAYER_SPRITE_Y + 16
        else:
            x = ENEMY_SPRITE_X + 16
            y = ENEMY_SPRITE_Y + 16
        self.numbers.add(x, y, value, "player" if player_side else "enemy")

    # ================================================================ 绘制
    def _draw_background(self) -> None:
        """背景：天空 + 地面 + 两个站台（④ 震屏时整体跟着晃）。"""
        sx, sy = self.shake_offset()
        pyxel.cls(palette.LIGHT_BLUE)
        top = HORIZON_Y + sy
        # 地面画高 4px，震屏时上下移动也不会露出缝
        pyxel.rect(0, top, SCREEN_W, SCREEN_H - HORIZON_Y + 4, palette.GREEN)
        pyxel.rect(0, top, SCREEN_W, 2, palette.DARK_GREEN)
        # 敌方站台（跟着敌方精灵一起滑入，震屏时一起晃）
        ex, ey = self.platform_offset("enemy")
        pyxel.elli(136 + ex, 49 + ey, 60, 18, palette.DARK_GREEN)
        pyxel.elli(140 + ex, 54 + ey, 52, 12, palette.GREEN)
        # 我方站台
        px, py = self.platform_offset("player")
        pyxel.elli(10 + px, 113 + py, 60, 18, palette.DARK_GREEN)
        pyxel.elli(14 + px, 118 + py, 52, 12, palette.GREEN)

    def _draw_creature(self, creature: Creature, x: int, y: int,
                       side: str | None = None) -> None:
        """画一只精灵的 32x32 战斗图（倒下的不画）。

        绘制偏移的来源（都只在绘制层生效）：

        - ① 入场动画；
        - ② 受击闪烁 / 抖动 / 后移；
        - ④ 震屏。
        """
        if creature is None or creature.fainted:
            return
        if side is None:
            side = "enemy" if int(x) == ENEMY_SPRITE_X else "player"
        if self._hit_blink(side):
            return                       # ② 受击闪烁：这一帧不画精灵
        try:
            img = sprite_base.get(f"creature_{creature.species_id}_battle")
        except KeyError:
            return
        dx, dy = self.creature_offset(side)
        sx, sy = self.shake_offset()
        pyxel.blt(x + dx + sx, y + dy + sy, img, 0, 0, 32, 32, colkey=0)

    def _hit_blink(self, side: str) -> bool:
        """② 受击闪烁：前 HIT_FLASH_FRAMES 帧里隔帧不画精灵。"""
        age = self._hit_age.get(side, -1)
        if age < 0 or age >= HIT_FLASH_FRAMES:
            return False
        return (age % 2) == 1

    def _draw_particles(self) -> None:
        """⑤ 画命中粒子。"""
        offset = self.shake_offset()
        for particle in self._particles:
            particle.draw(offset)

    def _draw_status_boxes(self) -> None:
        """画双方信息框（§13.1）。"""
        sx, sy = self.shake_offset()
        draw_status_box(ENEMY_BOX_X + sx, ENEMY_BOX_Y + sy,
                        self.enemy.display_name, self.enemy.level,
                        self.enemy.hp, self.enemy.hp_max,
                        self.enemy.mp, self.enemy.mp_max,
                        hp_display=self.hp_display("enemy"))
        if self.active is not None:
            draw_status_box(PLAYER_BOX_X + sx, PLAYER_BOX_Y + sy,
                            self.active.display_name, self.active.level,
                            self.active.hp, self.active.hp_max,
                            self.active.mp, self.active.mp_max,
                            hp_display=self.hp_display("player"))

    def _draw_panel(self) -> None:
        """画底部面板（§13.1：(0, 150) 240×66）。"""
        pyxel.rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H, palette.LIGHT_GRAY)
        pyxel.rectb(PANEL_X, PANEL_Y, PANEL_W, PANEL_H, palette.DARK_PURPLE)

        state = self.state
        if state == self.INTRO:
            text.draw_wrapped(PANEL_X + 8, PANEL_Y + 8, self.intro_text,
                              PANEL_W - 16, palette.BLACK)
        elif state == self.MESSAGE:
            text.draw_wrapped(PANEL_X + 8, PANEL_Y + 8, self.message or "",
                              PANEL_W - 16, palette.BLACK)
        elif state == self.COMMAND:
            self.command_menu.draw()
            count = self.player.item_count(BALL_ITEM_ID)
            text.draw(BALL_COUNT_X, COMMAND_POS["ball"][1], f"x{count}",
                      palette.GRAY)
        elif state == self.SKILL_SELECT:
            self.skill_menu.draw()
        elif state in (self.PARTY_SELECT, self.FORCED_SWITCH):
            self.party_menu.draw()
            hint = ("选一只精灵（不能取消）" if state == self.FORCED_SWITCH
                    else "选择要出战的精灵")
            text.draw(PANEL_X + 8, PARTY_HINT_Y, hint, palette.DARK_PURPLE)
        elif state == self.ITEM_SELECT:
            self.item_menu.draw()
        elif state == self.CATCH:
            text.draw_wrapped(PANEL_X + 8, PANEL_Y + 8, self.message or "",
                              PANEL_W - 16, palette.BLACK)

    def _draw_defeat_text(self) -> None:
        """战败台词画在黑屏上（淡出之后）。"""
        if not getattr(self, "_defeat_text", None):
            return
        if self.message is None:
            return
        lines = text.wrap(self.message, 210)
        y = 96 - (len(lines) - 1) * 7
        for i, line in enumerate(lines):
            text.draw_center(SCREEN_W // 2, y + i * 14, line, palette.WHITE)
