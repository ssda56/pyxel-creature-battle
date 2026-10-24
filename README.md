# 精灵对战小游戏

一款像素卡通风格的 2D 俯视角精灵对战 RPG（Pyxel 实现），玩法循环参考经典宝可梦式：

**探索地图 → 遭遇野生精灵 → 战斗 / 捕捉 → 治疗与养成 → 商店补给 → 继续探索**

| 项 | 值 |
|---|---|
| 画面 | 240 × 216，60 fps，自定义 16 色调色板 |
| 引擎 | Pyxel 2.9.9 / Python 3.12.14 |
| 内容规模 | 8 只精灵 · 28 个技能 · 3 张地图 · 5 件道具 · 15 个音效 · 3 段 BGM |
| 自动化测试 | 553 个用例，全绿（标准库 `unittest`） |
| 状态 | **功能完整，可从头玩到尾** |

> **玩家向的说明**（怎么操作、界面怎么读、怎么存档）在 **[docs/游戏说明书.md](docs/游戏说明书.md)**。
> 本文档面向开发者与维护者。
>
> 里程碑 M0–M8 的逐条核对结论在 **[docs/里程碑核对.md](docs/里程碑核对.md)**。

---

## 1. 环境

| 项 | 值 |
|---|---|
| 解释器 | `E:\小说2\精灵对战小游戏\.venv\Scripts\python.exe`（Python 3.12.14） |
| 依赖 | 仅 `pyxel` 2.9.9 + Python 标准库。**不要 pip install 任何东西**（本机 pip 会挂死） |
| 画面 | 240 × 216，60 fps（已锁定） |
| 操作系统 | Windows（中文渲染依赖 Windows 系统字体） |

## 2. 运行

```powershell
cd E:\小说2\精灵对战小游戏
.\.venv\Scripts\python.exe main.py
```

无窗口自检（不依赖显示器，用于 CI / 截图核对）：

```powershell
.\.venv\Scripts\python.exe main.py --headless --frames 10 --shot docs/shots/_check.png
```

> `docs/shots/_*.png` 已在 `.gitignore` 里，自检截图不会进版本库。

## 3. 操作

| 动作 | 按键 |
|---|---|
| 移动 | **W A S D** 或 方向键（两种都支持） |
| 确认 | Z / K / Enter |
| 取消 | X / J / Backspace |
| 打开菜单 | C |
| 退出确认弹窗 | Esc（不再直接退出，见下） |
| 静音开关 | M |

**Esc 的行为**：`main.py` 给 `pyxel.init` 传了 `quit_key=pyxel.KEY_NONE`，关掉了 Pyxel 自带的
"Esc 立刻退出"。Esc 改由 `src/core/game.py` 接管，弹出**退出确认弹窗**
（存档并退出 / 直接退出 / 取消），弹窗期间游戏逻辑暂停。

**游玩前请把输入法切成英文**，否则人物不动 —— 这是 Windows + SDL 的行为，不是 bug，详见 §8.1。

## 4. 跑测试

用标准库 `unittest`（**不是 pytest**，环境里没装，也别装）：

```powershell
cd E:\小说2\精灵对战小游戏
.\.venv\Scripts\python.exe -m unittest discover -s tests -t .
```

### ⚠️ PowerShell 下的假失败

`unittest` 把进度点写到 **stderr**，PowerShell 会把它当成 `NativeCommandError`，
于是**即使全部通过，`$LASTEXITCODE` 也是 1**。看结论请认准这两行，别看退出码：

```
Ran 553 tests in 6.059s
OK
```

