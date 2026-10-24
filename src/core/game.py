"""App 主类：update / draw 分发到当前场景（规划文档 §二 core/game.py）。

职责
----
- 启动时加载字体、烘焙全部素材；
- 持有场景栈（SceneManager）与输入（Input）；
- 每帧把 update / draw 分发到当前场景；
- **退出确认弹窗**（批 5 / T10）：按 `Esc` 弹出居中对话框，
  可以「存档并退出 / 直接退出 / 取消」，弹窗期间**游戏逻辑暂停**。

`self.input` 默认是 `RealInput()`，测试时可以直接替换成 `FakeInput`：

    game = Game()
    game.input = FakeInput(script=[{"confirm": 3}])

退出确认弹窗（T10）
------------------
- `main.py` 里 `pyxel.init(..., quit_key=pyxel.KEY_NONE)` 关掉了 Pyxel 自带的
  「Esc 立刻退出」，改由本模块接管 Esc，所以玩家按 Esc **不会立刻消失**；
- 弹窗是 **Game 层**的（不是某个场景的），所以标题画面 / 地图 / 战斗 / 商店
  里按 Esc 都会弹同一个框；
- 弹窗打开时 **不调用 `scene.update()`**（游戏逻辑暂停，玩家动不了），
  但场景照常绘制，弹窗画在**所有内容之上**；
- 「存档并退出」写档成功才退出；失败**不退出**，把原因显示在弹窗里，
  玩家可以改选「直接退出」；
- `game.player is None`（还停在标题画面、没开局）时，
  「存档并退出」**置灰不可选**，只能「直接退出 / 取消」。

可测试性
--------
真正的退出是 `Game._do_quit()`（内部调 `pyxel.quit()`）。
`pyxel.quit()` 会**直接结束整个 Python 进程**，所以测试必须把它替换成桩：

    game._do_quit = lambda: calls.append("quit")
"""

from __future__ import annotations

import pyxel

from src.assets_gen import palette, sprite_base
from src.core.input import Input, RealInput
from src.core.scene_manager import SceneManager
from src.data import map_data
from src.model import Player
from src.model import save_io
from src.scenes.title_scene import TitleScene
from src.ui import text

#: 画面尺寸（与 main.py 锁定值一致）
SCREEN_W = 240
SCREEN_H = 216

#: 退出确认弹窗的三个选项：(按键提示, 动作 id, 显示文字)
#: 动作 id：save = 存档并退出 / quit = 直接退出 / cancel = 取消
QUIT_OPTIONS: tuple[tuple[str, str, str], ...] = (
    ("Z", "save", "存档并退出"),
    ("C", "quit", "直接退出"),
    ("X", "cancel", "取消"),
)

#: 弹窗标题
QUIT_TITLE = "要退出游戏吗？"
#: 弹窗几何（居中）
QUIT_BOX_W = 168
QUIT_BOX_H = 100
QUIT_BOX_X = (SCREEN_W - QUIT_BOX_W) // 2
QUIT_BOX_Y = (SCREEN_H - QUIT_BOX_H) // 2
#: 选项行的起始 y 与行距
QUIT_OPTION_Y = QUIT_BOX_Y + 28
QUIT_OPTION_STEP = 18
#: 失败原因提示的 y
QUIT_MESSAGE_Y = QUIT_BOX_Y + 82


