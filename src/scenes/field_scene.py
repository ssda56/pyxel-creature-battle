"""地图探索场景（里程碑 M1 / 批 1 + 里程碑 M3 / T4 明雷遇敌）。

本批实现
--------
- 四向网格移动：按住方向键连续走格，每格 **10 帧**插值（像素级平滑）；
- 走路动画：移动中每 10 帧切一帧（player_{方向}_{0|1}），静止用帧 0；
- 碰撞：目标格在 BLOCKED_TILES 或越界则不动（但朝向仍然改变）；
- 摄像机：玩家居中并夹在地图边界内，地图比视口小则整体居中；
- HUD：左上角「金币 N」（色 10 黄）+ 右上角地图名；
- NPC 对话：面向相邻格的 NPC 按确认键，底部对话框逐句显示；
- Portal：踩到出入口格 -> 淡出 -> 换地图 -> 淡入；
- menu 键：**压栈**打开菜单（MenuScene），关掉后地图状态原样保留。

坐标约定
--------
- 格坐标 (gx, gy)：整数，x 向右、y 向下；
- 像素坐标 (px, py)：浮点，主角精灵**左上角**在屏幕上的位置（未减摄像机）；
  静止时 px = gx * 16、py = gy * 16，移动时在两格之间线性插值。

明雷遇敌（T4，《数值设定.md》§10.3 / §10.4）
-------------------------------------
- 野外状态**挂在 game 上**（game.wild_state），跨场景存活：
  战斗结束时 T3b 会 replace(FieldScene)，地图场景会被整个重建，
  所以刷怪状态（存活精灵、重生冷却）不能存在 FieldScene 实例里；
- game.wild_state[map_id] = {"wanderers": [...], "cooldown": {spawn_index: 帧数}}；
- game.wild_rng：随机源（测试可注入 random.Random(seed)）；
- 刷怪：进入地图按 max_alive 从刷怪点随机取点生成（种族/等级按遇敌表抽）；
- 游走：每 40~70 帧向 4 方向随机走 1 格（不可走 / 有精灵 / 玩家所在格则不动）；
- 碰撞：玩家与精灵同格 -> 立刻进入战斗（BattleScene），战斗结束移除该精灵并冷却。

对外接口（后续批次照着用）
--------------------------
    FieldScene(game)
    scene.enter(map_id=None, x=None, y=None, facing=None)
    scene.gx / scene.gy / scene.facing / scene.map_id
    scene.camera / scene.camera_x / scene.camera_y
    scene.wanderers / scene.wild_state
"""

from __future__ import annotations

import random

import pyxel

from src.assets_gen import palette, sprite_base
from src.assets_gen.sprites import tileset
from src.data import map_data
from src.scenes.menu_scene import MenuScene
from src.scenes.scene_base import Scene
from src.ui import text
from src.ui.transition import Fade

#: 画面尺寸（与 main.py 锁定值一致）
SCREEN_W = 240
SCREEN_H = 216

#: 走一格需要的帧数（规划文档 §3.8 要求 8~12 帧，这里取 10）
STEP_FRAMES = 10

#: 转场淡入淡出帧数
FADE_FRAMES = 15

#: 方向 -> (dx, dy)
DIRECTIONS: dict[str, tuple[int, int]] = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

#: 方向键的检查优先级（同时按住多个键时用这个顺序）
DIR_ORDER: tuple[str, ...] = ("up", "down", "left", "right")


# ------------------------------------------------------------ 明雷遇敌（§10.3）
#: 野外状态挂在 game 上的属性名（**懒创建**，跨场景存活）
WILD_STATE_ATTR = "wild_state"
WILD_RNG_ATTR = "wild_rng"

#: 游走方向（4 方向随机走 1 格，§10.3）
WANDER_DIRS: tuple[tuple[int, int], ...] = ((0, -1), (0, 1), (-1, 0), (1, 0))


