"""开局三选一场景（批 3 / T5）。

画面
----
- 深蓝底，顶部标题「选择你的初始精灵」；
- 三只精灵的 32x32 战斗图横排（复用 sprite_base 里已有的素材）；
- 选中的那只套一个黄色框；
- 下方显示所选精灵的名字 / 属性 / 定位 / 五维 / 初始技能；
- 底部提示按键。

操作
----
- 左右键：移动光标；
- 确认键：确定，开局（``game.player = Player.new_game(种族 ID)``）并进入地图 1；
- 取消键：回到标题画面。
"""

from __future__ import annotations

import pyxel

from src.assets_gen import palette, sprite_base
from src.data import map_data, skill_data, species_data as sd
from src.model.player import Player
from src.scenes.field_scene import FieldScene
from src.scenes.scene_base import Scene
from src.ui import text

#: 画面尺寸（与 main.py 锁定值一致）
SCREEN_W = 240
SCREEN_H = 216

#: 标题
TITLE_TEXT = "选择你的初始精灵"

#: 布局
TITLE_Y = 10
SPRITE_Y = 38
SPRITE_SIZE = 32
#: 三只精灵的 x 坐标（等距）
SPRITE_XS: tuple[int, ...] = (24, 104, 184)

NAME_Y = 92
STATS_Y = 112
SKILL_Y = 136
HINT_Y = 190
HINT_TEXT = "← → 选择    Z 确认    X 返回"

#: 开局地图（《数值设定.md》§10.1 新手村）
START_MAP_ID = map_data.START_MAP_ID


class StarterScene(Scene):
    """开局三选一：小火狮 / 水滴滴 / 兔小子（《数值设定.md》§3.1）。"""

    def __init__(self, game):
        super().__init__(game)
        #: 三只候选精灵的种族 ID
        self.ids: tuple[int, ...] = tuple(sd.STARTER_IDS)
        #: 光标（0..2）
        self.index: int = 0

    # ------------------------------------------------------------ 生命周期
    def enter(self, **kwargs) -> None:
        """进入：烘焙素材、光标回到第一只。"""
        sprite_base.bake_all()
        self.index = 0

    def resume(self) -> None:
        """重新回到前台：状态保留，不重置。"""

    def exit(self) -> None:
        """退出：什么都不用清理。"""

    # ------------------------------------------------------------ 查询
    @property
    def species_id(self) -> int:
        """当前选中的种族 ID。"""
        if not self.ids:
            return 0
        return int(self.ids[self.index % len(self.ids)])

    def initial_skills(self, species_id: int | None = None) -> list[int]:
        """某只精灵的初始技能 ID 列表。"""
        sid = self.species_id if species_id is None else int(species_id)
        species = sd.get_species(sid)
        return list(species.learnset.get(1, []))

    # ------------------------------------------------------------ 每帧
    def update(self, inp) -> None:
        """每帧逻辑更新。"""
        if not self.ids:
            return
        if inp.pressed("left"):
            self.index = (self.index - 1) % len(self.ids)
        if inp.pressed("right"):
            self.index = (self.index + 1) % len(self.ids)
        if inp.pressed("confirm"):
            self.start_game()
        elif inp.pressed("cancel"):
            self.back_to_title()

    def start_game(self) -> None:
        """确定选择：建玩家、进地图。"""
        species_id = self.species_id
        player = Player.new_game(species_id)
        self.game.player = player

        spawn = map_data.get_map(START_MAP_ID)["spawn"]
        state = getattr(self.game, "player_state", None)
        if state is None:
            state = {}
            self.game.player_state = state
        state["dollars"] = int(player.dollars)
        state["map_id"] = START_MAP_ID
        state["x"] = int(spawn[0])
        state["y"] = int(spawn[1])
        state["facing"] = "down"

        self.game.play_frames = 0
        self.game.scenes.replace(FieldScene(self.game), map_id=START_MAP_ID)

    def back_to_title(self) -> None:
        """取消：回到标题画面。"""
        from src.scenes.title_scene import TitleScene   # 局部导入避免循环引用

        self.game.scenes.replace(TitleScene(self.game))

    # ------------------------------------------------------------ 绘制
    def draw(self) -> None:
        """绘制整个三选一画面。"""
        pyxel.cls(palette.DEEP_BLUE)

        text.draw_center(SCREEN_W // 2, TITLE_Y, TITLE_TEXT, palette.YELLOW)

        for i, species_id in enumerate(self.ids):
            self._draw_species(species_id, i)

        self._draw_info()

        text.draw_center(SCREEN_W // 2, HINT_Y, HINT_TEXT, palette.GRAY)

    def _draw_species(self, species_id: int, slot: int) -> None:
        """画一只精灵的战斗图（选中的套黄框）。"""
        if slot >= len(SPRITE_XS):
            return
        x = SPRITE_XS[slot]
        try:
            img = sprite_base.get(f"creature_{int(species_id)}_battle")
        except KeyError:      # pragma: no cover - 素材缺失
            return
        if slot == self.index:
            pyxel.rectb(x - 4, SPRITE_Y - 4, SPRITE_SIZE + 8, SPRITE_SIZE + 8,
                        palette.YELLOW)
        pyxel.blt(x, SPRITE_Y, img, 0, 0, SPRITE_SIZE, SPRITE_SIZE, colkey=0)

    def _draw_info(self) -> None:
        """下方：所选精灵的名字 / 属性 / 五维 / 初始技能。"""
        if not self.ids:
            return
        species = sd.get_species(self.species_id)
        color = palette.color_of(species.type)

        text.draw(16, NAME_Y, species.name, palette.WHITE)
        name_w = text.width(species.name)
        text.draw(16 + name_w + 8, NAME_Y, species.type, color)
        type_w = text.width(species.type)
        text.draw(16 + name_w + 8 + type_w + 8, NAME_Y, species.role, palette.GRAY)

        stats = sd.stats_at(species.id, 5)
        line = (f"HP{stats['HP']} MP{stats['MP']} "
                f"攻{stats['ATK']} 防{stats['DEF']} 速{stats['SPD']}")
        text.draw(16, STATS_Y, line, palette.LIGHT_GRAY)

        names = [skill_data.get_skill(s).name for s in self.initial_skills()]
        text.draw(16, SKILL_Y, f"初始技能：{'、'.join(names)}", palette.LIGHT_GRAY)