想拿到干净的退出码，把 stderr 合进 stdout：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . 2>&1 | Select-Object -Last 5
```

## 5. 目录结构

```
精灵对战小游戏/
├── main.py                          # 入口：pyxel.init / run，场景调度
├── README.md                        # 本文档（开发者向）
├── assets/fonts/README.md           # 中文字体放这里（不放也能跑，见 §6.1）
├── docs/
│   ├── 游戏说明书.md                 # 玩家向操作说明
│   ├── 数值设定.md                   # 全部数值的唯一权威来源
│   ├── 里程碑核对.md                 # M0–M8 逐条核对结论
│   ├── 美术生图提示词.md             # AI 生图提示词（最终未采用，见 §8.3）
│   └── shots/                       # 各批次截图归档
├── saves/                           # 存档目录（save1.json 已被 .gitignore 忽略）
├── tools/
│   └── art_import.py                # 可选：AI 图 → 字符画转换器（需 Pillow，未参与构建）
├── src/
│   ├── core/
│   │   ├── game.py                  # App 主类：update/draw 分发、退出确认弹窗、静音提示
│   │   ├── scene_manager.py         # 场景栈（push / pop / replace）
│   │   ├── input.py                 # 输入抽象（9 动作，RealInput / FakeInput）
│   │   └── focus.py                 # 启动时把窗口抢到前台（Windows）
│   ├── data/                        # 纯数据层，不含逻辑
│   │   ├── species_data.py          # 8 只精灵种族表
│   │   ├── skill_data.py            # 28 个技能
│   │   ├── item_data.py             # 5 件道具 + 初始背包 + 初始金币
│   │   └── map_data.py              # 3 张地图、走行性、传送点、刷怪点、NPC、遇敌表
│   ├── model/                       # 纯模型层，不 import 任何 UI / 引擎模块
│   │   ├── creature.py              # 精灵实例：等级 / 经验 / HP / MP / 技能
│   │   ├── player.py                # 玩家：金币 / 队伍 / 仓库 / 背包
│   │   └── save_io.py               # 存档读写（原子写入、读档不抛异常）
│   ├── battle/                      # 纯计算层
│   │   ├── type_chart.py            # 8×8 属性克制表（7 正式属性 + 内部"无"）
│   │   ├── damage_calc.py           # 伤害公式
│   │   └── catch_calc.py            # 捕捉概率公式
│   ├── scenes/
│   │   ├── scene_base.py            # enter / resume / exit / update / draw
│   │   ├── title_scene.py           # 标题：新游戏 / 继续游戏
│   │   ├── starter_scene.py         # 开局三选一
│   │   ├── field_scene.py           # 地图探索：移动 / 碰撞 / 摄像机 / 明雷 / NPC / 传送
│   │   ├── battle_scene.py          # 回合制战斗（五指令）
│   │   ├── menu_scene.py            # 主菜单：精灵 / 道具 / 存档 / 返回
│   │   └── shop_scene.py            # 商店买卖
│   ├── ui/
│   │   ├── text.py                  # 中文渲染（字体路径只在这个文件里）
│   │   ├── widgets.py               # 列表 / 对话框 / 血条蓝条
│   │   ├── damage_number.py         # 圆圈数字伤害飘字
│   │   ├── transition.py            # Bayer 抖动淡入淡出
│   │   └── sound.py                 # 音效与 BGM（15 SFX / 3 BGM / 静音）
│   └── assets_gen/                  # 程序化素材（规划文档的"方案 D"）
│       ├── palette.py               # 全局唯一配色来源 + 属性→主色表
│       ├── sprite_base.py           # 字符画烘焙器 + 绘图画布
│       └── sprites/
│           ├── tileset.py           # 12 种 16×16 图块
│           ├── player.py            # 主角 4 方向 × 2 帧
│           └── creatures.py         # 8 只精灵（战斗图 32×32 + 图标 16×16）
└── tests/                           # 553 个用例
    ├── helpers.py                   # 无窗口跑帧 / 截图 / 假输入
    ├── field_helpers.py             # FieldScene 专用辅助
    ├── battle_helpers.py            # BattleScene 专用辅助
    └── test_*.py                    # 45 个测试文件，按模块划分