def wild_state_of(game) -> dict:
    """取 game 上的野外状态表（懒创建）。

    结构（跨场景存活，战斗结束后地图场景被重建也不丢）：

        {map_id: {"wanderers": [wanderer, ...], "cooldown": {spawn_index: 帧数}}}

    其中 wanderer::

        {"species_id": int, "level": int, "gx": int, "gy": int,
         "alive": bool, "move_timer": int, "spawn_index": int}
    """
    states = getattr(game, WILD_STATE_ATTR, None)
    if not isinstance(states, dict):
        states = {}
        setattr(game, WILD_STATE_ATTR, states)
    return states


def wild_rng_of(game):
    """取 game 上的野外随机源（懒创建，默认 random.Random()）。

    测试可以注入 random.Random(seed) 让刷怪与游走完全可复现。
    """
    rng = getattr(game, WILD_RNG_ATTR, None)
    if rng is None:
        rng = random.Random()
        setattr(game, WILD_RNG_ATTR, rng)
    return rng

#: 对话框位置（《数值设定.md》§13.4：底部 240x48，2 行 19 字）
BOX_X, BOX_Y, BOX_W, BOX_H = 0, 168, 240, 48
BOX_PAD = 6

def compute_camera(player_cx: float, player_cy: float,
                   map_w_px: int, map_h_px: int,
                   view_w: int = SCREEN_W, view_h: int = SCREEN_H) -> tuple[int, int]:
    """算摄像机左上角的像素坐标。

    规则
    ----
    1. 玩家居中：cam = 玩家中心 - 视口一半；
    2. 夹在地图边界内：0 <= cam <= 地图尺寸 - 视口；
    3. 地图比视口小：整张地图居中（cam 为负值）。

    参数里的玩家坐标是**精灵中心**的像素坐标。
    """
    if map_w_px >= view_w:
        cam_x = min(max(int(player_cx) - view_w // 2, 0), map_w_px - view_w)
    else:
        cam_x = (map_w_px - view_w) // 2
    if map_h_px >= view_h:
        cam_y = min(max(int(player_cy) - view_h // 2, 0), map_h_px - view_h)
    else:
        cam_y = (map_h_px - view_h) // 2
    return cam_x, cam_y


class FieldScene(Scene):
    """野外地图场景。"""

    def __init__(self, game):
        super().__init__(game)
        self.map_id: int = map_data.START_MAP_ID
        self.map: dict = map_data.get_map(self.map_id)

        #: 主角所在格
        self.gx = 0
        self.gy = 0
        #: 主角精灵左上角的像素坐标（浮点，移动时插值）
        self.px = 0.0
        self.py = 0.0
        #: 朝向（up / down / left / right）
        self.facing = "down"

        #: 是否正在走格
        self.moving = False
        #: 当前这一步已经走的帧数（1..STEP_FRAMES）
        self.move_timer = 0
        #: 连续走路累计帧数（用来切走路动画）
        self.walk_timer = 0
        #: 走路动画帧号 0 / 1
        self.anim = 0
        #: 本步的起点 / 终点像素坐标
        self.from_px = 0.0
        self.from_py = 0.0
        self.to_px = 0.0
        self.to_py = 0.0

        #: 对话框内容：None 或 {"npc": npc, "lines": [...], "page": int}
        self.dialogue = None
        #: 转场
        self.fade = Fade()
        #: 等待传送的出入口
        self.pending_portal = None

        #: 本次战斗中参战的野生精灵（战斗结束时用来移除它）
        self.battle_target = None
        #: 当前地图的遇敌表（缓存；None = 该图没有野生精灵）
        self._encounters = map_data.encounters_of(self.map_id)
        #: 当前地图的刷怪点（缓存）
        self._spawn_points = map_data.spawn_points_of(self.map_id)

    # ------------------------------------------------------------ 生命周期
    def enter(self, **kwargs) -> None:
        """进入地图场景。

        可选参数：map_id / x / y / facing（都按格坐标）。
        不给 map_id 时沿用 game.player_state 里的地图；
        不给 x / y 时：同地图用 player_state 的位置，否则用地图出生点。
        """
        sprite_base.bake_all()

        state = getattr(self.game, "player_state", None) or {}
        map_id = kwargs.get("map_id")
        if map_id is None:
            map_id = state.get("map_id", map_data.START_MAP_ID)
        x = kwargs.get("x")
        y = kwargs.get("y")
        facing = kwargs.get("facing")
        self.set_map(map_id, x=x, y=y, facing=facing)

    def resume(self) -> None:
        """从下层场景回来：只恢复动画计时，不重置位置。"""
        self.walk_timer = 0

    def exit(self) -> None:
        """退出：把最终状态写回 player_state。"""
        self.sync_state()

    # ------------------------------------------------------------ 地图
    def set_map(self, map_id: int, x: int | None = None, y: int | None = None,
                facing: str | None = None) -> None:
        """切换到指定地图并把主角放到 (x, y)（不给就用出生点 / player_state）。"""
        self.map_id = map_id
        self.map = map_data.get_map(map_id)
        self._encounters = map_data.encounters_of(map_id)
        self._spawn_points = map_data.spawn_points_of(map_id)

        state = getattr(self.game, "player_state", None) or {}
        if x is None or y is None:
            if state.get("map_id") == map_id and "x" in state and "y" in state:
                x = state["x"] if x is None else x
                y = state["y"] if y is None else y
            else:
                spawn = self.map["spawn"]
                x = spawn[0] if x is None else x
                y = spawn[1] if y is None else y

        x = int(x)
        y = int(y)
        if not map_data.is_walkable(map_id, x, y):
            # 落点不可走（例如存档坐标过期）-> 退回出生点
            x, y = self.map["spawn"]
        self.gx, self.gy = x, y
        self.px = float(x * map_data.TILE_SIZE)
        self.py = float(y * map_data.TILE_SIZE)

        self.moving = False
        self.move_timer = 0
        self.walk_timer = 0
        self.anim = 0
        self.dialogue = None
        self.pending_portal = None
        if facing in DIRECTIONS:
            self.facing = facing
        self.sync_state()
        # 野外状态挂在 game 上（跨场景存活）：这里只做「补足数量」，
        # 不会重置已经存活的精灵与重生冷却。
        self._refresh_population()

    def sync_state(self) -> None:
        """把当前位置 / 朝向 / 地图写回 game.player_state（存档系统用）。"""
        state = getattr(self.game, "player_state", None)
        if state is None:
            return
        state["map_id"] = self.map_id
        state["x"] = self.gx
        state["y"] = self.gy
        state["facing"] = self.facing

    # ------------------------------------------------------------ 摄像机
    @property
    def camera(self) -> tuple[int, int]:
        """摄像机左上角像素坐标。"""
        map_w, map_h = map_data.map_pixel_size(self.map_id)
        return compute_camera(self.px + map_data.TILE_SIZE / 2,
                              self.py + map_data.TILE_SIZE / 2,
                              map_w, map_h)

    @property
    def camera_x(self) -> int:
        """摄像机左上角 x（像素）。"""
        return self.camera[0]

    @property
    def camera_y(self) -> int:
        """摄像机左上角 y（像素）。"""
        return self.camera[1]

    # ------------------------------------------------------------ 每帧
    def update(self, inp) -> None:
        """每帧逻辑更新。"""
        # 转场期间：不移动、不交互
        if self.fade.is_active:
            self.fade.update()
            return

        # 对话中：只能翻页 / 关闭，不能移动
        if self.dialogue is not None:
            self._update_dialogue(inp)
            return

        # 面向 NPC 按确认键 -> 打开对话
        if inp.pressed("confirm"):
            npc = self.npc_in_front()
            if npc is not None:
                self.open_dialogue(npc)
                return

        # menu 键：压栈打开菜单（不是 replace —— 地图状态要原样保留）
        if inp.pressed("menu"):
            self.game.scenes.push(MenuScene(self.game))
            return

        direction = self._read_direction(inp)

        if self.moving:
            self._advance_move()
        if not self.moving and direction is not None:
            self._start_move(direction)

        if self.moving:
            self.walk_timer += 1
            self.anim = (self.walk_timer // STEP_FRAMES) % 2
        else:
            self.walk_timer = 0
            self.anim = 0

        self.sync_state()

        # 明雷遇敌：游走 + 碰撞检测。返回 True 表示已经进入战斗场景。
        if self._update_wild():
            return

    def _read_direction(self, inp) -> str | None:
        """读方向：优先用本帧刚按下的方向，否则用当前朝向。"""
        for d in DIR_ORDER:
            if inp.pressed(d):
                self.facing = d
                return d
        if inp.held(self.facing):
            return self.facing
        return None

    def _start_move(self, direction: str) -> None:
        """尝试朝 direction 走一格；目标不可走则只转向不动。"""
        dx, dy = DIRECTIONS[direction]
        tx, ty = self.gx + dx, self.gy + dy
        self.facing = direction
        if not map_data.is_walkable(self.map_id, tx, ty):
            return
        self.moving = True
        self.move_timer = 1
        self.from_px = self.px
        self.from_py = self.py
        self.to_px = float(tx * map_data.TILE_SIZE)
        self.to_py = float(ty * map_data.TILE_SIZE)
        self._apply_interpolation()

    def _advance_move(self) -> None:
        """推进当前这一步的插值；走满 10 帧就落格。"""
        self.move_timer += 1
        if self.move_timer >= STEP_FRAMES:
            self.move_timer = STEP_FRAMES
            self.moving = False
            self.gx = int(self.to_px) // map_data.TILE_SIZE
            self.gy = int(self.to_py) // map_data.TILE_SIZE
            self.px = self.to_px
            self.py = self.to_py
            self._check_portal()
        else:
            self._apply_interpolation()

    def _apply_interpolation(self) -> None:
        """按当前步的进度更新像素坐标。"""
        k = self.move_timer / STEP_FRAMES
        self.px = self.from_px + (self.to_px - self.from_px) * k
        self.py = self.from_py + (self.to_py - self.from_py) * k

    # ------------------------------------------------------------ 出入口
    def _check_portal(self) -> None:
        """踩到出入口格 -> 开始淡出转场。"""
        for portal in self.map["portals"]:
            if portal["x"] == self.gx and portal["y"] == self.gy:
                self.pending_portal = portal
                self.fade.start_out(FADE_FRAMES, on_done=self._enter_portal)
                return

    def _enter_portal(self) -> None:
        """淡出结束：换地图，再淡入。"""
        portal = self.pending_portal
        self.pending_portal = None
        if portal is None:
            return
        self.set_map(portal["to_map"], x=portal["to_x"], y=portal["to_y"])
        self.fade.start_in(FADE_FRAMES)

    # ------------------------------------------------------------ NPC
    def npc_in_front(self) -> dict | None:
        """当前朝向的相邻格上是否有 NPC；有则返回 NPC 数据。"""
        dx, dy = DIRECTIONS[self.facing]
        nx, ny = self.gx + dx, self.gy + dy
        for npc in self.map["npcs"]:
            if npc["x"] == nx and npc["y"] == ny:
                return npc
        return None

    def open_dialogue(self, npc: dict) -> None:
        """打开 NPC 对话框（同时停下移动）。"""
        self.moving = False
        self.move_timer = 0
        self.walk_timer = 0
        self.anim = 0
        self.dialogue = {
            "npc": npc,
            "lines": list(npc.get("lines") or ["……"]),
            "page": 0,
        }

    def _update_dialogue(self, inp) -> None:
        """对话中：确认键翻页 / 关闭，取消键直接关闭。"""
        if inp.pressed("confirm"):
            self.dialogue["page"] += 1
            if self.dialogue["page"] >= len(self.dialogue["lines"]):
                self.dialogue = None
        elif inp.pressed("cancel"):
            self.dialogue = None

    # ---------------------------------------------------- 明雷遇敌（§10.3）
    @property
    def wild_state(self) -> dict:
        """当前地图的野外状态字典（**就是** game.wild_state[map_id] 本身）。

        结构::

            {"wanderers": [wanderer, ...], "cooldown": {spawn_index: 剩余帧数}}

        其中 wanderer::

            {"species_id": int, "level": int, "gx": int, "gy": int,
             "alive": bool, "move_timer": int, "spawn_index": int}
        """
        return self._wild_state()

    @property
    def wanderers(self) -> list[dict]:
        """当前地图存活的野生精灵列表（原地引用 game.wild_state 里的那份）。"""
        return self._wild_state()["wanderers"]

    def _wild_state(self) -> dict:
        """取（并懒创建）当前地图在 game 上的野外状态。

        **这个 dict 是跨场景存活的**：战斗结束后地图场景会被整个重建，
        但因为状态挂在 game 上，存活精灵与重生冷却都不会丢。
        """
        states = wild_state_of(self.game)
        state = states.get(self.map_id)
        if state is None:
            state = {"wanderers": [], "cooldown": {}}
            states[self.map_id] = state
        state.setdefault("wanderers", [])
        state.setdefault("cooldown", {})
        return state

    def _refresh_population(self) -> None:
        """补足野外精灵数量（受 max_alive 与刷怪点占用约束）。

        规则（§10.3）：

        - 同屏存活上限 = encounters["max_alive"]；
        - 处于重生冷却的刷怪点**也算占位**（冷却没走完不许在那里再刷），
          这样「打掉一只 -> 冷却 180 帧 -> 从刷怪点重生」才成立；
        - 精灵不能刷在玩家所在格，也不能和别的精灵重叠。
        """
        enc = self._encounters
        if enc is None:
            return
        points = self._spawn_points
        if not points:
            return

        state = self._wild_state()
        wanderers = state["wanderers"]
        cooldown = state["cooldown"]
        max_alive = int(enc["max_alive"])
        rng = wild_rng_of(self.game)

        # 已被占用（或正在冷却）的刷怪点不能再用
        used = {int(w["spawn_index"]) for w in wanderers}
        used |= {int(i) for i in cooldown}
        free = [i for i in range(len(points)) if i not in used]
        occupied = {(int(w["gx"]), int(w["gy"])) for w in wanderers}

        candidates = free

        # 「存活数 + 冷却中」不超过上限：冷却中的刷怪点也算占位，
        # 这样打掉一只之后不会立刻在别处补一只（冷却形同虚设）。
        while candidates and len(wanderers) + len(cooldown) < max_alive:
            idx = candidates.pop(rng.randrange(len(candidates)))
            px, py = points[idx]
            if not map_data.is_walkable(self.map_id, px, py):
                continue
            if (px, py) == (self.gx, self.gy):
                continue                       # 不刷在玩家所在格
            if (px, py) in occupied:
                continue                       # 不和别的精灵重叠
            self._spawn_wanderer(idx, (px, py))
            occupied.add((px, py))

    def _spawn_wanderer(self, spawn_index: int, point: tuple[int, int]) -> dict | None:
        """在指定刷怪点生成一只野生精灵，返回它的状态字典。"""
        enc = self._encounters
        if enc is None:
            return None
        rng = wild_rng_of(self.game)
        rolled = map_data.roll_wild(self.map_id, rng)
        if rolled is None:
            return None
        species_id, level = rolled
        move_min = int(enc["move_min"])
        move_max = int(enc["move_max"])
        wanderer = {
            "species_id": int(species_id),
            "level": int(level),
            "gx": int(point[0]),
            "gy": int(point[1]),
            "alive": True,
            "move_timer": rng.randint(move_min, move_max),
            "spawn_index": int(spawn_index),
        }
        self._wild_state()["wanderers"].append(wanderer)
        return wanderer

    def _tick_cooldowns(self) -> None:
        """所有地图的重生冷却每帧递减（§10.3：重生冷却 180 帧 = 6 秒）。

        冷却归零时**立刻**在原刷怪点把精灵刷回来
        （§10.3「战斗结束后该实体从地图移除，冷却后从刷怪点重生」）。
        """
        states = wild_state_of(self.game)
        for map_id, state in list(states.items()):
            cooldown = state.get("cooldown") or {}
            for idx in list(cooldown.keys()):
                left = int(cooldown[idx]) - 1
                if left > 0:
                    cooldown[idx] = left
                    continue
                del cooldown[idx]
                self._respawn_wanderer(map_id, int(idx))

    def _respawn_wanderer(self, map_id: int, spawn_index: int) -> None:
        """在指定地图的指定刷怪点重生一只精灵（冷却走完后调用）。

        刷怪点被占 / 不可走 / 已达存活上限时就不刷。
        """
        enc = map_data.encounters_of(map_id)
        if enc is None:
            return
        points = map_data.spawn_points_of(map_id)
        if not 0 <= spawn_index < len(points):
            return

        state = wild_state_of(self.game).setdefault(
            map_id, {"wanderers": [], "cooldown": {}})
        wanderers = state["wanderers"]
        if len(wanderers) >= int(enc["max_alive"]):
            return

        occupied = {(int(w["gx"]), int(w["gy"])) for w in wanderers}
        player_cell = (self.gx, self.gy) if map_id == self.map_id else None

        # 优先原刷怪点；被占了就换一个可用的刷怪点
        candidates = [spawn_index] + [i for i in range(len(points))
                                     if i != spawn_index]
        rng = wild_rng_of(self.game)
        for idx in candidates:
            px, py = points[idx]
            if not map_data.is_walkable(map_id, px, py):
                continue
            if (px, py) in occupied:
                continue                      # 不和别的精灵重叠
            if (px, py) == player_cell:
                continue                      # 不刷在玩家所在格
            rolled = map_data.roll_wild(map_id, rng)
            if rolled is None:
                return
            species_id, level = rolled
            wanderers.append({
                "species_id": int(species_id),
                "level": int(level),
                "gx": int(px),
                "gy": int(py),
                "alive": True,
                "move_timer": rng.randint(int(enc["move_min"]),
                                          int(enc["move_max"])),
                "spawn_index": int(spawn_index),
            })
            return

    def _update_wild(self) -> bool:
        """推进野外状态：冷却递减 -> 补足数量 -> 碰撞检测 -> 游走 -> 碰撞检测。

        返回 True 表示**已经进入战斗**（本帧不要再更新别的逻辑）。

        两次碰撞检测的原因：玩家先走、精灵后走，所以要
        「先查玩家是否踩到精灵，再查精灵是否踩到玩家」。
        """
        self._tick_cooldowns()

        enc = self._encounters
        if enc is None:
            return False

        # 数量不足时补足（冷却走完的精灵已由 _tick_cooldowns 直接重生）
        self._refresh_population()

        # 玩家刚落到精灵所在格 -> 立刻进战斗（精灵还没来得及走）
        if self._check_encounter():
            return True

        state = self._wild_state()
        wanderers = state["wanderers"]
        rng = wild_rng_of(self.game)
        move_min = int(enc["move_min"])
        move_max = int(enc["move_max"])

        occupied = {(int(w["gx"]), int(w["gy"])) for w in wanderers
                    if w.get("alive", True)}
        player_cell = (self.gx, self.gy)

        for w in wanderers:
            if not w.get("alive", True):
                continue
            w["move_timer"] = int(w.get("move_timer", move_min)) - 1
            if w["move_timer"] > 0:
                continue
            # 到了游走时间：4 方向随机走 1 格
            dx, dy = rng.choice(WANDER_DIRS)
            nx, ny = int(w["gx"]) + dx, int(w["gy"]) + dy
            if ((nx, ny) != player_cell
                    and (nx, ny) not in occupied
                    and map_data.is_walkable(self.map_id, nx, ny)):
                occupied.discard((int(w["gx"]), int(w["gy"])))
                w["gx"], w["gy"] = nx, ny
                occupied.add((nx, ny))
            # 走不动就原地不动，重新计时（§10.3「无路可走则原地停留」）
            w["move_timer"] = rng.randint(move_min, move_max)

        # 精灵走到玩家所在格 -> 同样进战斗
        return self._check_encounter()

    def _check_encounter(self) -> bool:
        """玩家与野生精灵同格 -> 立刻进入战斗（§10.3）。"""
        for w in self._wild_state()["wanderers"]:
            if not w.get("alive", True):
                continue
            if int(w["gx"]) == self.gx and int(w["gy"]) == self.gy:
                self._start_battle(w)
                return True
        return False

    def _start_battle(self, wanderer: dict) -> None:
        """进入战斗（**replace** 当前场景，战斗结束后 T3b 会 replace 回地图）。

        为什么用 replace 而不是 push：T3b 的战斗结束时执行
        ``game.scenes.replace(FieldScene(game), ...)``，如果这里 push，
        场景栈会多留一层旧 FieldScene（每打一次仗多一层）。
        """
        from src.model import Creature
        from src.scenes.battle_scene import BattleScene

        self.battle_target = wanderer
        enemy = Creature(int(wanderer["species_id"]), int(wanderer["level"]))
        self.game.scenes.replace(BattleScene(self.game, enemy,
                                  on_end=self._on_battle_end))

    def _on_battle_end(self, result: str) -> None:
        """战斗结束（由 BattleScene 在弹出前调用一次）。

        - 参战的精灵从地图上移除，它占用的刷怪点进入重生冷却；
        - 逃跑（§5.5）：玩家向后弹开 1 格（目标格不可走则原地不动）；
        - 战败：玩家由 T3b 传送到新手村出生点，这里不用特殊处理。
        """
        target = self.battle_target
        self.battle_target = None

        state = self._wild_state()
        enc = self._encounters

        if target is not None:
            wanderers = state["wanderers"]
            for i, w in enumerate(wanderers):
                if w is target:
                    del wanderers[i]
                    break
            target["alive"] = False
            if enc is not None:
                state["cooldown"][int(target["spawn_index"])] = int(
                    enc["respawn_frames"])

        if result == "run":
            self._push_back_player()

    def _push_back_player(self) -> None:
        """玩家向后弹开 1 格（§5.5）；目标格不可走 / 被精灵占着则原地不动。"""
        dx, dy = DIRECTIONS.get(self.facing, (0, 0))
        nx, ny = self.gx - dx, self.gy - dy
        if not map_data.is_walkable(self.map_id, nx, ny):
            return
        for w in self._wild_state()["wanderers"]:
            if w.get("alive", True) and int(w["gx"]) == nx and int(w["gy"]) == ny:
                return
        self.gx, self.gy = nx, ny
        self.px = float(nx * map_data.TILE_SIZE)
        self.py = float(ny * map_data.TILE_SIZE)
        self.moving = False
        self.move_timer = 0
        self.walk_timer = 0
        self.sync_state()

    # ------------------------------------------------------------ 绘制
    def draw(self) -> None:
        """绘制整个地图场景。"""
        self._draw_map()
        self._draw_wanderers()
        self._draw_npcs()
        self._draw_player()
        self._draw_hud()
        if self.dialogue is not None:
            self._draw_dialogue()
        self.fade.draw()

    def _tile_image(self, tile_id: int) -> pyxel.Image:
        """取图块 ID 对应的已烘焙图片。"""
        sprite = tileset.TILES_BY_ID.get(tile_id)
        if sprite is None:
            raise KeyError(f"没有编号为 {tile_id} 的图块")
        return sprite_base.get(sprite.name)

    def _draw_map(self) -> None:
        """画地图图层（只画视口内的格子）。"""
        cam_x, cam_y = self.camera
        m = self.map
        w, h = m["w"], m["h"]
        size = map_data.TILE_SIZE

        x0 = max(0, cam_x // size)
        x1 = min(w - 1, (cam_x + SCREEN_W) // size)
        y0 = max(0, cam_y // size)
        y1 = min(h - 1, (cam_y + SCREEN_H) // size)

        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                img = self._tile_image(m["tiles"][ty][tx])
                dx = tx * size - cam_x
                dy = ty * size - cam_y
                # 裁掉视口外的部分
                sx = sy = 0
                sw = sh = size
                if dx < 0:
                    sx = -dx
                    sw += dx
                    dx = 0
                if dy < 0:
                    sy = -dy
                    sh += dy
                    dy = 0
                if dx + sw > SCREEN_W:
                    sw = SCREEN_W - dx
                if dy + sh > SCREEN_H:
                    sh = SCREEN_H - dy
                if sw > 0 and sh > 0:
                    pyxel.blt(dx, dy, img, sx, sy, sw, sh, colkey=0)

    def _draw_wanderers(self) -> None:
        """画野生精灵（16x16 图标，在玩家**之前**画，玩家在它上面）。"""
        cam_x, cam_y = self.camera
        size = map_data.TILE_SIZE
        for w in self._wild_state()["wanderers"]:
            if not w.get("alive", True):
                continue
            x = int(w["gx"]) * size - cam_x
            y = int(w["gy"]) * size - cam_y
            if x < -size or y < -size or x > SCREEN_W or y > SCREEN_H:
                continue
            try:
                img = sprite_base.get(f"creature_{int(w['species_id'])}_icon")
            except KeyError:
                continue
            pyxel.blt(x, y, img, 0, 0, 16, 16, colkey=0)

    def _draw_npcs(self) -> None:
        """画 NPC（16x16 小人，用图元拼）。"""
        cam_x, cam_y = self.camera
        size = map_data.TILE_SIZE
        for npc in self.map["npcs"]:
            x = npc["x"] * size - cam_x
            y = npc["y"] * size - cam_y
            if x < -size or y < -size or x > SCREEN_W or y > SCREEN_H:
                continue
            self._draw_npc_figure(x, y, npc.get("kind", "npc"))

    def _draw_npc_figure(self, x: int, y: int, kind: str) -> None:
        """画一个小人：头发 + 脸 + 身体（描边统一色 5）。"""
        outline = palette.DARK_PURPLE
        skin = palette.ORANGE
        hair = palette.BROWN
        coat = palette.WHITE if kind == "heal" else palette.LIGHT_BLUE

        # 身体（不超出 16x16 格，避免压到下一格的玩家）
        pyxel.rect(x + 4, y + 8, 8, 5, coat)
        pyxel.rectb(x + 4, y + 8, 8, 5, outline)
        # 头（先画头发再画脸，形成刘海）
        pyxel.circ(x + 8, y + 4, 4, hair)
        pyxel.circ(x + 8, y + 5, 3, skin)
        pyxel.circb(x + 8, y + 4, 4, outline)
        # 眼睛
        pyxel.pset(x + 6, y + 5, outline)
        pyxel.pset(x + 10, y + 5, outline)
        # 衣服标记：护士红十字 / 店员围裙
        if kind == "heal":
            pyxel.rect(x + 7, y + 9, 2, 3, palette.RED)
            pyxel.rect(x + 6, y + 10, 4, 1, palette.RED)
        elif kind == "shop":
            pyxel.rect(x + 6, y + 10, 4, 3, palette.ORANGE)

    def _draw_player(self) -> None:
        """画主角（16x16 行走图）。"""
        img = sprite_base.get(f"player_{self.facing}_{self.anim}")
        cam_x, cam_y = self.camera
        pyxel.blt(int(round(self.px)) - cam_x, int(round(self.py)) - cam_y,
                  img, 0, 0, 16, 16, colkey=0)

    def _draw_hud(self) -> None:
        """左上角金币 + 右上角地图名。"""
        dollars = (getattr(self.game, "player_state", None) or {}).get("dollars", 300)
        money_text = f"金币 {dollars}"
        mw = text.width(money_text)
        pyxel.rect(0, 0, mw + 8, 16, palette.DEEP_BLUE)
        text.draw(4, 2, money_text, palette.YELLOW)

        name = self.map["name"]
        nw = text.width(name)
        pyxel.rect(SCREEN_W - nw - 8, 0, nw + 8, 16, palette.DEEP_BLUE)
        text.draw(SCREEN_W - nw - 4, 2, name, palette.WHITE)

    def _draw_dialogue(self) -> None:
        """底部对话框：白底黑字，2 行 19 字（《数值设定.md》§13.4）。"""
        pyxel.rect(BOX_X, BOX_Y, BOX_W, BOX_H, palette.LIGHT_GRAY)
        pyxel.rectb(BOX_X, BOX_Y, BOX_W, BOX_H, palette.DARK_PURPLE)

        d = self.dialogue
        name = d["npc"].get("name", "")
        text.draw(BOX_X + BOX_PAD, BOX_Y + 4, name, palette.RED)

        lines = d["lines"]
        page = min(d["page"], len(lines) - 1)
        text.draw_wrapped(BOX_X + BOX_PAD, BOX_Y + 20, lines[page],
                          BOX_W - BOX_PAD * 2, palette.BLACK)

        # 翻页提示（右下角小三角）
        if d["page"] < len(lines) - 1:
            ty = BOX_Y + BOX_H - 12
            pyxel.tri(BOX_X + BOX_W - 18, ty,
                      BOX_X + BOX_W - 18, ty + 8,
                      BOX_X + BOX_W - 10, ty + 4,
                      palette.DARK_PURPLE)