class Game:
    """游戏主对象。"""

    def __init__(self, input: Input | None = None):
        # 字体与素材必须先准备好，后面任何一帧绘制都要用
        text.init_font()
        sprite_base.bake_all()

        #: 输入源，测试可替换
        self.input: Input = input if input is not None else RealInput()
        #: 场景栈
        self.scenes = SceneManager()
        #: 玩家状态（存档 / HUD 读它；后续批次继续扩字段）
        # 初始金币 300（《数值设定.md》§7.1），起始地图 1 新手村
        # （出生点 15, 10，与 §11 存档格式里的 player 字段一致）。
        self.player_state: dict = {
            "dollars": 300,
            "map_id": map_data.START_MAP_ID,
            "x": 15,
            "y": 10,
            "facing": "down",
        }

        #: 玩家状态（队伍 / 金币 / 背包）。
        #: **未开局时是 None**：玩家由「开局三选一」（StarterScene）或
        #: 「继续游戏」（load_game）创建，标题画面不需要玩家。
        #: 任何场景都必须容忍 player 为 None（见 menu_scene 的 _player()）。
        self.player: Player | None = None

        #: 游戏内计时（帧）。存档里的 play_seconds = play_frames // 60。
        self.play_frames: int = 0

        #: 退出确认弹窗是否打开（批 5 / T10）
        self.quit_dialog_active: bool = False
        #: 弹窗里的补充说明（空串 = 不显示），例如存档失败的原因
        self.quit_message: str = ""

        self.scenes.push(TitleScene(self))

    # ------------------------------------------------------------ 每帧
    def update(self) -> None:
        """分发一帧逻辑更新。

        顺序：先跑场景逻辑，再让输入推进到下一帧
        （这样第 N 帧的场景看到的就是第 N 帧的输入状态）。
        """
        # 退出确认弹窗打开时：**游戏逻辑暂停**（不跑场景的 update），
        # 只处理弹窗自己的输入；弹窗期间也不计时（play_frames 不涨）。
        if self.quit_dialog_active:
            self._update_quit_dialog()
            self.input.update()
            return

        # Esc -> 打开退出确认弹窗（Pyxel 自带的退出键已在 main.py 关掉）
        if self.input.pressed("quit"):
            self.open_quit_dialog()
            self.input.update()
            return

        self.play_frames += 1

        # 金币以 player 为准（战斗 / 商店改的都是 player.dollars），
        # 这里同步回 player_state，HUD 与存档都读它。
        if self.player is not None:
            state = getattr(self, "player_state", None)
            if isinstance(state, dict):
                state["dollars"] = int(self.player.dollars)

        scene = self.scenes.current
        if scene is not None:
            scene.update(self.input)
        self.input.update()

    def draw(self) -> None:
        """分发一帧绘制。"""
        scene = self.scenes.current
        if scene is not None:
            scene.draw()
        # 退出确认弹窗画在**所有场景内容之上**
        if self.quit_dialog_active:
            self._draw_quit_dialog()

    # ------------------------------------------------------------ 退出确认
    def open_quit_dialog(self) -> None:
        """打开退出确认弹窗（对所有场景生效）。"""
        self.quit_dialog_active = True
        self.quit_message = ""

    def close_quit_dialog(self) -> None:
        """关闭退出确认弹窗，回到游戏。"""
        self.quit_dialog_active = False
        self.quit_message = ""

    def quit_options(self) -> list[dict]:
        """弹窗的三个选项（含可用状态）。

        还没开局（`player is None`）时「存档并退出」**不可用**（置灰），
        此时只有「直接退出 / 取消」两项可选。
        """
        can_save = self.player is not None
        options = []
        for key, action, label in QUIT_OPTIONS:
            options.append({
                "key": key,
                "action": action,
                "label": label,
                "enabled": can_save if action == "save" else True,
            })
        return options

    def _do_quit(self) -> None:
        """真正退出游戏。

        **单独一个方法是为了可测**：`pyxel.quit()` 会直接结束整个进程，
        测试里用桩替换掉它（`game._do_quit = lambda: ...`）。
        """
        pyxel.quit()

    def _quit_and_save(self) -> None:
        """「存档并退出」：写档成功才退出；失败**不退出**，把原因显示在弹窗里。"""
        if self.player is None:
            # 还没开局：没有队伍可存，存档项本来就该是灰的
            self.quit_message = "还没开始游戏，没有可保存的进度"
            return
        try:
            ok = bool(save_io.save_game(self))
        except Exception:            # pragma: no cover - 存档层已自己兜底
            ok = False
        if not ok:
            self.quit_message = "存档失败：无法写入存档文件"
            return
        self._do_quit()

    def _update_quit_dialog(self) -> None:
        """弹窗输入：Z 存档并退出 / C 直接退出 / X 取消（Esc 也等于取消）。"""
        if self.input.pressed("confirm"):        # Z
            self._quit_and_save()
            return
        if self.input.pressed("menu"):           # C
            self._do_quit()
            return
        if self.input.pressed("cancel"):         # X
            self.close_quit_dialog()
            return
        if self.input.pressed("quit"):           # Esc 也能取消
            self.close_quit_dialog()

    def _draw_quit_dialog(self) -> None:
        """绘制退出确认弹窗（盖在所有场景内容之上）。"""
        # 压暗背景（每隔 4 行铺一条深蓝，25% 覆盖），把注意力集中到弹窗上
        for y in range(0, SCREEN_H, 4):
            pyxel.rect(0, y, SCREEN_W, 1, palette.DEEP_BLUE)

        x, y = QUIT_BOX_X, QUIT_BOX_Y
        w, h = QUIT_BOX_W, QUIT_BOX_H
        pyxel.rect(x, y, w, h, palette.LIGHT_GRAY)
        pyxel.rectb(x, y, w, h, palette.DARK_PURPLE)
        pyxel.rectb(x + 1, y + 1, w - 2, h - 2, palette.GRAY)

        text.draw_center(SCREEN_W // 2, y + 6, QUIT_TITLE, palette.DEEP_BLUE)

        for i, option in enumerate(self.quit_options()):
            line = f"{option['key']}  {option['label']}"
            color = palette.BLACK if option["enabled"] else palette.GRAY
            text.draw(x + 26, QUIT_OPTION_Y + i * QUIT_OPTION_STEP, line, color)

        if self.quit_message:
            text.draw_center(SCREEN_W // 2, QUIT_MESSAGE_Y,
                             self.quit_message, palette.RED)
