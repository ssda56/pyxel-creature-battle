# 中文字体目录

**本目录已随仓库分发一份开源的 12px 中文点阵字体**，游戏默认使用它：

| 文件 | 说明 |
|---|---|
| `ark-pixel-12px-monospaced-zh_hans.ttf` | **Ark Pixel Font（方舟像素字体）12px 等宽简体中文版** |
| `OFL.txt` | 上述字体的 SIL Open Font License 1.1 授权全文 |

## 为什么用点阵字体

它是为 12px 手工点阵设计的中文像素字体，每条笔画都落在整像素上。
系统矢量黑体（如 simhei）在 12px 下横竖笔画会粘连、还会出现块状伪影——
同一段文字并排渲染对比过，差距很明显。

两者字宽实测**完全一致**（全角 12px / 半角 6px），所以换字体不影响任何布局常量。

## 想换字体

把字体文件放进本目录，再改 `src/ui/text.py` 里 `FONT_CANDIDATES` 的顺序。
注意：**字体路径只允许出现在 `src/ui/text.py` 这一个文件里**（项目硬性约定）。

回退顺序：内置点阵字体 → `assets/fonts/simhei.ttf` →
`C:\Windows\Fonts\simhei.ttf` → `msyh.ttc` → `Deng.ttf` → `simsun.ttc`。

> **不要**把素材目录里的 `umplus_j12r.bdf` / `PixelMplus12-Regular.ttf` 复制过来：
> 它们是日文字体，缺简体字形，"精灵对战"会渲染成"精?小游"（已实测）。
