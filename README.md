# 精灵对战小游戏

一款像素卡通风格的 2D 俯视角精灵对战 RPG（Pyxel 实现），玩法循环参考经典宝可梦式：

**探索地图 → 遭遇野生精灵 → 战斗 / 捕捉 → 治疗与养成 → 商店补给 → 继续探索**

当前进度：**批 1 —— 项目地基**（只搭工程框架与占位素材，战斗 / 背包 / 存档等玩法尚未实现）。

---

## 1. 环境

| 项 | 值 |
|---|---|
| 解释器 | `E:\小说2\精灵对战小游戏\.venv\Scripts\python.exe`（Python 3.12.14） |
| 依赖 | 仅 `pyxel`（2.9.9）+ Python 标准库，**不要 pip install 任何东西** |
| 画面 | 240 x 216，30 fps（**已锁定**） |
| 操作系统 | Windows（中文渲染依赖 Windows 系统字体） |

## 2. 运行

```powershell
# 开窗口运行（Esc 退出）
E:\小说2\精灵对战小游戏\.venv\Scripts\python.exe main.py

# 无窗口自检（跑 10 帧并截图，用于 CI / 画面核对）
E:\小说2\精灵对战小游戏\.venv\Scripts\python.exe main.py --headless --frames 10 --shot docs/shots/batch1_title.png
```

## 3. 跑测试

用标准库 `unittest`（**不是 pytest**，环境里也没装）：

```powershell
cd E:\小说2\精灵对战小游戏
E:\小说2\精灵对战小游戏\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

## 4. 目录结构

```
精灵对战小游戏/
├── main.py                      # 入口：pyxel.init / run，场景调度
├── README.md
├── assets/
│   └── fonts/                   # 可选：把 simhei.ttf 放这里（见下方字体说明）
├── docs/
│   ├── 数值设定.md               # 全部数值的唯一权威来源（已获用户批准）
│   └── shots/                   # 截图输出目录
│       └── batch1_title.png
├── saves/                       # 存档目录（后续批次使用）
├── src/
│   ├── core/
│   │   ├── game.py              # App 主类：update/draw 分发到当前场景
│   │   ├── scene_manager.py     # 场景栈（push / pop / replace）
│   │   └── input.py             # 输入抽象（RealInput / FakeInput）
│   ├── scenes/
│   │   ├── scene_base.py        # 场景基类（enter/resume/exit/update/draw）
│   │   └── title_scene.py       # 标题画面（新游戏 / 继续游戏）
│   ├── ui/
│   │   └── text.py              # 中文文本渲染封装（字体路径只在这里）
│   └── assets_gen/              # 程序化素材（规划文档 `9 方案 D）
│       ├── palette.py           # 全局唯一配色来源 + 属性→主色表
│       ├── sprite_base.py       # 字符画烘焙器 + 绘图辅助画布
│       └── sprites/
│           ├── tileset.py               # 10 种 16x16 图块
│           ├── player.py                # 主角 4 方向 x 2 帧
│           └── creature_placeholder.py  # 8 只精灵占位图（战斗 32x32 + 图标 16x16）
└── tests/
    ├── helpers.py               # 无窗口跑帧 / 截图 / 假输入工具
    ├── test_text.py
    ├── test_sprite.py
    ├── test_scene_manager.py
    └── test_title_shot.py
```

## 5. 关键约定（后续批次照此写）

### 5.1 中文字体

- **字体路径只允许出现在 `src/ui/text.py`**；其他任何文件都不许写字体路径。
- **所有中文必须经 `src/ui/text.py` 渲染**，禁止直接 `pyxel.text` 画中文。

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
  它们是日文字体，缺简体字形，“精灵对战”会渲染成“精?小游”（已实测）。
- 字号固定 **12**（行高 14），与《数值设定.md》`13 一致。

### 5.2 调色板与描边

- 全部色号来自 `src/assets_gen/palette.py`，**不允许在别处写裸色号**。
- 本项目使用**自定义 16 色**：Pyxel 2.9.9 的 `pyxel.init()` 没有 palette 参数，
  所以在 `init()` 之后用 `palette.apply()`（内部是 `pyxel.colors[:] = PALETTE_RGB`）整体替换。
- 索引语义：0 黑 / 1 深蓝 / 2 蓝 / 3 深绿 / 4 绿 / **5 深紫（描边专用）** / 6 灰 / 7 白 /
  8 红 / 9 橙 / 10 黄 / 11 浅绿 / 12 浅蓝 / 13 棕 / 14 粉 / 15 浅灰。
- 属性 → 主色：火=9 橙，水=12 浅蓝，草=11 浅绿，风=2 蓝，光=7 白，暗=14 粉，雷=10 黄，无=6 灰。
- **描边一律用色 5**：`pyxel.blt(colkey=0)` 会把色 0 变透明，黑色描边会整圈消失（已实测）。
  同理，**精灵图里不能出现色 0**。

### 5.3 素材烘焙

```python
from src.assets_gen import sprite_base
sprite_base.bake_all()                   # 启动时烘焙全部素材（幂等）
img = sprite_base.get("player_down_0")   # 取已烘焙的 pyxel.Image
pyxel.blt(x, y, img, 0, 0, 16, 16, colkey=0)
```

- 字符画里 `'.'` 表示透明（烘焙时跳过不写像素），其他字符必须在该精灵的 palette 里声明。
- 字符画每行长度必须一致，否则 `bake()` 抛 `SpriteRowLengthError`（ValueError 子类），
  消息里带**精灵名 + 行号**。
- 新增素材：写一个 `SpriteMatrix` 模块，导出 `SPRITES` 列表，并在
  `src/assets_gen/sprites/__init__.py` 的 `ALL_SPRITES` 里挂上。

### 5.4 输入

- 动作只有 7 个：`up / down / left / right / confirm / cancel / menu`。
- 按键：方向键；confirm = Z / K / Enter；cancel = X / J / Backspace；menu = C。
- **Esc 不做功能键**（保持 Pyxel 默认退出键）。
- `Input.held(action)` = 持续按住；`Input.pressed(action)` = 本帧边沿。
- 测试用 `FakeInput(script=[{"confirm": 3}])`：脚本是**段列表**，
  每段 `{动作: 持续帧数}`，段与段不重叠，用完后不再按住。

### 5.5 场景栈

- `SceneManager.push(scene)` → 调 `scene.enter()`
- `SceneManager.pop()` → 弹栈，先 `scene.exit()`，再让下层 `scene.resume()`
- `SceneManager.replace(scene)` → 旧场景 `exit()`，新场景 `enter()`
- `resume()` = “重新回到前台”，恢复动画 / 计时器，**不重置**状态；
  重置请写在 `enter()` 里。

## 6. 本批范围

**已做**：工程骨架、输入抽象、场景栈、标题画面、中文文本模块、调色板、
图块 / 主角 / 精灵占位素材、单元测试与截图自检。

**没做（后续批次）**：地图行走、遇敌、战斗、捕捉、背包、商店、存档、音效。
`docs/数值设定.md` 是全部数值的唯一权威来源，实现时以它为准。