```

## 6. 关键约定（改代码前必读）

### 6.1 中文字体

- **字体路径只允许出现在 `src/ui/text.py`**，其他任何文件都不许写字体路径。
- **所有中文必须经 `src/ui/text.py` 渲染**，禁止直接用 `pyxel.text` 画中文。

```python
from src.ui import text
text.draw(x, y, "精灵对战", 10)          # 左上角对齐
text.draw_center(cx, y, "精灵对战", 10)   # 水平居中
text.width("精灵对战")                    # -> 48（全角 12px / 半角 6px）
text.wrap("一段很长的话", 120)            # 按像素宽度折行
```

- 字体回退顺序：`assets/fonts/simhei.ttf` → `C:\Windows\Fonts\simhei.ttf` →
  `msyh.ttc` → `Deng.ttf` → `simsun.ttc`，全都没有就抛 `RuntimeError`。
- **绝对不要用素材目录里的 `umplus_j12r.bdf` / `PixelMplus12-Regular.ttf`**：
  它们是日文字体，缺简体字形，"精灵对战"会渲染成"精?小游"（已实测）。
- 字号固定 **12**（行高 14）。

### 6.2 调色板与描边

- 全部色号来自 `src/assets_gen/palette.py`，**不允许在别处写裸色号**。
- 本项目使用**自定义 16 色**：Pyxel 2.9.9 的 `pyxel.init()` 没有 palette 参数，
  所以在 `init()` 之后用 `palette.apply()`（内部是 `pyxel.colors[:] = PALETTE_RGB`）整体替换。
- 索引语义：0 黑 / 1 深蓝 / 2 蓝 / 3 深绿 / 4 绿 / **5 深紫（描边专用）** / 6 灰 / 7 白 /
  8 红 / 9 橙 / 10 黄 / 11 浅绿 / 12 浅蓝 / 13 棕 / 14 粉 / 15 浅灰。
- 属性 → 主色：火=9 橙，水=12 浅蓝，草=11 浅绿，风=2 蓝，光=7 白，暗=14 粉，雷=10 黄，无=6 灰。
- **描边一律用色 5**：`pyxel.blt(colkey=0)` 会把色 0 变透明，黑色描边会整圈消失（已实测）。
  同理，**精灵图里不能出现色 0**。

### 6.3 素材烘焙

```python
from src.assets_gen import sprite_base
sprite_base.bake_all()                   # 启动时烘焙全部素材（幂等）
img = sprite_base.get("player_down_0")   # 取已烘焙的 pyxel.Image
pyxel.blt(x, y, img, 0, 0, 16, 16, colkey=0)
```

- 字符画里 `'.'` 表示透明（烘焙时跳过不写像素），其他字符必须在该精灵的 palette 里声明。
- 字符画每行长度必须一致，否则 `bake()` 抛 `SpriteRowLengthError`（`ValueError` 子类），
  消息里带**精灵名 + 行号**。
- 新增素材：写一个 `SpriteMatrix` 模块，导出 `SPRITES` 列表，并在
  `src/assets_gen/sprites/__init__.py` 的 `ALL_SPRITES` 里挂上。

### 6.4 输入

- 动作共 9 个：`up / down / left / right / confirm / cancel / menu / quit / mute`。
- `Input.held(action)` = 持续按住；`Input.pressed(action)` = 本帧边沿。
- 测试用 `FakeInput(script=[{"confirm": 3}])`：脚本是**段列表**，
  每段 `{动作: 持续帧数}`，段与段不重叠，用完后不再按住。
- `Game.update()` 的顺序是：**先跑 `scene.update(input)`，最后才 `input.update()`**。

### 6.5 场景栈

- `SceneManager.push(scene)` → 调 `scene.enter()`
- `SceneManager.pop()` → 弹栈，先 `scene.exit()`，再让下层 `scene.resume()`
- `SceneManager.replace(scene)` → 旧场景 `exit()`，新场景 `enter()`
- `resume()` = "重新回到前台"，恢复动画 / 计时器，**不重置**状态；
  重置请写在 `enter()` 里。

### 6.6 音频

- **15 个音效**（合成器 MML，走通道 0/1/2）：
  `cursor / confirm / cancel / coin / hit / hit_super / hurt / catch_ok / catch_fail /
  heal / level_up / encounter / victory / escape / defeat`
- **3 段 BGM**（ogg，独占**通道 3**，不抢占音效）：`field / cave / battle`
- 音量：音效 `SFX_GAIN = 0.3`，BGM `BGM_GAIN = 0.6`。
- `play_bgm(name)` 内部去重：同一个 BGM 重复请求只触发一次 `pyxel.play`。
- 无音频设备 / 无头环境下 `init()` 只把音频标记成"不可用"，游戏照常跑。

## 7. 与规划文档的偏差

`E:\小说2\01-规划开发文档.md` 是**动工前的规划稿**，里面的架构清单与实际实现有若干出入。
代码是准的，文档没同步。逐条记录如下（详细核对见 [docs/里程碑核对.md](docs/里程碑核对.md)）：

| # | 规划文档写的 | 实际实现 | 说明 |
|---|---|---|---|
| 1 | `src/model/bag.py` | **不存在**，背包并入 `src/model/player.py` | 背包就是个 `dict[int, int]`，不值得单独一个文件 |
| 2 | `assets/game.pyxres` | **不存在**，改为 `src/assets_gen/` 程序化生成 | 见 §8.3 |
| 3 | 字体放 `assets/fonts/` | 目录留空，回退到系统 `simhei.ttf` | 见 §8.3 |
| 4 | §3.2「玩家指令**四**选一」 | **五**选一（多一个"精灵"换人） | 少了换人没法打 |
| 5 | §3.7「草丛随机遇敌约 10%/步」 | **明雷**：地图上游走的实体，碰撞进战斗 | 文档 §八（第 251 行）自己确认过明雷，**文档内部矛盾** |
| 6 | §3.8「每格 8~12 帧插值」 | **20 帧**/格 | 60fps 下 0.33 秒一格，手感更实 |
| 7 | §3.9「预留 3 个存档位」 | 只做 1 个，且没有预留结构 | MVP 范围 |
| 8 | §3.4「与仓库交换」 | **未实现**，只有队伍内两只互换 | 已知缺口，见 §8.6 |
| 9 | §14「用 **pytest** 断言」 | 实际用标准库 `unittest` | pytest 装不上，见 §1 |

## 8. 已知限制

### 8.1 中文输入法会吞掉按键（重要）

**开启中文输入法（IME）时，游戏收不到键盘事件**：画面正常刷新，但人物不走、菜单不响应。
这是 Windows + SDL 层面的行为，不是游戏 bug（实测：窗口焦点正常 `focus=1`、游戏循环正常、
无任何异常，但 `pyxel.btn()` 恒为 False）。

**解决办法：游玩前把输入法切到英文**（Shift 或 Win+Space）。

### 8.2 同一进程内不能重复 `pyxel.init()`

Pyxel 2.9.9 的 Rust 内核在第二次 `pyxel.init()` 时会 panic（`Pyxel already initialized`）。
所以**不要用 PyCharm 的 Python 控制台反复重跑**，用 Run 按钮（每次全新进程）或命令行。
同理，`pyxel.quit()` 会**直接结束整个进程**，测试里一律用桩替换，不要真调。

### 8.3 美术与字体都是"程序自带"，没有外部素材

精灵、图块、主角全部是**字符画 + 调色板**在启动时烘焙成 `pyxel.Image` 的，
源码即素材，改图改 `src/assets_gen/sprites/*.py` 就行。当初评估过 AI 生图再转换的路线
（`tools/art_import.py` 与 `docs/美术生图提示词.md` 是那条路的残留），**最终没有采用**。

代价：风格偏简，8 只精灵的辨识度依赖颜色和轮廓差异。

字体同理，没有随项目分发 `simhei.ttf`，靠系统字体回退。**换了没有黑体的机器会抛 `RuntimeError`**，
届时把 `simhei.ttf` 放进 `assets/fonts/` 即可。

### 8.4 音频只验证了接线，没验证听感

15 个音效与 3 段 BGM 的**触发时机、通道分配、去重、静音**都有自动化测试覆盖，
但**音量平衡、音色是否好听，没有任何人正式听过并确认**。这块需要人耳判断。

### 8.5 没有 30 分钟连续试玩记录

规划文档 M8 的验收标准是「30 分钟流畅试玩无崩溃」。项目里**目前没有这份记录**——
`saves/save1.json` 里能查到的时长是 `play_seconds: 30`（30 秒）。所以 M8 判"部分达成"。

能拿出的替代证据是：553 个用例全绿、多轮无头长跑不崩溃、单帧耗时约 5 ms（16.67 ms 预算的 30%）。
但这些**都不能代替真人在真窗口里连玩 30 分钟**。

### 8.6 仓库交换没做

队伍满 6 只后，捕捉到的精灵会进"仓库"，但**没有界面把仓库里的精灵换回队伍**。
属于已知功能缺口。

## 9. 数值可调点

全部数值的唯一权威来源是 [docs/数值设定.md](docs/数值设定.md)。其中 §12 列出五个可调点，
**当前全部是默认值，一个都没调过**：

| 编号 | 内容 | 当前值 |
|---|---|---|
| O-1 | 固定伤害项（压缩"抵抗命中"的回合数） | **关闭**（`FIXED_DAMAGE = 0`，`src/battle/damage_calc.py`） |
| O-2 | 经验曲线 | `10 × L^1.40 + 6` |
| O-3 | 遇敌权重 / 等级区间 | 见 `src/data/map_data.py` |
| O-4 | 商品价格 | 见 `src/data/item_data.py` |
| O-5 | 初始金币 | 300 |

**O-1 是已知的手感痛点**：属性被抵抗时，Lv5 一次只能打掉很少血，要十来下才能结束一场。
把它从 0 改成 2 能把回合数压到 6 下左右，但会让整体节奏变快。**尚未调整，等你试玩后的判断。**
