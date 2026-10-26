"""标题画面（批 3 / T5 · T17 场景化封面）。

画面
----
封面是一幅有景深的像素风景（见 src/ui/title_art.py），标题压在风景上：

    天空渐变（拜耳抖动过渡）+ 星 + 月
      远山剪影（蓝，山脊一线橙光，带雪线）
        近山剪影（深蓝，山脊一线粉光）
          针叶林剪影（深绿，右缘受光）
            草地（暗部抖动 + 草叶 + 花 + 石头）
              左右两只精灵（32x32 战斗图 + 脚下投影）夹住标题
                标题「精灵对战」：黄色 + 橙色立体底边 + 深紫描边，2 倍放大
                  菜单面板：深蓝板 + 浅灰描边，两项「新游戏」「继续游戏」

整张风景（含标题、精灵、菜单板）由 title_art.bake_background
**烘焙一次并缓存**，本场景每帧只做一次 blt + 两项菜单文字，所以绘制开销与环境
复杂度无关；菜单文字与光标随状态变色，必须实时画。

光标用 pyxel.tri() 画的小三角形而不是 "▶" 字符，
因为字体里的 ▶ 字形不保证存在（《数值设定.md》§13.2 允许这两种做法）。

「新游戏」按确认键 -> 开局三选一（StarterScene，挑初始精灵）；
「继续游戏」按确认键 -> 读档（save_io.load_game）：

- "ok"          -> 进入 FieldScene（地图 / 坐标 / 朝向都来自存档）；
- "no_file"     -> 菜单上方显示「没有找到存档」120 帧（2 秒）；
- "bad_version" -> 显示「存档版本不兼容」；
- "corrupt"     -> 显示「存档已损坏」。

三种失败都**不崩溃**、**不改写原存档**。

T17 变更
--------
- 去掉底部版本号小字（用户明确要求）：FOOTER_TEXT / FOOTER_Y 连同绘制一起删除；
- 背景 / 标题 / 精灵 / 菜单板交给 src/ui/title_art.py；
- 菜单文字改成选中黄、未选白，读档失败提示加了深色底板，保证压在风景上读得清；
- **行为一个字节都没动**：上下键切菜单、确认键执行、提示持续 HINT_FRAMES 帧、
  音效、三种失败文案全部原样。
"""

from __future__ import annotations

from src.assets_gen import palette
from src.data import map_data
from src.model import save_io
from src.scenes.field_scene import FieldScene
from src.scenes.scene_base import Scene
from src.scenes.starter_scene import StarterScene
from src.ui import sound, title_art

TITLE_TEXT = "精灵对战"
MENU_ITEMS: tuple[str, ...] = ("新游戏", "继续游戏")

#: 画面布局（封面几何统一由 src/ui/title_art.py 定义，这里做转发，
#: 保证原有的常量名依然可导入）
#: 标题画面仍以屏幕中线为对称轴（标题 / 读档失败提示都用它）
TITLE_X = title_art.TITLE_CX
TITLE_Y = title_art.TITLE_TOP
MENU_X = title_art.MENU_TEXT_X
MENU_Y = title_art.MENU_FIRST_Y
MENU_STEP = title_art.MENU_STEP
CURSOR_X = title_art.CURSOR_X
#: 读档失败提示的 y 坐标与持续帧数
#: HINT_Y 放在菜单面板**正上方**的草地上：提示自带深色底板，落在草地阴影上
#: 对比度足够，而且不会压住菜单面板的边框（面板顶边在 y=163）。
#: HINT_FRAMES = 120 帧 @60fps = 2 秒，与 60 帧 @30fps 一致
HINT_Y = 144
HINT_FRAMES = 120

#: 读档结果码 -> 提示文字
LOAD_ERROR_HINTS: dict[str, str] = {
    save_io.RESULT_NO_FILE: "没有找到存档",
    save_io.RESULT_BAD_VERSION: "存档版本不兼容",
    save_io.RESULT_CORRUPT: "存档已损坏",
}


class TitleScene(Scene):
    """标题画面。"""

    def __init__(self, game):
        super().__init__(game)
        self.index = 0
        #: 读档失败提示（空串 = 不显示）
        self.hint: str = ""
        self.hint_timer: int = 0

    # ------------------------------------------------------------ 生命周期
    def enter(self, **kwargs) -> None:
        """进入标题画面：光标回到第一项，提示清空。"""
        self.index = 0
        self.hint = ""
        self.hint_timer = 0

    # ------------------------------------------------------------ 每帧
    def update(self, inp) -> None:
        """上下键移动光标，确认键执行对应菜单项。"""
        if inp.pressed("up"):
            self.index = (self.index - 1) % len(MENU_ITEMS)
            sound.play_sfx("cursor")
        if inp.pressed("down"):
            self.index = (self.index + 1) % len(MENU_ITEMS)
            sound.play_sfx("cursor")
        if self.hint_timer > 0:
            self.hint_timer -= 1
            if self.hint_timer <= 0:
                self.hint_timer = 0
                self.hint = ""
        if inp.pressed("confirm"):
            sound.play_sfx("confirm")
            if self.index == 0:
                # 新游戏：开局三选一（挑初始精灵）
                self.game.scenes.replace(StarterScene(self.game))
            else:
                # 继续游戏：读档
                self._continue_game()

    def _continue_game(self) -> None:
        """读档：成功进地图，失败在标题下方给一行提示。"""
        result = save_io.load_game(self.game)
        if result == save_io.RESULT_OK:
            state = getattr(self.game, "player_state", None) or {}
            self.game.scenes.replace(
                FieldScene(self.game),
                map_id=state.get("map_id", map_data.START_MAP_ID),
                x=state.get("x"),
                y=state.get("y"),
                facing=state.get("facing"),
            )
            return
        self.hint = LOAD_ERROR_HINTS.get(result, "读档失败")
        self.hint_timer = HINT_FRAMES

    def draw(self) -> None:
        """绘制标题画面。"""
        # 整幅封面（天空 / 山 / 林 / 草地 / 精灵 / 标题 / 菜单板）：一次 blt
        title_art.draw_background()

        for i, item in enumerate(MENU_ITEMS):
            title_art.draw_menu_item(
                MENU_X, MENU_Y + i * MENU_STEP, item, i == self.index
            )

        if self.hint:
            title_art.draw_hint(HINT_Y, self.hint, palette.YELLOW)
